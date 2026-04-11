"""
BR3 Cluster — Log Analysis (runs on Muddy)
Pattern detection, cross-file correlation, error fingerprinting.
Reads logs directly from local project directories — no SSH sync needed.

Run: uvicorn core.cluster.node_analysis:app --host 0.0.0.0 --port 8200
"""

import os
import re
import time
import json
import sqlite3
import hashlib
import threading
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import FastAPI
from pydantic import BaseModel

from core.cluster.base_service import create_app

# --- Config ---
# On Muddy, logs are local — no SSH sync needed
PROJECTS_DIR = os.environ.get("PROJECTS_DIR", os.path.expanduser("~/Projects"))
DB_PATH = os.environ.get("ANALYSIS_DB", os.path.expanduser("~/.buildrunner/analysis.db"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))

# --- App ---
app = create_app(role="log-analysis", version="0.1.0")

# --- State ---
_analyzing = False
_last_analysis_time = 0.0
_active_patterns = []
_known_fingerprints: set[str] = set()
_resolved_fingerprints: set[str] = set()

# Remove LOG_DIR — not needed when running locally
LOG_DIR = None  # kept for compatibility but unused


# --- SQLite Setup ---
def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS log_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            log_type TEXT NOT NULL,
            event_type TEXT,
            level TEXT,
            message TEXT,
            method TEXT,
            url TEXT,
            status_code INTEGER,
            duration_ms INTEGER,
            response_size INTEGER,
            payload TEXT,
            project TEXT,
            ingested_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            first_seen TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now')),
            resolved INTEGER DEFAULT 0,
            fingerprint TEXT,
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            sources TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            details TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_entries_ts ON log_entries(timestamp);
        CREATE INDEX IF NOT EXISTS idx_entries_type ON log_entries(log_type);
        CREATE INDEX IF NOT EXISTS idx_entries_level ON log_entries(level) WHERE level IN ('error', 'warn');
        CREATE INDEX IF NOT EXISTS idx_patterns_resolved ON patterns(resolved);
        CREATE INDEX IF NOT EXISTS idx_patterns_severity ON patterns(severity);

        CREATE VIRTUAL TABLE IF NOT EXISTS log_fts USING fts5(
            message, url, content='log_entries', content_rowid='id', detail='none'
        );
    """)
    conn.commit()


# --- Log Parsing ---
SUPABASE_RE = re.compile(
    r'\[(.+?)\]\s+\[(\w+)\]\s+(\w+)\s+(.+?)\s+(\d+)\s+(\d+)ms\s+(\d+)b'
)
BROWSER_RE = re.compile(
    r'\[(.+?)\]\s+\[(\w+)\]\s+(.*)'
)
WARNING_RE = re.compile(r'^\s+[⚠!]\s+(\w+)\s+[—-]\s+(.*)')


def _parse_supabase_log(filepath: str) -> list[dict]:
    entries = []
    try:
        lines = Path(filepath).read_text(errors="replace").split("\n")
    except Exception:
        return []

    current = None
    for line in lines[-500:]:  # Last 500 lines
        m = SUPABASE_RE.match(line)
        if m:
            if current:
                entries.append(current)
            status = int(m.group(5))
            size = int(m.group(7))
            level = "error" if status >= 500 else "warn" if status >= 400 or (status == 200 and size == 0) else "info"
            current = {
                "timestamp": m.group(1), "log_type": "supabase",
                "event_type": m.group(2).lower(), "method": m.group(3),
                "url": m.group(4), "status_code": status,
                "duration_ms": int(m.group(6)), "response_size": size,
                "level": level, "message": line.strip(),
            }
            continue

        w = WARNING_RE.match(line)
        if w and current:
            current["payload"] = json.dumps({"warning": w.group(1), "detail": w.group(2)})
            current["level"] = "warn"
            continue

        e = BROWSER_RE.match(line)
        if e:
            if current:
                entries.append(current)
            current = {
                "timestamp": e.group(1), "log_type": "supabase",
                "event_type": e.group(2).lower(), "level": "info",
                "message": e.group(3),
            }

    if current:
        entries.append(current)
    return entries


NET_RE = re.compile(
    r'\[NET\]\s+(\w+)\s+(https?://\S+)\s+(\w+)\s+(\d+)ms'
)


def _parse_browser_log(filepath: str) -> list[dict]:
    entries = []
    try:
        lines = Path(filepath).read_text(errors="replace").split("\n")
    except Exception:
        return []

    for line in lines[-500:]:
        m = BROWSER_RE.match(line)
        if not m:
            continue

        raw_level = m.group(2).lower()
        message = m.group(3)

        # --- Parse [NET] lines specially to extract status, URL, method ---
        if raw_level == "net":
            net_match = NET_RE.match(f"[NET] {message}")
            if net_match:
                method = net_match.group(1)
                url = net_match.group(2)
                status_raw = net_match.group(3)
                duration = int(net_match.group(4))

                # Determine level from status
                if status_raw == "ERR":
                    level = "error"
                    status_code = 0  # network failure / timeout
                elif status_raw.isdigit():
                    status_code = int(status_raw)
                    level = "error" if status_code >= 500 else "warn" if status_code >= 400 else "info"
                else:
                    status_code = 0
                    level = "warn"

                entries.append({
                    "timestamp": m.group(1), "log_type": "browser",
                    "event_type": "network", "level": level,
                    "message": message,
                    "method": method, "url": url,
                    "status_code": status_code, "duration_ms": duration,
                })
            continue

        # --- Regular console entries ---
        if raw_level in ("error", "err"):
            level = "error"
        elif raw_level in ("warn", "warning"):
            level = "warn"
        else:
            level = raw_level

        entries.append({
            "timestamp": m.group(1), "log_type": "browser",
            "event_type": "console", "level": level,
            "message": message,
        })
    return entries


def _parse_generic_log(filepath: str, log_type: str) -> list[dict]:
    entries = []
    try:
        lines = Path(filepath).read_text(errors="replace").split("\n")
    except Exception:
        return []

    for line in lines[-500:]:
        m = BROWSER_RE.match(line)
        if m:
            entries.append({
                "timestamp": m.group(1), "log_type": log_type,
                "event_type": m.group(2).lower(),
                "level": "info", "message": m.group(3),
            })
    return entries


# --- Error Fingerprinting ---
def _fingerprint(entry: dict) -> str:
    msg = entry.get("message", "")
    # Strip variable parts
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}T[\d:.]+Z?', '<TS>', msg)
    normalized = re.sub(r'\b[0-9a-f]{8,}\b', '<HEX>', normalized, flags=re.I)
    normalized = re.sub(r'\b\d{3,}\b', '<N>', normalized)
    normalized = re.sub(r'"[^"]{20,}"', '"<STR>"', normalized)

    raw = f"{entry.get('level', '')}:{entry.get('log_type', '')}:{normalized}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# --- Pattern Detection ---
def _detect_patterns(entries: list[dict]) -> list[dict]:
    patterns = []

    # Group by log_type
    by_type = defaultdict(list)
    for e in entries:
        by_type[e.get("log_type", "unknown")].append(e)

    # --- Auth refresh loop (only flag if 5+ TOKEN_REFRESHED in 30s window) ---
    auth_events = [e for e in entries if "TOKEN_REFRESHED" in e.get("message", "")]
    if len(auth_events) >= 5:
        timestamps = []
        for e in auth_events:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamps.append(dt)
                except (ValueError, TypeError):
                    pass
        timestamps.sort()
        rapid_burst = False
        if len(timestamps) >= 5:
            for i in range(len(timestamps) - 4):
                window = (timestamps[i + 4] - timestamps[i]).total_seconds()
                if window <= 30:
                    rapid_burst = True
                    break
        if rapid_burst:
            patterns.append({
                "pattern_type": "auth_refresh_loop",
                "severity": "critical",
                "description": f"{len(auth_events)} TOKEN_REFRESHED events with rapid bursts (5+ in 30s) — refresh loop",
                "count": len(auth_events),
            })

    # --- RLS denial spike ---
    # Exclude HEAD requests — they return 0 bytes by design (count-only queries)
    supabase_entries = by_type.get("supabase", [])
    queries = [e for e in supabase_entries if e.get("event_type") == "query"]
    empty_200s = [e for e in queries if e.get("status_code") == 200 and e.get("response_size") == 0 and e.get("method", "").upper() != "HEAD"]
    if len(queries) >= 10 and len(empty_200s) / len(queries) > 0.3:
        patterns.append({
            "pattern_type": "rls_denial_spike",
            "severity": "high",
            "description": f"{len(empty_200s)}/{len(queries)} queries returning empty (RLS denial)",
            "count": len(empty_200s),
        })
    elif len(empty_200s) >= 3:
        patterns.append({
            "pattern_type": "rls_denial",
            "severity": "medium",
            "description": f"{len(empty_200s)} RLS denials (EMPTY_200)",
            "count": len(empty_200s),
        })

    # --- Server errors (5xx) from any source ---
    server_errors = [e for e in entries if e.get("status_code", 0) >= 500]
    if server_errors:
        patterns.append({
            "pattern_type": "server_error",
            "severity": "high",
            "description": f"{len(server_errors)} server errors (5xx)",
            "count": len(server_errors),
        })

    # --- Edge function errors (400 OR timeout from /functions/v1/) ---
    edge_fn_errors = [
        e for e in entries
        if "/functions/v1/" in (e.get("url") or e.get("message") or "")
        and (
            (e.get("status_code", 0) >= 400)  # 400, 401, 500, etc.
            or e.get("status_code") == 0  # network timeout (ERR)
            or e.get("level") == "error"  # any error level
        )
    ]
    if edge_fn_errors:
        # Distinguish timeout vs HTTP error
        timeouts = [e for e in edge_fn_errors if e.get("status_code") == 0 or (e.get("duration_ms", 0) > 30000)]
        http_errors = [e for e in edge_fn_errors if e.get("status_code", 0) >= 400]

        if timeouts:
            patterns.append({
                "pattern_type": "edge_function_timeout",
                "severity": "critical",
                "description": f"{len(timeouts)} edge function timeouts — function exceeded execution limit",
                "count": len(timeouts),
            })
        if http_errors:
            patterns.append({
                "pattern_type": "edge_function_error",
                "severity": "high",
                "description": f"{len(http_errors)} edge function errors ({', '.join(set(str(e.get('status_code')) for e in http_errors))})",
                "count": len(http_errors),
            })

    # --- Browser [ERROR] lines (catch-all for any runtime error) ---
    # Catch things like "[plan-ai] generateX failed: {}"
    browser_errors = [
        e for e in entries
        if e.get("log_type") == "browser"
        and e.get("level") == "error"
        and e.get("event_type") == "console"
        and "vite" not in (e.get("message") or "").lower()  # skip HMR noise
    ]
    if browser_errors:
        patterns.append({
            "pattern_type": "runtime_error",
            "severity": "high",
            "description": f"{len(browser_errors)} runtime errors: {browser_errors[0].get('message', '')[:80]}",
            "count": len(browser_errors),
        })

    # --- Latency degradation ---
    timed_entries = [e for e in supabase_entries if e.get("duration_ms") and e.get("duration_ms") > 0]
    if len(timed_entries) >= 10:
        avg_duration = sum(e["duration_ms"] for e in timed_entries) / len(timed_entries)
        slow = [e for e in timed_entries if e["duration_ms"] > 800]
        if avg_duration > 500 or len(slow) > len(timed_entries) * 0.2:
            patterns.append({
                "pattern_type": "latency_degradation",
                "severity": "high" if avg_duration > 800 else "medium",
                "description": f"Avg latency {avg_duration:.0f}ms, {len(slow)} slow requests (>800ms)",
                "count": len(slow),
            })

    # --- Network errors ---
    net_errors = [e for e in by_type.get("device", []) if "network" in e.get("message", "").lower() or "offline" in e.get("message", "").lower()]
    if len(net_errors) >= 3:
        patterns.append({
            "pattern_type": "network_error",
            "severity": "medium",
            "description": f"{len(net_errors)} network errors in device log",
            "count": len(net_errors),
        })

    # --- New errors (never seen before) ---
    for e in entries:
        if e.get("level") in ("error", "err"):
            fp = _fingerprint(e)
            if fp not in _known_fingerprints:
                _known_fingerprints.add(fp)
                patterns.append({
                    "pattern_type": "new_error",
                    "severity": "medium",
                    "description": f"New error: {e.get('message', '')[:100]}",
                    "count": 1,
                    "fingerprint": fp,
                })
            if fp in _resolved_fingerprints:
                patterns.append({
                    "pattern_type": "regression",
                    "severity": "critical",
                    "description": f"Regression: {e.get('message', '')[:100]}",
                    "count": 1,
                    "fingerprint": fp,
                })

    # --- JS errors ---
    js_errors = [e for e in by_type.get("browser", []) if e.get("level") == "error"]
    if js_errors:
        # Group by fingerprint
        by_fp = defaultdict(list)
        for e in js_errors:
            by_fp[_fingerprint(e)].append(e)

        for fp, group in by_fp.items():
            if len(group) >= 3:
                patterns.append({
                    "pattern_type": "repeated_error",
                    "severity": "medium",
                    "description": f"{len(group)}x: {group[0].get('message', '')[:100]}",
                    "count": len(group),
                    "fingerprint": fp,
                })

    return patterns


# --- Cross-File Correlation ---
def _correlate(entries: list[dict]) -> list[dict]:
    correlations = []

    # Sort by timestamp
    timed = [e for e in entries if e.get("timestamp")]
    timed.sort(key=lambda e: e.get("timestamp", ""))

    # Build time-indexed buckets (500ms windows)
    buckets = defaultdict(list)
    for e in timed:
        try:
            ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            bucket_key = int(ts.timestamp() * 2)  # 500ms buckets
            buckets[bucket_key].append(e)
        except (ValueError, KeyError):
            continue

    for bucket_key, bucket_entries in buckets.items():
        sources = set(e.get("log_type") for e in bucket_entries)
        if len(sources) < 2:
            continue  # Only multi-source buckets are interesting

        # Rule: Auth failure + browser redirect
        has_auth_fail = any(e.get("status_code") in (401, 403) for e in bucket_entries)
        has_redirect = any("redirect" in e.get("message", "").lower() or "login" in e.get("message", "").lower() for e in bucket_entries)
        if has_auth_fail and has_redirect:
            correlations.append({
                "rule_name": "Auth Cascade",
                "severity": "critical",
                "description": "Auth failure causing redirect — possible auth cascade",
                "sources": list(sources),
            })

        # Rule: EMPTY_200 + empty UI state
        has_empty_200 = any(e.get("status_code") == 200 and e.get("response_size") == 0 for e in bucket_entries)
        has_empty_ui = any("undefined" in e.get("message", "").lower() or "null" in e.get("message", "").lower() or "empty" in e.get("message", "").lower() for e in bucket_entries)
        if has_empty_200 and has_empty_ui:
            correlations.append({
                "rule_name": "RLS Denial Chain",
                "severity": "high",
                "description": "RLS denial causing empty UI state",
                "sources": list(sources),
            })

        # Rule: Slow query + stale/refetch
        has_slow = any(e.get("duration_ms", 0) > 1000 for e in bucket_entries)
        has_stale = any("stale" in e.get("message", "").lower() or "refetch" in e.get("message", "").lower() for e in bucket_entries)
        if has_slow and has_stale:
            correlations.append({
                "rule_name": "Slow Query Impact",
                "severity": "medium",
                "description": "Slow DB query causing React Query staleness",
                "sources": list(sources),
            })

    return correlations


# --- Log Sync (SSH tail from Muddy) ---
_sync_processes = {}


BUILDS_REGISTRY = os.path.expanduser("~/.buildrunner/cluster-builds.json")
SESSIONS_URL = "http://127.0.0.1:4400/api/sessions"


def _discover_projects() -> list[str]:
    """Discover ACTIVE projects only — from build registry + live Claude sessions."""
    active = set()

    # Source 1: Build registry — running/pending builds
    try:
        with open(BUILDS_REGISTRY) as f:
            reg = json.load(f)
        for bid, build in reg.get("builds", {}).items():
            if build.get("status") in ("running", "pending", "registered"):
                project = build.get("project")
                if project:
                    active.add(project)
    except Exception:
        pass

    # Source 2: Active Claude Code sessions (ad-hoc fixes)
    try:
        import urllib.request
        resp = urllib.request.urlopen(SESSIONS_URL, timeout=3)
        data = json.loads(resp.read())
        for session in data.get("sessions", []):
            project = session.get("project")
            if project and project != "--":
                active.add(project)
    except Exception:
        pass

    # Validate: only include projects that actually have .buildrunner/ dirs
    projects_dir = Path(PROJECTS_DIR)
    validated = [p for p in active if (projects_dir / p / ".buildrunner").exists()]

    return validated if validated else []


_known_projects: set[str] = set()
_alerted_fingerprints: set[str] = set()

CLUSTER_CHECK = os.path.expanduser("~/.buildrunner/scripts/cluster-check.sh")


# --- Alert + Auto-Fix ---
ALERTS_DIR = os.path.expanduser("~/.buildrunner/alerts")
DASHBOARD_EVENT_URL = "http://127.0.0.1:4400/api/events"


def _push_alert_to_dashboard(pattern: dict):
    """Write alert JSON to ~/.buildrunner/alerts/ for dashboard monitor workspace,
    and emit an event to the dashboard event server."""
    try:
        os.makedirs(ALERTS_DIR, exist_ok=True)
        fp = pattern.get("fingerprint") or hashlib.md5(
            f"{pattern['pattern_type']}:{pattern.get('description', '')}".encode()
        ).hexdigest()[:12]
        alert_data = {
            "type": "log_analysis",
            "node": "Muddy",
            "severity": pattern["severity"],
            "message": f"{pattern['pattern_type']}: {pattern['description']}",
            "pattern_type": pattern["pattern_type"],
            "count": pattern.get("count", 1),
            "fingerprint": fp,
            "timestamp": datetime.now().isoformat(),
        }
        alert_file = os.path.join(ALERTS_DIR, f"log-{fp}.json")
        with open(alert_file, "w") as f:
            json.dump(alert_data, f)
        print(f"  [ALERT] dashboard alert: {alert_file}")
    except Exception as e:
        print(f"  [ALERT] dashboard alert write failed: {e}")

    # Emit event to dashboard event server
    try:
        import urllib.request
        event = json.dumps({
            "type": "log.analysis.alert",
            "source": "log-analysis",
            "data": json.dumps({
                "pattern_type": pattern["pattern_type"],
                "severity": pattern["severity"],
                "description": pattern.get("description", ""),
                "count": pattern.get("count", 1),
            }),
        }).encode()
        req = urllib.request.Request(
            DASHBOARD_EVENT_URL,
            data=event,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3)
        print(f"  [ALERT] dashboard event emitted: {pattern['pattern_type']}")
    except Exception as e:
        print(f"  [ALERT] dashboard event emit failed: {e}")


def _clear_resolved_dashboard_alerts():
    """Remove alert files for patterns that have been resolved."""
    try:
        if not os.path.exists(ALERTS_DIR):
            return
        processed_dir = os.path.join(ALERTS_DIR, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        for f in os.listdir(ALERTS_DIR):
            if not f.startswith("log-") or not f.endswith(".json"):
                continue
            filepath = os.path.join(ALERTS_DIR, f)
            try:
                with open(filepath) as fh:
                    alert = json.load(fh)
                fp = alert.get("fingerprint", "")
                if fp in _resolved_fingerprints:
                    dest = os.path.join(processed_dir, f"remediated-{f}")
                    os.rename(filepath, dest)
                    print(f"  [ALERT] resolved alert moved: {f}")
            except Exception:
                pass
    except Exception as e:
        print(f"  [ALERT] cleanup failed: {e}")


def _send_macos_notification(pattern: dict):
    """Fire macOS notification for critical/high patterns."""
    try:
        title = f"BR3: {pattern['pattern_type']}"
        msg = pattern["description"][:100]
        subprocess.Popen(
            ["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Basso"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"  [ALERT] macOS notification: {title}")
    except Exception as e:
        print(f"  [ALERT] notification failed: {e}")


def _push_alert_to_walter(pattern: dict):
    """Push alert to Walter so it shows in developer brief alongside test results."""
    try:
        walter_url = subprocess.run(
            [CLUSTER_CHECK, "test-runner"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        if walter_url:
            import urllib.request
            data = json.dumps(pattern).encode()
            req = urllib.request.Request(
                f"{walter_url}/api/alert",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
            print(f"  [ALERT] pushed to Walter: {pattern['pattern_type']}")
    except Exception as e:
        print(f"  [ALERT] Walter push failed: {e}")


def _attempt_auto_fix(pattern: dict, entries: list[dict]):
    """Attempt automatic fixes for known error patterns."""
    ptype = pattern["pattern_type"]
    desc = pattern.get("description", "")

    # --- Rule 1: Edge function "Unknown action" → auto-deploy ---
    if ptype == "edge_function_error":
        for e in entries:
            msg = e.get("message", "")
            if "Unknown action:" in msg:
                action_match = re.search(r"Unknown action:\s*(\w+)", msg)
                fn_url = e.get("url", "")
                fn_match = re.search(r"/functions/v1/([\w-]+)", fn_url or msg)
                if action_match and fn_match:
                    _auto_fix_deploy_edge_function(fn_match.group(1), action_match.group(1))
                    return

    # --- Rule 2: Edge function timeout → redeploy (may fix cold start / stuck deploy) ---
    if ptype == "edge_function_timeout":
        for e in entries:
            url = e.get("url", "")
            fn_match = re.search(r"/functions/v1/([\w-]+)", url)
            if fn_match:
                fn_name = fn_match.group(1)
                print(f"  [AUTO-FIX] Edge function timeout on '{fn_name}' — redeploying to clear stale worker...")
                _auto_fix_redeploy_edge_function(fn_name)
                return

    # --- Rule 3: Runtime error matching "failed: {}" → likely empty error body, check edge fn ---
    if ptype == "runtime_error" and "failed: {}" in desc:
        # Empty error body usually means edge function returned non-JSON or timed out
        for e in entries:
            msg = e.get("message", "")
            fn_name_match = re.search(r"generate(\w+)\s+failed", msg)
            if fn_name_match:
                print(f"  [AUTO-FIX] Runtime error with empty body — likely edge function issue. Check Supabase dashboard logs.")
                return

    # --- Rule 4: Auth refresh loop → log for investigation ---
    if ptype == "auth_refresh_loop" and pattern.get("count", 0) > 50:
        print(f"  [AUTO-FIX] Auth refresh loop detected ({pattern['count']}x) — needs manual investigation")
        return


def _auto_fix_deploy_edge_function(fn_name: str, action_name: str):
    """Auto-deploy an edge function when 'Unknown action' is detected but code exists locally."""
    print(f"  [AUTO-FIX] Checking if '{action_name}' exists in local edge function '{fn_name}'...")

    # Search all BR3 projects for the edge function source
    projects_dir = Path(PROJECTS_DIR)
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        index_path = project_dir / "supabase" / "functions" / fn_name / "index.ts"
        if not index_path.exists():
            continue

        # Check if the action exists in the local code
        try:
            code = index_path.read_text()
        except Exception:
            continue

        if f"'{action_name}'" in code or f'"{action_name}"' in code:
            print(f"  [AUTO-FIX] Found '{action_name}' in {index_path} — deploying...")
            result = subprocess.run(
                ["supabase", "functions", "deploy", fn_name, "--no-verify-jwt"],
                capture_output=True, text=True, cwd=str(project_dir), timeout=120,
                env={**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"},
            )
            if result.returncode == 0:
                print(f"  [AUTO-FIX] ✓ Deployed {fn_name} successfully")
                _send_macos_notification({
                    "pattern_type": "auto_fix_applied",
                    "severity": "info",
                    "description": f"Auto-deployed {fn_name} (missing action: {action_name})",
                })
            else:
                print(f"  [AUTO-FIX] ✗ Deploy failed: {result.stderr[:200]}")
            return
        else:
            print(f"  [AUTO-FIX] '{action_name}' NOT found in {index_path} — code is missing, cannot auto-fix")
            return

    print(f"  [AUTO-FIX] No edge function '{fn_name}' found in any project")


def _auto_fix_redeploy_edge_function(fn_name: str):
    """Redeploy an edge function to clear stale workers (fixes some timeout issues)."""
    projects_dir = Path(PROJECTS_DIR)
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        fn_dir = project_dir / "supabase" / "functions" / fn_name
        if not fn_dir.exists():
            continue

        print(f"  [AUTO-FIX] Redeploying '{fn_name}' from {project_dir}...")
        result = subprocess.run(
            ["supabase", "functions", "deploy", fn_name, "--no-verify-jwt"],
            capture_output=True, text=True, cwd=str(project_dir), timeout=120,
            env={**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"},
        )
        if result.returncode == 0:
            print(f"  [AUTO-FIX] ✓ Redeployed {fn_name}")
            _send_macos_notification({
                "pattern_type": "auto_fix_applied",
                "severity": "info",
                "description": f"Redeployed {fn_name} after timeout",
            })
        else:
            print(f"  [AUTO-FIX] ✗ Redeploy failed: {result.stderr[:200]}")
        return

    print(f"  [AUTO-FIX] No edge function '{fn_name}' found in any project")


# --- Analysis Loop ---
def _analysis_loop():
    global _analyzing, _last_analysis_time, _active_patterns

    while True:
        time.sleep(POLL_INTERVAL)

        if _analyzing:
            continue

        _analyzing = True
        try:
            all_entries = []
            projects = _discover_projects()

            # Read logs directly from local project directories
            for project in projects:
                if project not in _known_projects:
                    _known_projects.add(project)

                project_dir = Path(PROJECTS_DIR) / project / ".buildrunner"
                if not project_dir.exists():
                    continue

                # Skip stale logs (not modified in last 24 hours)
                max_age_hours = 24
                now = time.time()

                supa_log = project_dir / "supabase.log"
                if supa_log.exists() and (now - supa_log.stat().st_mtime) < max_age_hours * 3600:
                    entries = _parse_supabase_log(str(supa_log))
                    for e in entries:
                        e["project"] = project
                    all_entries.extend(entries)

                browser_log = project_dir / "browser.log"
                if browser_log.exists() and (now - browser_log.stat().st_mtime) < max_age_hours * 3600:
                    entries = _parse_browser_log(str(browser_log))
                    for e in entries:
                        e["project"] = project
                    all_entries.extend(entries)

                for logname, logtype in [("device.log", "device"), ("query.log", "query")]:
                    logpath = project_dir / logname
                    if logpath.exists() and (now - logpath.stat().st_mtime) < max_age_hours * 3600:
                        entries = _parse_generic_log(str(logpath), logtype)
                        for e in entries:
                            e["project"] = project
                        all_entries.extend(entries)

            if not all_entries:
                _analyzing = False
                continue

            # Detect patterns
            patterns = _detect_patterns(all_entries)

            # Cross-file correlation
            correlations = _correlate(all_entries)

            # Store patterns — deduplicate by pattern_type + project
            conn = _get_db()
            # Clear non-fingerprinted patterns each cycle (they're recalculated)
            conn.execute("DELETE FROM patterns WHERE fingerprint IS NULL AND resolved = 0")
            for p in patterns:
                fp = p.get("fingerprint") or hashlib.md5(f"{p['pattern_type']}:{p.get('description','')}".encode()).hexdigest()[:12]
                existing = conn.execute("SELECT id FROM patterns WHERE fingerprint = ? AND resolved = 0", (fp,)).fetchone()
                if existing:
                    conn.execute("UPDATE patterns SET count = ?, last_seen = datetime('now'), description = ? WHERE id = ?",
                                 (p.get("count", 1), p["description"], existing["id"]))
                else:
                    conn.execute(
                        """INSERT INTO patterns (pattern_type, severity, description, count, fingerprint, details)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (p["pattern_type"], p["severity"], p["description"],
                         p.get("count", 1), fp, json.dumps(p))
                    )

            for c in correlations:
                conn.execute(
                    """INSERT INTO correlations (rule_name, severity, description, sources, details)
                       VALUES (?, ?, ?, ?, ?)""",
                    (c["rule_name"], c["severity"], c["description"],
                     json.dumps(c.get("sources", [])), json.dumps(c))
                )

            # Retain only last 7 days
            conn.execute("DELETE FROM patterns WHERE last_seen < datetime('now', '-7 days') AND resolved = 1")
            conn.execute("DELETE FROM correlations WHERE timestamp < datetime('now', '-7 days')")

            conn.commit()
            conn.close()

            _active_patterns = patterns
            _last_analysis_time = time.time()

            if patterns:
                print(f"Analysis: {len(patterns)} patterns, {len(correlations)} correlations")

            # --- Clean up resolved alerts from dashboard ---
            _clear_resolved_dashboard_alerts()

            # --- Alert + Auto-Fix for critical/high patterns ---
            for p in patterns:
                fp = p.get("fingerprint") or hashlib.md5(f"{p['pattern_type']}:{p.get('description','')}".encode()).hexdigest()[:12]
                if p["severity"] in ("critical", "high") and fp not in _alerted_fingerprints:
                    _alerted_fingerprints.add(fp)
                    _send_macos_notification(p)
                    _push_alert_to_walter(p)
                    _push_alert_to_dashboard(p)
                    _attempt_auto_fix(p, all_entries)

        except Exception as e:
            print(f"Analysis error: {e}")
        finally:
            _analyzing = False


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=_analysis_loop, daemon=True)
    t.start()


# --- API Endpoints ---
@app.get("/api/logs/analyze")
async def analyze(project: Optional[str] = None):
    """Get pre-analyzed log summary — designed for SessionStart hook injection."""
    conn = _get_db()

    if project:
        patterns = conn.execute(
            "SELECT * FROM patterns WHERE resolved = 0 ORDER BY severity, count DESC"
        ).fetchall()
    else:
        patterns = conn.execute(
            "SELECT * FROM patterns WHERE resolved = 0 ORDER BY severity, count DESC LIMIT 20"
        ).fetchall()

    conn.close()

    # Build token-efficient summary
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_patterns = sorted([dict(p) for p in patterns], key=lambda p: severity_order.get(p["severity"], 9))

    severity_icons = {"critical": "!!!", "high": "!!", "medium": "!", "low": ""}

    summary_lines = []
    for p in sorted_patterns[:10]:
        icon = severity_icons.get(p["severity"], "")
        summary_lines.append(f"{icon} {p['pattern_type']}: {p['description']} ({p['count']}x)")

    return {
        "summary": "\n".join(summary_lines) if summary_lines else "No active patterns",
        "patterns": sorted_patterns[:10],
        "total_patterns": len(patterns),
        "last_analysis": _last_analysis_time,
    }


@app.get("/api/logs/patterns")
async def get_patterns(resolved: bool = False):
    """Get active or resolved patterns."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM patterns WHERE resolved = ? ORDER BY severity, last_seen DESC",
        (1 if resolved else 0,)
    ).fetchall()
    conn.close()
    return {"patterns": [dict(r) for r in rows]}


@app.get("/api/logs/correlations")
async def get_correlations(limit: int = 20):
    """Get cross-file event correlations."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM correlations ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {"correlations": [dict(r) for r in rows]}


@app.get("/api/logs/search")
async def search_logs(q: str, limit: int = 20):
    """Full-text search across all log entries."""
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT l.* FROM log_entries l
               JOIN log_fts f ON l.id = f.rowid
               WHERE log_fts MATCH ? ORDER BY l.timestamp DESC LIMIT ?""",
            (q, limit)
        ).fetchall()
    except Exception:
        rows = conn.execute(
            "SELECT * FROM log_entries WHERE message LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{q}%", limit)
        ).fetchall()
    conn.close()
    return {"results": [dict(r) for r in rows]}


@app.post("/api/logs/resolve")
async def resolve_pattern(fingerprint: str):
    """Mark a pattern as resolved (for regression detection)."""
    _resolved_fingerprints.add(fingerprint)
    conn = _get_db()
    conn.execute("UPDATE patterns SET resolved = 1 WHERE fingerprint = ?", (fingerprint,))
    conn.commit()
    conn.close()
    return {"status": "resolved"}


@app.post("/api/migration/dryrun")
async def migration_dryrun(project: Optional[str] = None):
    """Run migrations against local Supabase sandbox. Returns pass/fail."""
    # Check if Supabase is available
    try:
        result = subprocess.run(
            ["supabase", "status"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"status": "supabase_not_running", "message": "Run 'supabase start' on Crawford first"}
    except Exception:
        return {"status": "supabase_not_available", "message": "Supabase CLI not found"}

    # Run db reset (applies all migrations from scratch)
    try:
        result = subprocess.run(
            ["supabase", "db", "reset"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return {"status": "pass", "message": "All migrations applied successfully"}
        else:
            return {
                "status": "fail",
                "message": "Migration failed",
                "error": result.stderr[-500:] if result.stderr else result.stdout[-500:],
            }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Migration timed out after 120s"}


@app.get("/api/logs/stats")
async def log_stats():
    """Log analysis statistics."""
    return {
        "analyzing": _analyzing,
        "last_analysis": _last_analysis_time,
        "active_patterns": len(_active_patterns),
        "known_fingerprints": len(_known_fingerprints),
        "resolved_fingerprints": len(_resolved_fingerprints),
        "projects_monitored": list(_known_projects),
        "mode": "local",
    }
