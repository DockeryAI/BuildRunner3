"""
BR3 Cluster — Node 2: Walter (Sentinel)
Continuous testing. Watches repos, runs affected tests, stores results in SQLite.

Run: uvicorn core.cluster.node_tests:app --host 0.0.0.0 --port 8100
"""

import os
import re
import time
import json
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
REPOS_DIR = os.environ.get("REPOS_DIR", os.path.expanduser("~/repos"))
DB_PATH = os.environ.get("TEST_DB", os.path.expanduser("~/.walter/test_results.db"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
LOCKWOOD_URL = os.environ.get("LOCKWOOD_URL", "http://10.0.1.101:8100")

# --- App ---
app = create_app(role="test-runner", version="0.1.0")

# --- State ---
_running = False
_last_run_time = 0.0
_last_results = {}
_file_hashes: dict[str, str] = {}


# --- SQLite Setup ---
def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS test_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            runner TEXT NOT NULL,
            project TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            git_sha TEXT,
            git_branch TEXT,
            duration_ms INTEGER,
            total INTEGER DEFAULT 0,
            passed INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            flaky INTEGER DEFAULT 0,
            trigger TEXT DEFAULT 'watch'
        );
        CREATE TABLE IF NOT EXISTS test_cases (
            case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES test_runs(run_id) ON DELETE CASCADE,
            suite_name TEXT,
            test_name TEXT NOT NULL,
            full_name TEXT NOT NULL,
            file_path TEXT,
            status TEXT NOT NULL,
            duration_ms INTEGER,
            retry_count INTEGER DEFAULT 0,
            failure_message TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_runs_project ON test_runs(project);
        CREATE INDEX IF NOT EXISTS idx_runs_ts ON test_runs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_cases_run ON test_cases(run_id);
        CREATE INDEX IF NOT EXISTS idx_cases_name ON test_cases(full_name);

        CREATE TABLE IF NOT EXISTS test_file_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            test_file TEXT NOT NULL,
            source_file TEXT NOT NULL,
            confidence TEXT DEFAULT 'import',
            last_verified TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_testmap_project_source ON test_file_map(project, source_file);
    """)
    conn.commit()


# --- Git Operations ---
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


def _git_pull(repo_path: str) -> bool:
    """Pull latest changes. Returns True if changes were pulled."""
    try:
        result = subprocess.run(
            ["git", "pull", "--rebase", "--quiet"],
            capture_output=True, text=True, cwd=repo_path, timeout=30
        )
        return "Already up to date" not in result.stdout
    except Exception:
        return False


def _detect_changes(repo_path: str) -> list[str]:
    """Detect changed files since last check using file modification times."""
    changed = []
    repo = Path(repo_path)
    skip_dirs = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".cache"}

    for path in repo.rglob("*"):
        if any(s in path.parts for s in skip_dirs):
            continue
        if not path.is_file():
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".py", ".vue"}:
            continue

        key = str(path)
        try:
            mtime = str(path.stat().st_mtime)
        except OSError:
            continue

        if _file_hashes.get(key) != mtime:
            if key in _file_hashes:  # skip first run (everything is "new")
                changed.append(str(path.relative_to(repo)))
            _file_hashes[key] = mtime

    return changed


# --- Test File Map ---
# Test file patterns: *.test.ts, *.test.tsx, *.spec.ts, *.test.js, etc.
_TEST_SUFFIXES = {".test.ts", ".test.tsx", ".test.js", ".test.jsx", ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx", ".test.py"}
_SOURCE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py", ".vue"}
_SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".cache", ".venv"}

# Regex to find import/require statements that reference relative paths
_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|"""
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)|"""
    r"""from\s+(\S+)\s+import)""",
    re.MULTILINE,
)


def _is_test_file(path: Path) -> bool:
    """Check if a file is a test file by its name pattern."""
    name = path.name
    for suffix in _TEST_SUFFIXES:
        if name.endswith(suffix):
            return True
    # Python test convention: test_*.py
    if name.startswith("test_") and name.endswith(".py"):
        return True
    # __tests__ directory convention
    if "__tests__" in path.parts:
        return True
    return False


def _infer_source_from_convention(test_path: Path, repo: Path) -> Optional[str]:
    """Infer source file from test file naming convention.

    foo.test.ts -> foo.ts
    foo.spec.tsx -> foo.tsx
    test_foo.py -> foo.py
    __tests__/foo.test.ts -> ../foo.ts
    """
    name = test_path.name

    # Handle *.test.ext / *.spec.ext
    for pattern in (".test.", ".spec."):
        idx = name.find(pattern)
        if idx > 0:
            ext = name[idx + len(pattern) - 1:]  # includes the dot
            source_name = name[:idx] + ext

            # If in __tests__ dir, source is one level up
            if "__tests__" in test_path.parts:
                source_candidate = test_path.parent.parent / source_name
            else:
                source_candidate = test_path.parent / source_name

            if source_candidate.exists():
                return str(source_candidate.relative_to(repo))

    # Handle test_*.py -> *.py
    if name.startswith("test_") and name.endswith(".py"):
        source_name = name[5:]  # strip 'test_'
        source_candidate = test_path.parent / source_name
        if source_candidate.exists():
            return str(source_candidate.relative_to(repo))

    return None


def _extract_imports(test_path: Path, repo: Path) -> list[str]:
    """Extract source file paths from import statements in a test file."""
    try:
        content = test_path.read_text(errors="ignore")
    except (OSError, UnicodeDecodeError):
        return []

    source_files = []
    for match in _IMPORT_RE.finditer(content):
        # Get the first non-None group (different import styles)
        raw = match.group(1) or match.group(2) or match.group(3)
        if not raw or not raw.startswith("."):
            continue  # skip non-relative imports

        # Resolve relative path from test file location
        resolved = (test_path.parent / raw).resolve()

        # Try with various extensions if no extension
        candidates = [resolved]
        if not resolved.suffix:
            for ext in _SOURCE_EXTENSIONS:
                candidates.append(resolved.with_suffix(ext))
                # Also try index files
                candidates.append(resolved / f"index{ext}")

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    rel = str(candidate.relative_to(repo.resolve()))
                    source_files.append(rel)
                except ValueError:
                    pass
                break

    return source_files


def build_test_map(project: str, repo_path: str) -> int:
    """Scan test files and build source->test mapping. Returns count of mappings created."""
    repo = Path(repo_path)
    if not repo.exists():
        return 0

    conn = _get_db()

    # Clear existing entries for this project
    conn.execute("DELETE FROM test_file_map WHERE project = ?", (project,))

    mappings = []
    seen_pairs = set()

    for path in repo.rglob("*"):
        if any(s in path.parts for s in _SKIP_DIRS):
            continue
        if not path.is_file():
            continue
        if not _is_test_file(path):
            continue

        test_rel = str(path.relative_to(repo))

        # Method 1: Parse imports
        for source_rel in _extract_imports(path, repo):
            pair = (test_rel, source_rel)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                mappings.append((project, test_rel, source_rel, "import"))

        # Method 2: Naming convention
        source_rel = _infer_source_from_convention(path, repo)
        if source_rel:
            pair = (test_rel, source_rel)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                mappings.append((project, test_rel, source_rel, "convention"))

    # Bulk insert
    conn.executemany(
        "INSERT INTO test_file_map (project, test_file, source_file, confidence) VALUES (?, ?, ?, ?)",
        mappings,
    )
    conn.commit()
    conn.close()
    return len(mappings)


def get_test_map(files: list[str], project: str) -> dict[str, list[dict]]:
    """Given source files, return which test files cover them."""
    conn = _get_db()
    result = {}

    for source_file in files:
        rows = conn.execute(
            "SELECT test_file, confidence FROM test_file_map WHERE project = ? AND source_file = ?",
            (project, source_file),
        ).fetchall()
        if rows:
            result[source_file] = [
                {"test_file": r["test_file"], "confidence": r["confidence"]}
                for r in rows
            ]
        else:
            result[source_file] = []

    conn.close()
    return result


def _invalidate_test_map_entries(project: str, changed_files: list[str]):
    """Invalidate test map entries when source or test files change."""
    if not changed_files:
        return

    conn = _get_db()
    for f in changed_files:
        # If a test file changed, remove its mappings (will be rebuilt)
        conn.execute(
            "DELETE FROM test_file_map WHERE project = ? AND test_file = ?",
            (project, f),
        )
        # If a source file changed, remove its mappings (will be rebuilt)
        conn.execute(
            "DELETE FROM test_file_map WHERE project = ? AND source_file = ?",
            (project, f),
        )
    conn.commit()
    conn.close()


# --- Test Runners ---
def _run_vitest(repo_path: str, project_name: str, changed_files: list[str]) -> dict:
    """Run vitest for affected tests. Returns parsed results."""
    if not Path(repo_path, "node_modules", ".bin", "vitest").exists():
        return None

    # Check if there are test files
    has_tests = any(Path(repo_path).rglob("*.test.*")) or any(Path(repo_path).rglob("*.spec.*"))
    if not has_tests:
        return None

    start = time.time()
    result_file = f"/tmp/walter-vitest-{project_name}.json"

    try:
        cmd = [
            "npx", "vitest", "run",
            "--reporter=json",
            f"--outputFile={result_file}",
            "--passWithNoTests",
        ]
        # If we know which files changed, use --changed
        if changed_files:
            cmd.append("--changed")

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=repo_path, timeout=120,
            env={**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}
        )

        duration = int((time.time() - start) * 1000)

        # Parse JSON results
        if Path(result_file).exists():
            try:
                data = json.loads(Path(result_file).read_text())
                return {
                    "runner": "vitest",
                    "project": project_name,
                    "duration_ms": duration,
                    "total": data.get("numTotalTests", 0),
                    "passed": data.get("numPassedTests", 0),
                    "failed": data.get("numFailedTests", 0),
                    "skipped": data.get("numPendingTests", 0),
                    "tests": [
                        {
                            "suite": tr.get("name", ""),
                            "name": ar.get("title", ""),
                            "full_name": ar.get("fullName", ""),
                            "status": ar.get("status", "unknown"),
                            "duration_ms": ar.get("duration", 0),
                            "failure": "\n".join(ar.get("failureMessages", [])),
                        }
                        for tr in data.get("testResults", [])
                        for ar in tr.get("assertionResults", [])
                    ],
                }
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse exit code
        return {
            "runner": "vitest",
            "project": project_name,
            "duration_ms": duration,
            "total": 0, "passed": 0,
            "failed": 1 if result.returncode != 0 else 0,
            "skipped": 0,
            "tests": [],
            "error": result.stderr[-500:] if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"runner": "vitest", "project": project_name, "error": "timeout", "failed": 1, "total": 1, "passed": 0, "skipped": 0, "tests": [], "duration_ms": 120000}
    except Exception as e:
        return {"runner": "vitest", "project": project_name, "error": str(e), "failed": 0, "total": 0, "passed": 0, "skipped": 0, "tests": [], "duration_ms": 0}


def _run_playwright(repo_path: str, project_name: str, changed_files: list[str]) -> dict:
    """Run Playwright E2E tests. WebKit only, 1 worker, per research."""
    pw_config = Path(repo_path, "playwright.config.ts")
    if not pw_config.exists():
        pw_config = Path(repo_path, "playwright.config.js")
    if not pw_config.exists():
        return None

    # Only run E2E if UI-related files changed
    ui_extensions = {".tsx", ".jsx", ".vue", ".css", ".html"}
    ui_changed = any(Path(f).suffix in ui_extensions for f in changed_files)
    if changed_files and not ui_changed:
        return None  # Skip E2E for non-UI changes

    start = time.time()
    result_file = f"/tmp/walter-playwright-{project_name}.json"

    try:
        cmd = [
            "npx", "playwright", "test",
            "--reporter=json",
            "--workers=1",
            "--project=webkit",  # lowest memory per research
        ]
        if changed_files:
            cmd.append("--only-changed")

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=repo_path, timeout=300,
            env={
                **os.environ,
                "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}",
                "PLAYWRIGHT_JSON_OUTPUT_NAME": result_file,
            }
        )

        duration = int((time.time() - start) * 1000)

        if Path(result_file).exists():
            try:
                data = json.loads(Path(result_file).read_text())
                tests = []
                for suite in data.get("suites", []):
                    _extract_pw_tests(suite, tests)

                passed = sum(1 for t in tests if t["status"] == "passed")
                failed = sum(1 for t in tests if t["status"] == "failed")
                flaky = sum(1 for t in tests if t["status"] == "flaky")
                skipped = sum(1 for t in tests if t["status"] == "skipped")

                return {
                    "runner": "playwright",
                    "project": project_name,
                    "duration_ms": duration,
                    "total": len(tests),
                    "passed": passed,
                    "failed": failed,
                    "flaky": flaky,
                    "skipped": skipped,
                    "tests": tests,
                }
            except (json.JSONDecodeError, KeyError):
                pass

        return {
            "runner": "playwright",
            "project": project_name,
            "duration_ms": duration,
            "total": 0, "passed": 0, "failed": 1 if result.returncode != 0 else 0,
            "skipped": 0, "tests": [],
            "error": result.stderr[-500:] if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"runner": "playwright", "project": project_name, "error": "timeout", "failed": 1, "total": 1, "passed": 0, "skipped": 0, "tests": [], "duration_ms": 300000}
    except Exception as e:
        return {"runner": "playwright", "project": project_name, "error": str(e), "failed": 0, "total": 0, "passed": 0, "skipped": 0, "tests": [], "duration_ms": 0}


def _extract_pw_tests(suite: dict, tests: list, prefix: str = ""):
    """Recursively extract tests from Playwright's nested suite structure."""
    title = f"{prefix} > {suite.get('title', '')}" if prefix else suite.get("title", "")
    for spec in suite.get("specs", []):
        for test in spec.get("tests", []):
            results = test.get("results", [])
            status = "passed"
            failure = ""
            duration = 0
            retries = len(results) - 1 if len(results) > 1 else 0

            if results:
                last = results[-1]
                status = last.get("status", "passed")
                duration = last.get("duration", 0)
                if last.get("error"):
                    failure = last["error"].get("message", "")

                # Detect flaky: failed then passed on retry
                if len(results) > 1 and results[0].get("status") == "failed" and results[-1].get("status") == "passed":
                    status = "flaky"

            tests.append({
                "suite": title,
                "name": spec.get("title", ""),
                "full_name": f"{title} > {spec.get('title', '')}",
                "status": status,
                "duration_ms": duration,
                "failure": failure,
                "retry_count": retries,
            })

    for child in suite.get("suites", []):
        _extract_pw_tests(child, tests, title)


# --- Store Results ---
def _store_results(results: dict):
    """Store test run results in SQLite."""
    if not results or results.get("total", 0) == 0 and not results.get("error"):
        return

    conn = _get_db()
    cursor = conn.execute(
        """INSERT INTO test_runs (runner, project, git_sha, git_branch, duration_ms,
           total, passed, failed, skipped, flaky, trigger)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (results.get("runner", "unknown"),
         results.get("project", "unknown"),
         results.get("git_sha", ""),
         results.get("git_branch", ""),
         results.get("duration_ms", 0),
         results.get("total", 0),
         results.get("passed", 0),
         results.get("failed", 0),
         results.get("skipped", 0),
         results.get("flaky", 0),
         "watch")
    )
    run_id = cursor.lastrowid

    for test in results.get("tests", []):
        conn.execute(
            """INSERT INTO test_cases (run_id, suite_name, test_name, full_name,
               file_path, status, duration_ms, retry_count, failure_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id,
             test.get("suite", ""),
             test.get("name", ""),
             test.get("full_name", ""),
             test.get("file_path", ""),
             test.get("status", "unknown"),
             test.get("duration_ms", 0),
             test.get("retry_count", 0),
             test.get("failure", ""))
        )

    conn.commit()
    conn.close()


# --- Background Test Loop ---
def _test_loop():
    """Main loop: pull repos, detect changes, run affected tests."""
    global _running, _last_run_time, _last_results

    # First run: populate file hashes without running tests
    repos_path = Path(REPOS_DIR)
    for repo_dir in repos_path.iterdir():
        if repo_dir.is_dir() and not repo_dir.name.startswith("."):
            _detect_changes(str(repo_dir))

    while True:
        time.sleep(POLL_INTERVAL)
        if _running:
            continue

        _running = True
        try:
            for repo_dir in repos_path.iterdir():
                if not repo_dir.is_dir() or repo_dir.name.startswith("."):
                    continue

                project_name = repo_dir.name
                repo_path = str(repo_dir)

                # Pull latest
                _git_pull(repo_path)

                # Detect changes
                changed = _detect_changes(repo_path)
                if not changed:
                    continue

                print(f"Changes in {project_name}: {len(changed)} files")

                # Auto-rebuild affected test map entries
                _invalidate_test_map_entries(project_name, changed)
                build_test_map(project_name, repo_path)

                git_sha = _git_sha(repo_path)
                git_branch = _git_branch(repo_path)

                # Run vitest first (fast, per research: stagger, don't parallel)
                vitest_results = _run_vitest(repo_path, project_name, changed)
                if vitest_results:
                    vitest_results["git_sha"] = git_sha
                    vitest_results["git_branch"] = git_branch
                    _store_results(vitest_results)
                    _last_results[f"{project_name}_vitest"] = vitest_results
                    print(f"  vitest: {vitest_results.get('passed', 0)}/{vitest_results.get('total', 0)} passed")

                # Then Playwright (slower, only for UI changes)
                pw_results = _run_playwright(repo_path, project_name, changed)
                if pw_results:
                    pw_results["git_sha"] = git_sha
                    pw_results["git_branch"] = git_branch
                    _store_results(pw_results)
                    _last_results[f"{project_name}_playwright"] = pw_results
                    print(f"  playwright: {pw_results.get('passed', 0)}/{pw_results.get('total', 0)} passed")

            _last_run_time = time.time()
        except Exception as e:
            print(f"Test loop error: {e}")
        finally:
            _running = False


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=_test_loop, daemon=True)
    t.start()


# --- API Endpoints ---
@app.get("/api/results")
async def get_results(project: Optional[str] = None, latest: bool = True):
    """Get test results. If latest=true, returns most recent run per project."""
    try:
        conn = _get_db()
    except Exception:
        return {"results": [], "error": "database unavailable"}
    try:
        if latest:
            if project:
                runs = conn.execute(
                    "SELECT * FROM test_runs WHERE project = ? ORDER BY timestamp DESC LIMIT 1",
                    (project,)
                ).fetchall()
            else:
                runs = conn.execute(
                    """SELECT * FROM test_runs WHERE run_id IN (
                         SELECT MAX(run_id) FROM test_runs GROUP BY project, runner
                       ) ORDER BY timestamp DESC"""
                ).fetchall()
        else:
            if project:
                runs = conn.execute(
                    "SELECT * FROM test_runs WHERE project = ? ORDER BY timestamp DESC LIMIT 20",
                    (project,)
                ).fetchall()
            else:
                runs = conn.execute(
                    "SELECT * FROM test_runs ORDER BY timestamp DESC LIMIT 20"
                ).fetchall()

        results = []
        for run in runs:
            run_dict = dict(run)
            cases = conn.execute(
                "SELECT * FROM test_cases WHERE run_id = ? AND status = 'failed'",
                (run["run_id"],)
            ).fetchall()
            run_dict["failures"] = [dict(c) for c in cases]
            results.append(run_dict)

        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}
    finally:
        conn.close()


@app.get("/api/coverage")
async def get_coverage(project: Optional[str] = None):
    """Get pass rate as a proxy for coverage."""
    try:
        conn = _get_db()
    except Exception:
        return {"pass_rate": 0, "passed": 0, "total": 0, "error": "database unavailable"}
    try:
        if project:
            row = conn.execute(
                """SELECT SUM(passed) as passed, SUM(total) as total
                   FROM test_runs WHERE project = ?
                   AND run_id IN (SELECT MAX(run_id) FROM test_runs WHERE project = ? GROUP BY runner)""",
                (project, project)
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT SUM(passed) as passed, SUM(total) as total
                   FROM test_runs WHERE run_id IN (
                     SELECT MAX(run_id) FROM test_runs GROUP BY project, runner
                   )"""
            ).fetchone()

        total = row["total"] or 0
        passed = row["passed"] or 0
        return {
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "passed": passed,
            "total": total,
        }
    except Exception as e:
        return {"pass_rate": 0, "passed": 0, "total": 0, "error": str(e)}
    finally:
        conn.close()


@app.get("/api/flaky")
async def get_flaky():
    """Detect flaky tests from status oscillation over last 7 days."""
    try:
        conn = _get_db()
    except Exception:
        return {"flaky": [], "error": "database unavailable"}
    try:
        rows = conn.execute("""
            WITH recent AS (
                SELECT tc.full_name, tc.status, tr.timestamp,
                       LAG(tc.status) OVER (PARTITION BY tc.full_name ORDER BY tr.timestamp) as prev
                FROM test_cases tc JOIN test_runs tr ON tc.run_id = tr.run_id
                WHERE tr.timestamp > datetime('now', '-7 days')
            )
            SELECT full_name,
                COUNT(*) as total_runs,
                SUM(CASE WHEN status != prev AND prev IS NOT NULL THEN 1 ELSE 0 END) as flips
            FROM recent GROUP BY full_name HAVING total_runs >= 3 AND flips > 0
            ORDER BY CAST(flips AS REAL) / (total_runs - 1) DESC
        """).fetchall()

        return {"flaky": [
            {"test": r["full_name"], "runs": r["total_runs"], "flips": r["flips"],
             "score": round(r["flips"] / (r["total_runs"] - 1), 3)}
            for r in rows
        ]}
    except Exception as e:
        return {"flaky": [], "error": str(e)}
    finally:
        conn.close()


@app.get("/api/history/{test_name:path}")
async def get_history(test_name: str, limit: int = 20):
    """Get history of a specific test."""
    try:
        conn = _get_db()
    except Exception:
        return {"history": [], "error": "database unavailable"}
    try:
        rows = conn.execute(
            """SELECT tc.*, tr.timestamp, tr.git_sha, tr.project
               FROM test_cases tc JOIN test_runs tr ON tc.run_id = tr.run_id
               WHERE tc.full_name = ? ORDER BY tr.timestamp DESC LIMIT ?""",
            (test_name, limit)
        ).fetchall()
        return {"history": [dict(r) for r in rows]}
    except Exception as e:
        return {"history": [], "error": str(e)}
    finally:
        conn.close()


@app.post("/api/run")
async def trigger_run(project: Optional[str] = None):
    """Trigger manual test run."""
    if _running:
        return {"status": "already_running"}

    def _manual_run():
        global _running
        _running = True
        try:
            repos_path = Path(REPOS_DIR)
            for repo_dir in repos_path.iterdir():
                if not repo_dir.is_dir() or repo_dir.name.startswith("."):
                    continue
                if project and repo_dir.name != project:
                    continue

                name = repo_dir.name
                path = str(repo_dir)
                sha = _git_sha(path)
                branch = _git_branch(path)

                vr = _run_vitest(path, name, [])
                if vr:
                    vr["git_sha"] = sha
                    vr["git_branch"] = branch
                    _store_results(vr)

                pr = _run_playwright(path, name, [])
                if pr:
                    pr["git_sha"] = sha
                    pr["git_branch"] = branch
                    _store_results(pr)
        finally:
            _running = False

    t = threading.Thread(target=_manual_run, daemon=True)
    t.start()
    return {"status": "started"}


@app.get("/api/testmap")
async def api_get_testmap(files: str = "", project: str = ""):
    """Get test file mapping for given source files."""
    if not files or not project:
        return {"error": "files and project params required"}
    file_list = [f.strip() for f in files.split(",") if f.strip()]
    return get_test_map(file_list, project)


@app.post("/api/testmap/baseline")
async def api_testmap_baseline(project: str = "", files: str = ""):
    """Run mapped tests and return baseline pass/fail state."""
    if not project:
        return {"error": "project param required"}

    file_list = [f.strip() for f in files.split(",") if f.strip()] if files else []
    mapping = get_test_map(file_list, project) if file_list else {}

    # Collect unique test files
    test_files = set()
    for source, tests in mapping.items():
        for t in tests:
            test_files.add(t["test_file"])

    if not test_files:
        return {"baseline": {}, "message": "no mapped tests found"}

    # Try to find the repo path
    repo_path = os.path.join(REPOS_DIR, project)
    if not os.path.isdir(repo_path):
        return {"baseline": {tf: "skip" for tf in test_files}, "message": "repo not found"}

    # Run vitest on specific test files
    baseline = {}
    for tf in test_files:
        test_path = os.path.join(repo_path, tf)
        if not os.path.exists(test_path):
            baseline[tf] = {"status": "skip", "duration_ms": 0}
            continue

        start = time.time()
        try:
            result = subprocess.run(
                ["npx", "vitest", "run", tf, "--reporter=verbose", "--passWithNoTests"],
                capture_output=True, text=True,
                cwd=repo_path, timeout=60,
                env={**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}
            )
            duration = int((time.time() - start) * 1000)
            baseline[tf] = {
                "status": "pass" if result.returncode == 0 else "fail",
                "duration_ms": duration,
            }
        except subprocess.TimeoutExpired:
            baseline[tf] = {"status": "fail", "duration_ms": 60000}
        except Exception:
            baseline[tf] = {"status": "skip", "duration_ms": 0}

    return {"baseline": baseline}


@app.get("/api/running")
async def is_running():
    return {"running": _running, "last_run": _last_run_time}
