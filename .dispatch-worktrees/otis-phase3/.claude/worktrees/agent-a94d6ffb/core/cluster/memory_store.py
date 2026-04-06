"""
BR3 Cluster — Lockwood Memory Store
SQLite-backed persistent memory for build history, commit summaries,
test results, log patterns, architecture notes, and session state.

Pulls data from Muddy (M5) until dedicated nodes (Walter, Crawford) exist.
"""

import os
import sqlite3
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional


DB_PATH = os.environ.get("MEMORY_DB", os.path.expanduser("~/.lockwood/memory.db"))
REPOS_DIR = os.environ.get("REPOS_DIR", os.path.expanduser("~/repos"))
MUDDY_HOST = os.environ.get("MUDDY_HOST", "10.0.1.100")


def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS build_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            build_name TEXT NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_seconds REAL,
            failure_reason TEXT,
            files_changed TEXT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS commits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            hash TEXT NOT NULL UNIQUE,
            message TEXT NOT NULL,
            author TEXT,
            timestamp TEXT NOT NULL,
            files_changed TEXT,
            indexed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            passed INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            failures TEXT,
            duration_seconds REAL,
            source TEXT NOT NULL DEFAULT 'muddy',
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS log_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            description TEXT NOT NULL,
            log_file TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 1,
            first_seen TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen TEXT NOT NULL DEFAULT (datetime('now')),
            resolved INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS architecture_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS session_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            branch TEXT,
            phase TEXT,
            build_name TEXT,
            working_on TEXT,
            open_todos TEXT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_build_project ON build_history(project);
        CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo);
        CREATE INDEX IF NOT EXISTS idx_test_project ON test_results(project);
        CREATE INDEX IF NOT EXISTS idx_patterns_type ON log_patterns(pattern_type);
    """)
    conn.commit()


# --- Build History ---

def record_build_phase(project: str, build_name: str, phase: str,
                       status: str, duration: float = None,
                       failure_reason: str = None, files_changed: list = None):
    conn = _get_db()
    conn.execute(
        """INSERT INTO build_history (project, build_name, phase, status,
           duration_seconds, failure_reason, files_changed)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (project, build_name, phase, status, duration, failure_reason,
         json.dumps(files_changed) if files_changed else None)
    )
    conn.commit()
    conn.close()


def get_build_history(project: str = None, limit: int = 50) -> list[dict]:
    conn = _get_db()
    if project:
        rows = conn.execute(
            "SELECT * FROM build_history WHERE project = ? ORDER BY timestamp DESC LIMIT ?",
            (project, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM build_history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def predict_phase(project: str, phase_pattern: str) -> dict:
    """Predict difficulty of a phase based on history of similar phases."""
    conn = _get_db()
    rows = conn.execute(
        """SELECT status, duration_seconds, failure_reason
           FROM build_history
           WHERE project = ? AND phase LIKE ?
           ORDER BY timestamp DESC LIMIT 20""",
        (project, f"%{phase_pattern}%")
    ).fetchall()
    conn.close()

    if not rows:
        return {"prediction": "no_data", "similar_phases": 0}

    total = len(rows)
    failures = sum(1 for r in rows if r["status"] == "failed")
    avg_duration = sum(r["duration_seconds"] or 0 for r in rows) / total
    failure_reasons = [r["failure_reason"] for r in rows if r["failure_reason"]]

    return {
        "prediction": "high_risk" if failures / total > 0.3 else "normal",
        "similar_phases": total,
        "failure_rate": round(failures / total, 2),
        "avg_duration_seconds": round(avg_duration, 1),
        "common_failures": list(set(failure_reasons))[:5],
    }


# --- Commit Indexing ---

def ingest_commits(repo_name: str, repo_path: str, count: int = 100):
    """Pull recent commits from a repo and store them."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--format=%H|||%s|||%an|||%aI", "--"],
            capture_output=True, text=True, cwd=repo_path, timeout=10
        )
        if result.returncode != 0:
            return 0
    except Exception:
        return 0

    conn = _get_db()
    inserted = 0
    for line in result.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) != 4:
            continue
        hash_, message, author, timestamp = parts

        try:
            # Get files changed in this commit
            files_result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", hash_],
                capture_output=True, text=True, cwd=repo_path, timeout=5
            )
            files = files_result.stdout.strip().split("\n") if files_result.returncode == 0 else []
        except Exception:
            files = []

        try:
            conn.execute(
                """INSERT OR IGNORE INTO commits (repo, hash, message, author, timestamp, files_changed)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (repo_name, hash_, message, author, timestamp, json.dumps(files))
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return inserted


def search_commits(query: str, repo: str = None, limit: int = 20) -> list[dict]:
    """Search commits by message content."""
    conn = _get_db()
    if repo:
        rows = conn.execute(
            """SELECT * FROM commits WHERE repo = ? AND message LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (repo, f"%{query}%", limit)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM commits WHERE message LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (f"%{query}%", limit)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Test Results ---

def ingest_test_results_from_muddy(project: str, project_path: str):
    """Pull test results from a project's .buildrunner/ on the local filesystem."""
    results_file = Path(project_path) / ".buildrunner" / "test-results.json"
    if not results_file.exists():
        return None

    try:
        data = json.loads(results_file.read_text())
    except Exception:
        return None

    conn = _get_db()
    conn.execute(
        """INSERT INTO test_results (project, passed, failed, skipped, failures, duration_seconds, source)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (project, data.get("passed", 0), data.get("failed", 0), data.get("skipped", 0),
         json.dumps(data.get("failures", [])), data.get("duration"), "muddy")
    )
    conn.commit()
    conn.close()
    return data


def get_latest_test_results(project: str = None) -> list[dict]:
    conn = _get_db()
    if project:
        rows = conn.execute(
            """SELECT * FROM test_results WHERE project = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (project,)
        ).fetchall()
    else:
        # Latest per project
        rows = conn.execute(
            """SELECT * FROM test_results WHERE id IN (
                 SELECT MAX(id) FROM test_results GROUP BY project
               ) ORDER BY timestamp DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Log Patterns ---

def ingest_log_patterns(log_file: str, log_path: str):
    """Analyze a log file for common patterns."""
    path = Path(log_path)
    if not path.exists():
        return []

    try:
        lines = path.read_text(errors="replace").split("\n")
    except Exception:
        return []

    patterns_found = []
    error_counts = {}

    for line in lines[-500:]:  # Last 500 lines
        lower = line.lower()
        if "401" in lower or "unauthorized" in lower:
            error_counts["auth_failure"] = error_counts.get("auth_failure", 0) + 1
        elif "403" in lower or "forbidden" in lower or "rls" in lower:
            error_counts["rls_denial"] = error_counts.get("rls_denial", 0) + 1
        elif "500" in lower or "internal server error" in lower:
            error_counts["server_error"] = error_counts.get("server_error", 0) + 1
        elif "timeout" in lower:
            error_counts["timeout"] = error_counts.get("timeout", 0) + 1
        elif "failed to fetch" in lower or "network" in lower:
            error_counts["network_error"] = error_counts.get("network_error", 0) + 1

    conn = _get_db()
    for pattern_type, count in error_counts.items():
        if count >= 3:  # Only store if pattern appears 3+ times
            existing = conn.execute(
                "SELECT id FROM log_patterns WHERE pattern_type = ? AND log_file = ? AND resolved = 0",
                (pattern_type, log_file)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE log_patterns SET count = ?, last_seen = datetime('now') WHERE id = ?",
                    (count, existing["id"])
                )
            else:
                conn.execute(
                    """INSERT INTO log_patterns (pattern_type, description, log_file, count)
                       VALUES (?, ?, ?, ?)""",
                    (pattern_type, f"{count}x {pattern_type} in {log_file}", log_file, count)
                )
            patterns_found.append({"type": pattern_type, "count": count, "file": log_file})

    conn.commit()
    conn.close()
    return patterns_found


def get_active_patterns() -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM log_patterns WHERE resolved = 0 ORDER BY last_seen DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Architecture Notes ---

def save_note(topic: str, content: str, project: str = None, source: str = "manual"):
    conn = _get_db()
    conn.execute(
        "INSERT INTO architecture_notes (project, topic, content, source) VALUES (?, ?, ?, ?)",
        (project, topic, content, source)
    )
    conn.commit()
    conn.close()


def search_notes(query: str, project: str = None) -> list[dict]:
    conn = _get_db()
    if project:
        rows = conn.execute(
            """SELECT * FROM architecture_notes
               WHERE project = ? AND (topic LIKE ? OR content LIKE ?)
               ORDER BY timestamp DESC LIMIT 20""",
            (project, f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM architecture_notes
               WHERE topic LIKE ? OR content LIKE ?
               ORDER BY timestamp DESC LIMIT 20""",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Session State ---

def save_session_state(project: str, branch: str = None, phase: str = None,
                       build_name: str = None, working_on: str = None,
                       open_todos: list = None):
    conn = _get_db()
    conn.execute(
        """INSERT INTO session_state (project, branch, phase, build_name, working_on, open_todos)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (project, branch, phase, build_name, working_on,
         json.dumps(open_todos) if open_todos else None)
    )
    conn.commit()
    conn.close()


def get_last_session(project: str) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM session_state WHERE project = ? ORDER BY timestamp DESC LIMIT 1",
        (project,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Full Context Brief ---

def generate_brief(project: str) -> dict:
    """Generate a full context packet for a Claude session."""
    brief = {
        "project": project,
        "generated_at": datetime.now().isoformat(),
    }

    # Last session
    session = get_last_session(project)
    if session:
        brief["last_session"] = {
            "branch": session.get("branch"),
            "phase": session.get("phase"),
            "build": session.get("build_name"),
            "working_on": session.get("working_on"),
            "todos": json.loads(session["open_todos"]) if session.get("open_todos") else [],
            "when": session.get("timestamp"),
        }

    # Recent build history
    history = get_build_history(project, limit=10)
    if history:
        brief["recent_builds"] = [
            {
                "phase": h["phase"],
                "status": h["status"],
                "duration": h.get("duration_seconds"),
                "failure": h.get("failure_reason"),
                "when": h["timestamp"],
            }
            for h in history
        ]

    # Latest test results
    tests = get_latest_test_results(project)
    if tests:
        t = tests[0]
        brief["test_results"] = {
            "passed": t["passed"],
            "failed": t["failed"],
            "failures": json.loads(t["failures"]) if t.get("failures") else [],
            "when": t["timestamp"],
        }

    # Active log patterns
    patterns = get_active_patterns()
    if patterns:
        brief["log_patterns"] = [
            {"type": p["pattern_type"], "count": p["count"],
             "file": p["log_file"], "last_seen": p["last_seen"]}
            for p in patterns
        ]

    # Recent architecture notes
    notes = search_notes("", project)[:5]
    if notes:
        brief["architecture_notes"] = [
            {"topic": n["topic"], "content": n["content"][:200], "when": n["timestamp"]}
            for n in notes
        ]

    return brief
