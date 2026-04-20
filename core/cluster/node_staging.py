"""
BR3 Cluster — Node 4: Lomax (Forge)
Staging server: build validation, project serving, Netlify preview deploys.

Run: uvicorn core.cluster.node_staging:app --host 0.0.0.0 --port 8100
"""

import os
import time
import json
import signal
import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from core.cluster.base_service import create_app

# --- Config ---
PROJECTS_DIR = os.environ.get("PROJECTS_DIR", os.path.expanduser("~/repos"))
DB_PATH = os.environ.get("STAGING_DB", os.path.expanduser("~/.lomax/builds.db"))
BUILD_INTERVAL = int(os.environ.get("BUILD_INTERVAL", "120"))  # seconds between build checks
LOCKWOOD_URL = os.environ.get("LOCKWOOD_URL", "http://10.0.1.101:8100")

# --- App ---
app = create_app(role="staging-server", version="0.1.0")

# --- State ---
_building = False
_file_mtimes: dict[str, float] = {}  # project -> latest mtime
_build_cache: dict[str, dict] = {}  # project -> last build result


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
        CREATE TABLE IF NOT EXISTS builds (
            build_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            git_sha TEXT,
            git_branch TEXT,
            passed INTEGER DEFAULT 0,
            tsc_ok INTEGER DEFAULT 0,
            vite_ok INTEGER DEFAULT 0,
            duration_sec REAL DEFAULT 0,
            tsc_errors TEXT,
            vite_errors TEXT,
            trigger TEXT DEFAULT 'watch'
        );
        CREATE TABLE IF NOT EXISTS previews (
            preview_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            preview_url TEXT,
            deploy_id TEXT,
            ok INTEGER DEFAULT 0,
            output TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_builds_project ON builds(project);
        CREATE INDEX IF NOT EXISTS idx_builds_ts ON builds(timestamp);
        CREATE INDEX IF NOT EXISTS idx_previews_project ON previews(project);
    """)
    conn.commit()


# --- Project Discovery ---
def _discover_projects() -> list[dict]:
    """Find all directories in PROJECTS_DIR with a package.json."""
    projects = []
    projects_path = Path(PROJECTS_DIR)
    if not projects_path.exists():
        return projects

    for d in sorted(projects_path.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        pkg = d / "package.json"
        if not pkg.exists():
            continue

        info = {"name": d.name.lower(), "path": str(d)}

        # Read package.json for metadata
        try:
            pkg_data = json.loads(pkg.read_text())
            info["display_name"] = pkg_data.get("name", d.name)
            scripts = pkg_data.get("scripts", {})
            info["has_dev"] = "dev" in scripts
            info["has_build"] = "build" in scripts
            info["has_tsc"] = (
                "tsc" in scripts
                or (d / "tsconfig.json").exists()
            )
        except (json.JSONDecodeError, OSError):
            info["display_name"] = d.name
            info["has_dev"] = False
            info["has_build"] = False
            info["has_tsc"] = False

        projects.append(info)

    return projects


# --- Process Group Helper (prevents zombie processes on timeout) ---
def _run_with_process_group(cmd: list[str], cwd: str, timeout: int, env: dict) -> tuple[str, str, int, bool]:
    """Run command in a new process group. Kills entire group on timeout.

    Returns: (stdout, stderr, returncode, timed_out)
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        start_new_session=True,
        text=True
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout, stderr, proc.returncode, False
    except subprocess.TimeoutExpired:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(0.5)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            stdout, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = "", ""
        return stdout, stderr, -1, True


# --- Git Helpers ---
def _git_sha(repo_path: str) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        ).stdout.strip()
    except Exception:
        return ""


def _git_branch(repo_path: str) -> str:
    try:
        return subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        ).stdout.strip()
    except Exception:
        return ""


# --- Build Validation ---
def _run_tsc(repo_path: str) -> dict:
    """Run tsc --noEmit. Returns {ok, errors, output}."""
    tsconfig = Path(repo_path) / "tsconfig.json"
    if not tsconfig.exists():
        return {"ok": True, "errors": [], "output": "no tsconfig.json — skipped"}

    env = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}
    stdout, stderr, returncode, timed_out = _run_with_process_group(
        ["npx", "tsc", "--noEmit"], repo_path, timeout=120, env=env
    )

    if timed_out:
        return {"ok": False, "errors": ["tsc timed out (120s)"], "output": "timeout"}

    output = stdout + stderr
    errors = []
    for line in output.splitlines():
        if ": error TS" in line:
            errors.append(line.strip())
    return {
        "ok": returncode == 0,
        "errors": errors,
        "output": output[-2000:] if output else "",
    }


def _run_vite_build(repo_path: str) -> dict:
    """Run vite build (dry run). Returns {ok, errors, output}."""
    pkg = Path(repo_path) / "package.json"
    if not pkg.exists():
        return {"ok": True, "errors": [], "output": "no package.json — skipped"}

    try:
        pkg_data = json.loads(pkg.read_text())
        if "build" not in pkg_data.get("scripts", {}):
            return {"ok": True, "errors": [], "output": "no build script — skipped"}
    except (json.JSONDecodeError, OSError):
        return {"ok": False, "errors": ["cannot read package.json"], "output": ""}

    env = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}
    stdout, stderr, returncode, timed_out = _run_with_process_group(
        ["npm", "run", "build"], repo_path, timeout=180, env=env
    )

    if timed_out:
        return {"ok": False, "errors": ["vite build timed out (180s)"], "output": "timeout"}

    output = stdout + stderr
    errors = []
    for line in output.splitlines():
        lower = line.lower()
        if "error" in lower and ("ts(" in lower or "vite" in lower or "rollup" in lower):
            errors.append(line.strip())
        elif line.startswith("ERROR") or line.startswith("error"):
            errors.append(line.strip())
    return {
        "ok": returncode == 0,
        "errors": errors,
        "output": output[-2000:] if output else "",
    }


def _validate_project(project_path: str, project_name: str, trigger: str = "watch") -> dict:
    """Run full build validation (tsc + vite build) for a project."""
    start = time.time()
    sha = _git_sha(project_path)
    branch = _git_branch(project_path)

    tsc = _run_tsc(project_path)
    vite = _run_vite_build(project_path)

    duration = round(time.time() - start, 1)
    passed = tsc["ok"] and vite["ok"]

    result = {
        "project": project_name,
        "passed": passed,
        "tsc_ok": tsc["ok"],
        "vite_ok": vite["ok"],
        "tsc_errors": tsc["errors"],
        "vite_errors": vite["errors"],
        "duration_sec": duration,
        "git_sha": sha,
        "git_branch": branch,
        "timestamp": time.time(),
        "trigger": trigger,
    }

    # Store in DB
    try:
        conn = _get_db()
        conn.execute(
            """INSERT INTO builds (project, git_sha, git_branch, passed, tsc_ok, vite_ok,
               duration_sec, tsc_errors, vite_errors, trigger)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_name, sha, branch, int(passed), int(tsc["ok"]), int(vite["ok"]),
             duration, json.dumps(tsc["errors"]), json.dumps(vite["errors"]), trigger)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB write error for {project_name}: {e}")

    # Update cache
    _build_cache[project_name] = result

    return result


def _has_changes(project_path: str, project_name: str) -> bool:
    """Check if any source files changed since last check."""
    src_dirs = [
        Path(project_path) / "src",
        Path(project_path) / "app",
        Path(project_path) / "lib",
    ]
    config_files = [
        Path(project_path) / "tsconfig.json",
        Path(project_path) / "vite.config.ts",
        Path(project_path) / "package.json",
    ]

    latest_mtime = 0.0

    for src_dir in src_dirs:
        if not src_dir.exists():
            continue
        for f in src_dir.rglob("*"):
            if f.is_file() and f.suffix in {".ts", ".tsx", ".js", ".jsx", ".vue", ".css"}:
                try:
                    mt = f.stat().st_mtime
                    if mt > latest_mtime:
                        latest_mtime = mt
                except OSError:
                    continue

    for cf in config_files:
        if cf.exists():
            try:
                mt = cf.stat().st_mtime
                if mt > latest_mtime:
                    latest_mtime = mt
            except OSError:
                continue

    prev = _file_mtimes.get(project_name, 0.0)
    _file_mtimes[project_name] = latest_mtime
    return latest_mtime > prev and prev > 0  # skip first run


# --- Netlify Preview Deploy ---
def _deploy_preview(project_path: str, project_name: str) -> dict:
    """Run netlify deploy --dir=dist and return the preview URL."""
    dist_dir = Path(project_path) / "dist"

    # Build first if dist doesn't exist or is stale
    if not dist_dir.exists():
        build_result = _run_vite_build(project_path)
        if not build_result["ok"]:
            return {
                "ok": False,
                "error": "Build failed — cannot deploy",
                "build_errors": build_result["errors"],
                "output": build_result["output"][-500:],
            }

    if not dist_dir.exists():
        return {"ok": False, "error": "dist/ directory not found after build"}

    env = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}
    stdout, stderr, returncode, timed_out = _run_with_process_group(
        ["npx", "netlify", "deploy", "--dir=dist", "--json"],
        project_path, timeout=120, env=env
    )

    if timed_out:
        return {"ok": False, "error": "netlify deploy timed out (120s)"}

    output = stdout + stderr

    # Parse JSON output from netlify deploy
    preview_url = ""
    deploy_id = ""
    try:
        deploy_data = json.loads(stdout)
        preview_url = deploy_data.get("deploy_url", "") or deploy_data.get("url", "")
        deploy_id = deploy_data.get("deploy_id", "")
    except (json.JSONDecodeError, ValueError):
        # Try to extract URL from text output
        for line in output.splitlines():
            if "http" in line and "netlify" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("http"):
                        preview_url = p.strip()
                        break
                    if preview_url:
                        break

    ok = returncode == 0 and bool(preview_url)

    # Store in DB
    try:
        conn = _get_db()
        conn.execute(
            """INSERT INTO previews (project, preview_url, deploy_id, ok, output)
               VALUES (?, ?, ?, ?, ?)""",
            (project_name, preview_url, deploy_id, int(ok), output[-1000:])
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB write error for preview {project_name}: {e}")

    return {
        "ok": ok,
        "preview_url": preview_url,
        "deploy_id": deploy_id,
        "output": output[-500:] if not ok else "",
    }


# --- Background Build Loop ---
def _build_loop():
    """Periodically validate all projects that have changed."""
    global _building

    # First run: populate mtimes without building
    projects = _discover_projects()
    for proj in projects:
        _has_changes(proj["path"], proj["name"])

    while True:
        time.sleep(BUILD_INTERVAL)
        if _building:
            continue

        _building = True
        try:
            projects = _discover_projects()
            for proj in projects:
                if _has_changes(proj["path"], proj["name"]):
                    print(f"Changes detected in {proj['name']}, validating...")
                    result = _validate_project(proj["path"], proj["name"], trigger="watch")
                    icon = "✓" if result["passed"] else "✗"
                    print(f"  {icon} {proj['name']}: tsc={'ok' if result['tsc_ok'] else 'FAIL'} "
                          f"vite={'ok' if result['vite_ok'] else 'FAIL'} ({result['duration_sec']}s)")
        except Exception as e:
            print(f"Build loop error: {e}")
        finally:
            _building = False


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=_build_loop, daemon=True)
    t.start()


# --- API Endpoints ---

@app.get("/api/projects")
async def list_projects():
    """List all projects being served."""
    projects = _discover_projects()
    result = []
    for proj in projects:
        entry = {
            "name": proj["name"],
            "display_name": proj.get("display_name", proj["name"]),
            "has_dev": proj.get("has_dev", False),
            "has_build": proj.get("has_build", False),
            "has_tsc": proj.get("has_tsc", False),
        }
        # Attach cached build status if available
        cached = _build_cache.get(proj["name"])
        if cached:
            entry["last_build"] = {
                "passed": cached["passed"],
                "tsc_ok": cached["tsc_ok"],
                "vite_ok": cached["vite_ok"],
                "timestamp": cached["timestamp"],
            }
        result.append(entry)
    return {"projects": result}


@app.get("/api/projects/{project}/build/status")
async def project_build_status(project: str):
    """Get build pass/fail status for a specific project."""
    project = project.lower()

    # Check cache first
    cached = _build_cache.get(project)
    if cached:
        return {
            "project": project,
            "passed": cached["passed"],
            "tsc_ok": cached["tsc_ok"],
            "vite_ok": cached["vite_ok"],
            "duration_sec": cached["duration_sec"],
            "git_sha": cached.get("git_sha", ""),
            "git_branch": cached.get("git_branch", ""),
            "timestamp": cached["timestamp"],
        }

    # Fall back to DB
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM builds WHERE project = ? ORDER BY timestamp DESC LIMIT 1",
            (project,)
        ).fetchone()
        conn.close()

        if row:
            return {
                "project": project,
                "passed": bool(row["passed"]),
                "tsc_ok": bool(row["tsc_ok"]),
                "vite_ok": bool(row["vite_ok"]),
                "duration_sec": row["duration_sec"],
                "git_sha": row["git_sha"] or "",
                "git_branch": row["git_branch"] or "",
                "timestamp": row["timestamp"],
            }
    except Exception:
        pass

    return {"project": project, "passed": None, "message": "no build data yet"}


@app.get("/api/build/status")
async def build_status_all():
    """Get build status for all projects (summary)."""
    projects = _discover_projects()
    results = []
    for proj in projects:
        cached = _build_cache.get(proj["name"])
        if cached:
            results.append({
                "project": proj["name"],
                "passed": cached["passed"],
                "tsc_ok": cached["tsc_ok"],
                "vite_ok": cached["vite_ok"],
                "timestamp": cached["timestamp"],
            })
        else:
            # Check DB
            try:
                conn = _get_db()
                row = conn.execute(
                    "SELECT * FROM builds WHERE project = ? ORDER BY timestamp DESC LIMIT 1",
                    (proj["name"],)
                ).fetchone()
                conn.close()
                if row:
                    results.append({
                        "project": proj["name"],
                        "passed": bool(row["passed"]),
                        "tsc_ok": bool(row["tsc_ok"]),
                        "vite_ok": bool(row["vite_ok"]),
                        "timestamp": row["timestamp"],
                    })
            except Exception:
                pass

    total = len(results)
    passing = sum(1 for r in results if r.get("passed"))
    return {
        "total_projects": len(projects),
        "builds_recorded": total,
        "passing": passing,
        "failing": total - passing,
        "results": results,
    }


@app.get("/api/build/errors")
async def build_errors(project: Optional[str] = None):
    """Get build errors. Optionally filter by project."""
    try:
        conn = _get_db()
        if project:
            project = project.lower()
            rows = conn.execute(
                """SELECT * FROM builds WHERE project = ? AND passed = 0
                   ORDER BY timestamp DESC LIMIT 10""",
                (project,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM builds WHERE passed = 0
                   ORDER BY timestamp DESC LIMIT 20"""
            ).fetchall()
        conn.close()

        errors = []
        for row in rows:
            tsc_errors = []
            vite_errors = []
            try:
                tsc_errors = json.loads(row["tsc_errors"]) if row["tsc_errors"] else []
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                vite_errors = json.loads(row["vite_errors"]) if row["vite_errors"] else []
            except (json.JSONDecodeError, TypeError):
                pass

            errors.append({
                "project": row["project"],
                "timestamp": row["timestamp"],
                "git_sha": row["git_sha"] or "",
                "tsc_ok": bool(row["tsc_ok"]),
                "vite_ok": bool(row["vite_ok"]),
                "tsc_errors": tsc_errors,
                "vite_errors": vite_errors,
            })

        return {"errors": errors}
    except Exception as e:
        return {"errors": [], "error": str(e)}


@app.post("/api/projects/{project}/preview")
async def trigger_preview(project: str):
    """Trigger a Netlify preview deploy for a project."""
    project = project.lower()
    projects = _discover_projects()
    match = next((p for p in projects if p["name"] == project), None)

    if not match:
        known = [p["name"] for p in projects]
        return {"ok": False, "error": f"Unknown project '{project}'", "known_projects": known}

    result = _deploy_preview(match["path"], project)
    return result


@app.post("/api/projects/{project}/build")
async def trigger_build(project: str):
    """Manually trigger build validation for a project."""
    project = project.lower()
    projects = _discover_projects()
    match = next((p for p in projects if p["name"] == project), None)

    if not match:
        known = [p["name"] for p in projects]
        return {"ok": False, "error": f"Unknown project '{project}'", "known_projects": known}

    def _run():
        global _building
        _building = True
        try:
            _validate_project(match["path"], project, trigger="manual")
        finally:
            _building = False

    if _building:
        return {"status": "already_building"}

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return {"status": "started", "project": project}


@app.get("/api/projects/{project}/previews")
async def get_previews(project: str, limit: int = 5):
    """Get preview deploy history for a project."""
    project = project.lower()
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM previews WHERE project = ? ORDER BY timestamp DESC LIMIT ?",
            (project, limit)
        ).fetchall()
        conn.close()
        return {"previews": [dict(r) for r in rows]}
    except Exception as e:
        return {"previews": [], "error": str(e)}


@app.get("/api/building")
async def is_building():
    """Check if a build is currently running."""
    return {"building": _building}
