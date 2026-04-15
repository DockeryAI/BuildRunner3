"""
BR3 Cluster — Node 2: Walter (Sentinel)
Continuous testing. Watches repos, runs affected tests, stores results in SQLite.
Thread-safe queue-based execution with git SHA change detection.

Run: uvicorn core.cluster.node_tests:app --host 0.0.0.0 --port 8100
"""

import os
import re
import time
import json
import uuid
import sqlite3
import subprocess
import threading
import queue
import urllib.request
import urllib.error
import psutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from core.cluster.base_service import create_app

# --- Config ---
REPOS_DIR = os.environ.get("REPOS_DIR", os.path.expanduser("~/repos"))
DB_PATH = os.environ.get("TEST_DB", os.path.expanduser("~/.walter/test_results.db"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
LOCKWOOD_URL = os.environ.get("LOCKWOOD_URL", "http://10.0.1.101:8100")
SERVICE_VERSION = "0.2.0"

# --- App ---
app = create_app(role="test-runner", version=SERVICE_VERSION)

# --- Thread-Safe State (RC1-RC3 fixes) ---
_state_lock = threading.Lock()       # Protects _running, _last_run_time, _last_results
_db_lock = threading.Lock()          # Serializes all SQLite writes (RC5)

_running = False
_last_run_time = 0.0
_last_results = {}

# --- Queue-based execution (RC4 fix) ---
# Single consumer thread pulls from queue, deduplicates by project+SHA, runs tests serially
_test_queue: queue.Queue = queue.Queue()
_run_status: dict[str, dict] = {}   # run_id -> {status, project, queued_at, started_at, completed_at, result}
_run_status_lock = threading.Lock()

# Track last tested SHA per project for git-based change detection
_last_tested_sha: dict[str, str] = {}


# --- SQLite Setup ---
def _get_db() -> sqlite3.Connection:
    """Get a SQLite connection. Caller must use _db_lock for write operations."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
            trigger TEXT DEFAULT 'watch',
            last_tested_sha TEXT
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

        CREATE TABLE IF NOT EXISTS project_sha_tracking (
            project TEXT PRIMARY KEY,
            last_tested_sha TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS repo_provisions (
            project TEXT PRIMARY KEY,
            provisioned_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # Migration: add last_tested_sha column if missing (existing DBs)
    try:
        conn.execute("SELECT last_tested_sha FROM test_runs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE test_runs ADD COLUMN last_tested_sha TEXT")
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


def _git_sha_full(repo_path: str) -> str:
    """Get full git SHA for reliable comparison."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
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


def _detect_changes(repo_path: str, project: str) -> list[str]:
    """Detect changed files since last tested SHA using git diff.

    Returns list of changed file paths relative to repo root.
    Uses git SHA tracking instead of mtime for reliable detection.
    """
    current_sha = _git_sha_full(repo_path)
    if not current_sha:
        return []

    # Get last tested SHA for this project
    last_sha = _last_tested_sha.get(project)

    # If no previous SHA, try loading from DB
    if not last_sha:
        try:
            with _db_lock:
                conn = _get_db()
                row = conn.execute(
                    "SELECT last_tested_sha FROM project_sha_tracking WHERE project = ?",
                    (project,)
                ).fetchone()
                conn.close()
            if row and row["last_tested_sha"]:
                last_sha = row["last_tested_sha"]
                _last_tested_sha[project] = last_sha
        except Exception:
            pass

    # First run: record SHA, return empty (no changes to test yet)
    if not last_sha:
        _last_tested_sha[project] = current_sha
        return []

    # Same SHA: no changes
    if last_sha == current_sha:
        return []

    # Get changed files between SHAs
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{last_sha}..{current_sha}"],
            capture_output=True, text=True, cwd=repo_path, timeout=10
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        pass

    # Fallback: if git diff fails (e.g., force push), return all tracked files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1..HEAD"],
            capture_output=True, text=True, cwd=repo_path, timeout=10
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        pass

    return []


def _update_tested_sha(project: str, sha: str):
    """Update the last tested SHA for a project after a successful test run."""
    _last_tested_sha[project] = sha
    try:
        with _db_lock:
            conn = _get_db()
            conn.execute(
                """INSERT INTO project_sha_tracking (project, last_tested_sha, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(project) DO UPDATE SET last_tested_sha = ?, updated_at = datetime('now')""",
                (project, sha, sha)
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"SHA tracking update failed: {e}")


# --- Auto-Provision ---
def _ensure_repo(project_name: str) -> str:
    """Create a bare repo for project if it doesn't exist. Returns repo path."""
    repo_path = os.path.join(REPOS_DIR, project_name)
    if not os.path.isdir(repo_path):
        subprocess.run(
            ["git", "init", "--bare", repo_path],
            capture_output=True, text=True, timeout=10
        )
        # Track provision in DB
        try:
            with _db_lock:
                conn = _get_db()
                conn.execute(
                    "INSERT OR IGNORE INTO repo_provisions (project) VALUES (?)",
                    (project_name,)
                )
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Provision tracking failed: {e}")
        print(f"Provisioned bare repo: {repo_path}")
    return repo_path


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

    # Bulk insert with db lock (RC5 fix)
    with _db_lock:
        conn = _get_db()
        conn.execute("DELETE FROM test_file_map WHERE project = ?", (project,))
        conn.executemany(
            "INSERT INTO test_file_map (project, test_file, source_file, confidence) VALUES (?, ?, ?, ?)",
            mappings,
        )
        conn.commit()
        conn.close()
    return len(mappings)


def get_test_map(files: list[str], project: str) -> dict[str, list[dict]]:
    """Given source files, return which test files cover them."""
    with _db_lock:
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

    with _db_lock:
        conn = _get_db()
        for f in changed_files:
            conn.execute(
                "DELETE FROM test_file_map WHERE project = ? AND test_file = ?",
                (project, f),
            )
            conn.execute(
                "DELETE FROM test_file_map WHERE project = ? AND source_file = ?",
                (project, f),
            )
        conn.commit()
        conn.close()


# --- Test Runners ---
def _find_vitest_dir(repo_path: str) -> Optional[str]:
    """Find the directory containing vitest — root or first subdirectory with node_modules/.bin/vitest."""
    if Path(repo_path, "node_modules", ".bin", "vitest").exists():
        return repo_path
    # Check common subdirs (ui/, app/, client/, frontend/, web/)
    for subdir in ("ui", "app", "client", "frontend", "web"):
        candidate = Path(repo_path, subdir)
        if candidate.joinpath("node_modules", ".bin", "vitest").exists():
            return str(candidate)
    return None


def _run_vitest(repo_path: str, project_name: str, changed_files: list[str]) -> dict:
    """Run vitest for affected tests. Returns parsed results."""
    vitest_dir = _find_vitest_dir(repo_path)
    if not vitest_dir:
        return None

    # Check if there are test files
    has_tests = any(Path(vitest_dir).rglob("*.test.*")) or any(Path(vitest_dir).rglob("*.spec.*"))
    if not has_tests:
        return None

    start = time.time()
    result_file = f"/tmp/walter-vitest-{project_name}-{uuid.uuid4().hex[:8]}.json"

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
            cwd=vitest_dir, timeout=120,
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
            finally:
                try:
                    os.unlink(result_file)
                except OSError:
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
    result_file = f"/tmp/walter-playwright-{project_name}-{uuid.uuid4().hex[:8]}.json"

    try:
        cmd = [
            "npx", "playwright", "test",
            "--reporter=json",
            "--workers=1",
            "--project=webkit",  # lowest memory per research
        ]
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
def _store_results(results: dict, trigger: str = "watch"):
    """Store test run results in SQLite. Thread-safe via _db_lock (RC5 fix)."""
    if not results or results.get("total", 0) == 0 and not results.get("error"):
        return

    with _db_lock:
        conn = _get_db()
        cursor = conn.execute(
            """INSERT INTO test_runs (runner, project, git_sha, git_branch, duration_ms,
               total, passed, failed, skipped, flaky, trigger, last_tested_sha)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
             trigger,
             results.get("git_sha_full", ""))
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


# --- Push Results to Lockwood (Phase 37 completion) ---
def _push_to_lockwood(results: dict, trigger: str = "watch"):
    """Push test results to Lockwood's /api/memory/tests endpoint.

    Sends rich test health data (SHA, branch, runner, trigger) for cross-project
    sparklines and health tracking. Retries once on failure.
    """
    if not results:
        return

    total = results.get("total", 0)
    passed = results.get("passed", 0)
    pass_rate = round((passed / total * 100), 1) if total > 0 else 0.0

    # Collect failure names from test results
    failures = [
        t.get("full_name", t.get("name", "unknown"))
        for t in results.get("tests", [])
        if t.get("status") == "failed"
    ]

    payload = json.dumps({
        "project": results.get("project", "unknown"),
        "sha": results.get("git_sha", ""),
        "branch": results.get("git_branch", ""),
        "pass_rate": pass_rate,
        "total": total,
        "passed": passed,
        "failed": results.get("failed", 0),
        "skipped": results.get("skipped", 0),
        "failures": failures,
        "duration_ms": results.get("duration_ms"),
        "runner": results.get("runner", "unknown"),
        "trigger": trigger,
    }).encode("utf-8")

    url = f"{LOCKWOOD_URL}/api/memory/tests"
    req = urllib.request.Request(url, data=payload, method="POST",
                                headers={"Content-Type": "application/json"})

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = resp.read().decode("utf-8")
                print(f"  Lockwood push OK (attempt {attempt + 1}): {results.get('project')} -> {resp_data}")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
            print(f"  Lockwood push FAIL (attempt {attempt + 1}): {results.get('project')} -> {e}")
            if attempt == 0:
                time.sleep(2)  # brief pause before retry

    return False


# --- Queue Consumer (RC4 fix: single execution path) ---
def _queue_consumer():
    """Single consumer thread that processes test runs serially from the queue.
    Deduplicates by project+SHA — if a newer SHA is queued for the same project,
    skip the older entry.
    """
    while True:
        try:
            item = _test_queue.get(timeout=5)
        except queue.Empty:
            continue

        run_id = item["run_id"]
        project = item["project"]
        repo_path = item["repo_path"]
        trigger = item.get("trigger", "watch")
        changed = item.get("changed", [])

        # Dedup: check if a newer entry for same project is already queued
        # by peeking at the queue (drain and re-add non-dupes)
        current_sha = _git_sha_full(repo_path)
        skip = False
        pending = []
        try:
            while True:
                next_item = _test_queue.get_nowait()
                if next_item["project"] == project:
                    # Newer entry for same project — skip current, keep newer
                    skip = True
                    pending.append(next_item)
                else:
                    pending.append(next_item)
        except queue.Empty:
            pass
        for p in pending:
            _test_queue.put(p)

        if skip:
            with _run_status_lock:
                _run_status[run_id] = {
                    "status": "skipped", "project": project,
                    "reason": "superseded by newer SHA",
                    "completed_at": datetime.now().isoformat()
                }
            _test_queue.task_done()
            continue

        # Mark as running
        with _run_status_lock:
            _run_status[run_id] = {
                "status": "running", "project": project,
                "started_at": datetime.now().isoformat()
            }
        with _state_lock:
            global _running
            _running = True

        try:
            _execute_test_run(run_id, project, repo_path, trigger, changed)
        except Exception as e:
            print(f"Test run error for {project}: {e}")
            with _run_status_lock:
                _run_status[run_id] = {
                    "status": "error", "project": project,
                    "error": str(e),
                    "completed_at": datetime.now().isoformat()
                }
        finally:
            with _state_lock:
                _running = False
            _test_queue.task_done()


def _execute_test_run(run_id: str, project: str, repo_path: str, trigger: str, changed: list[str]):
    """Execute a single test run for a project."""
    global _last_run_time, _last_results

    git_sha = _git_sha(repo_path)
    git_sha_full = _git_sha_full(repo_path)
    git_branch = _git_branch(repo_path)

    # Auto-rebuild affected test map entries
    _invalidate_test_map_entries(project, changed)
    build_test_map(project, repo_path)

    results_collected = []

    # Run vitest first (fast, per research: stagger, don't parallel)
    vitest_results = _run_vitest(repo_path, project, changed)
    if vitest_results:
        vitest_results["git_sha"] = git_sha
        vitest_results["git_sha_full"] = git_sha_full
        vitest_results["git_branch"] = git_branch
        _store_results(vitest_results, trigger=trigger)
        _push_to_lockwood(vitest_results, trigger=trigger)
        with _state_lock:
            _last_results[f"{project}_vitest"] = vitest_results
        results_collected.append(vitest_results)
        print(f"  vitest: {vitest_results.get('passed', 0)}/{vitest_results.get('total', 0)} passed")

    # Then Playwright (slower, only for UI changes)
    pw_results = _run_playwright(repo_path, project, changed)
    if pw_results:
        pw_results["git_sha"] = git_sha
        pw_results["git_sha_full"] = git_sha_full
        pw_results["git_branch"] = git_branch
        _store_results(pw_results, trigger=trigger)
        _push_to_lockwood(pw_results, trigger=trigger)
        with _state_lock:
            _last_results[f"{project}_playwright"] = pw_results
        results_collected.append(pw_results)
        print(f"  playwright: {pw_results.get('passed', 0)}/{pw_results.get('total', 0)} passed")

    # Update tested SHA after successful run
    if git_sha_full:
        _update_tested_sha(project, git_sha_full)

    with _state_lock:
        _last_run_time = time.time()

    # Update run status
    with _run_status_lock:
        _run_status[run_id] = {
            "status": "complete", "project": project,
            "results": [
                {"runner": r.get("runner"), "passed": r.get("passed", 0),
                 "failed": r.get("failed", 0), "total": r.get("total", 0)}
                for r in results_collected
            ],
            "completed_at": datetime.now().isoformat()
        }


# --- Background Watch Loop ---
def _watch_loop():
    """Polls repos for changes and enqueues test runs."""
    repos_path = Path(REPOS_DIR)

    # First run: seed SHA tracking
    for repo_dir in repos_path.iterdir():
        if repo_dir.is_dir() and not repo_dir.name.startswith("."):
            project = repo_dir.name
            _detect_changes(str(repo_dir), project)

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            for repo_dir in repos_path.iterdir():
                if not repo_dir.is_dir() or repo_dir.name.startswith("."):
                    continue

                project_name = repo_dir.name
                repo_path = str(repo_dir)

                # Pull latest
                _git_pull(repo_path)

                # Detect changes via git SHA
                changed = _detect_changes(repo_path, project_name)
                if not changed:
                    continue

                print(f"Changes in {project_name}: {len(changed)} files")

                # Enqueue test run
                run_id = f"watch-{uuid.uuid4().hex[:8]}"
                with _run_status_lock:
                    _run_status[run_id] = {
                        "status": "queued", "project": project_name,
                        "queued_at": datetime.now().isoformat()
                    }
                _test_queue.put({
                    "run_id": run_id,
                    "project": project_name,
                    "repo_path": repo_path,
                    "trigger": "watch",
                    "changed": changed,
                })
        except Exception as e:
            print(f"Watch loop error: {e}")


@app.on_event("startup")
async def startup():
    # Start queue consumer (single thread — serializes all test runs)
    consumer = threading.Thread(target=_queue_consumer, daemon=True, name="test-consumer")
    consumer.start()
    # Start watch loop (enqueues runs when changes detected)
    watcher = threading.Thread(target=_watch_loop, daemon=True, name="repo-watcher")
    watcher.start()


# --- Extended /health (overrides base_service /health with Walter-specific data) ---
_service_start_time = time.time()


@app.get("/api/health")
async def walter_health():
    """Extended health endpoint with Walter-specific operational data."""
    repos_path = Path(REPOS_DIR)
    repo_heads = {}
    for repo_dir in repos_path.iterdir():
        if repo_dir.is_dir() and not repo_dir.name.startswith("."):
            sha = _git_sha(str(repo_dir))
            if sha:
                repo_heads[repo_dir.name] = sha

    with _state_lock:
        running = _running
        last_run = _last_run_time

    mem = psutil.virtual_memory()

    watched_repos = sorted(repo_heads.keys())

    return {
        "status": "healthy",
        "role": "test-runner",
        "version": SERVICE_VERSION,
        "uptime": round(time.time() - _service_start_time, 1),
        "last_test_run": datetime.fromtimestamp(last_run).isoformat() if last_run > 0 else None,
        "running": running,
        "queue_depth": _test_queue.qsize(),
        "repo_count": len(watched_repos),
        "watched_repos": watched_repos,
        "repo_heads": repo_heads,
        "memory": {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent_used": mem.percent,
        },
    }


# --- API Endpoints ---
@app.get("/api/results")
async def get_results(project: Optional[str] = None, latest: bool = True):
    """Get test results. If latest=true, returns most recent run per project."""
    try:
        with _db_lock:
            conn = _get_db()
            if latest:
                if project:
                    # Get latest run per runner (vitest, playwright) for this project
                    runs = conn.execute(
                        """SELECT * FROM test_runs WHERE run_id IN (
                             SELECT MAX(run_id) FROM test_runs WHERE project = ? GROUP BY runner
                           ) ORDER BY timestamp DESC""",
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

            conn.close()
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.get("/api/coverage")
async def get_coverage(project: Optional[str] = None):
    """Get pass rate as a proxy for coverage."""
    try:
        with _db_lock:
            conn = _get_db()
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
            conn.close()

        total = row["total"] or 0
        passed = row["passed"] or 0
        return {
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "passed": passed,
            "total": total,
        }
    except Exception as e:
        return {"pass_rate": 0, "passed": 0, "total": 0, "error": str(e)}


@app.get("/api/flaky")
async def get_flaky():
    """Detect flaky tests from status oscillation over last 7 days."""
    try:
        with _db_lock:
            conn = _get_db()
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
            conn.close()

        return {"flaky": [
            {"test": r["full_name"], "runs": r["total_runs"], "flips": r["flips"],
             "score": round(r["flips"] / (r["total_runs"] - 1), 3)}
            for r in rows
        ]}
    except Exception as e:
        return {"flaky": [], "error": str(e)}


@app.post("/api/provision")
async def provision_repo(project: str = ""):
    """Ensure a bare repo exists for the given project. Idempotent."""
    if not project:
        return {"status": "error", "message": "project param required"}
    already_existed = os.path.isdir(os.path.join(REPOS_DIR, project))
    repo_path = _ensure_repo(project)
    return {"status": "ok", "project": project, "repo_path": repo_path, "created": not already_existed}


@app.post("/api/run")
async def trigger_run(project: Optional[str] = None, trigger: str = "manual"):
    """Enqueue a test run. Returns run_id for status polling."""
    repos_path = Path(REPOS_DIR)

    # Auto-provision if project specified but repo directory doesn't exist
    if project and not (repos_path / project).is_dir():
        _ensure_repo(project)

    run_ids = []

    for repo_dir in repos_path.iterdir():
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        if project and repo_dir.name.lower() != project.lower():
            continue

        name = repo_dir.name
        repo_path = str(repo_dir)
        run_id = f"{trigger}-{uuid.uuid4().hex[:8]}"

        with _run_status_lock:
            _run_status[run_id] = {
                "status": "queued", "project": name,
                "queued_at": datetime.now().isoformat()
            }

        _test_queue.put({
            "run_id": run_id,
            "project": name,
            "repo_path": repo_path,
            "trigger": trigger,
            "changed": [],  # manual runs test everything
        })
        run_ids.append(run_id)

    if not run_ids:
        return {"status": "error", "message": "no matching projects found"}

    return {"status": "queued", "run_ids": run_ids, "run_id": run_ids[0]}


@app.get("/api/run/{run_id}/status")
async def get_run_status(run_id: str):
    """Poll status of a queued/running test run."""
    with _run_status_lock:
        status = _run_status.get(run_id)
    if not status:
        return {"error": "run_id not found", "run_id": run_id}
    return {"run_id": run_id, **status}


@app.get("/api/testmap")
async def api_get_testmap(files: str = "", project: str = ""):
    """Get test file mapping for given source files."""
    if not files or not project:
        return {"error": "files and project params required"}
    file_list = [f.strip() for f in files.split(",") if f.strip()]
    return get_test_map(file_list, project)


# --- Runtime Alerts (pushed by node_analysis.py) ---
_runtime_alerts: list[dict] = []
_MAX_ALERTS = 50


@app.get("/api/alerts")
async def get_alerts(project: Optional[str] = None, limit: int = 10):
    """Get runtime alerts. Called by developer-brief.sh."""
    alerts = _runtime_alerts[-limit:]
    alerts.reverse()  # newest first
    return {"alerts": alerts}
