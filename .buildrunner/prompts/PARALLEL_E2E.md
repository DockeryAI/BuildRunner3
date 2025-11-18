# Worktree C: Parallel E2E Tests (3-4 hours)

## Goal
Create comprehensive E2E tests for parallel orchestration with real git worktrees.

## Tasks

### 1. Test Infrastructure (1 hour)
**File**: `tests/e2e/test_parallel_execution.py`

```python
import pytest
import subprocess
from pathlib import Path

@pytest.fixture
def test_repo(tmp_path):
    """Create isolated test git repository"""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(['git', 'init'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=repo)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo)

    # Initial commit
    (repo / 'README.md').write_text('test')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True)

    yield repo

    # Cleanup worktrees
    result = subprocess.run(
        ['git', 'worktree', 'list', '--porcelain'],
        cwd=repo, capture_output=True, text=True
    )
    for line in result.stdout.split('\n'):
        if line.startswith('worktree '):
            wt_path = line.split()[1]
            if wt_path != str(repo):
                subprocess.run(['git', 'worktree', 'remove', wt_path], cwd=repo)
```

### 2. Scenario 1: Independent Tasks (1.5 hours)
Test 4 tasks in parallel with no file conflicts.

```python
def test_four_independent_tasks_parallel(test_repo):
    """4 independent tasks execute in parallel successfully"""
    from core.parallel.session_manager import SessionManager

    session = SessionManager(test_repo)
    session.create_session("test", total_tasks=4)

    # Create tasks (different files = no conflicts)
    tasks = [
        {'id': 't1', 'files': ['file1.txt'], 'content': 'task 1'},
        {'id': 't2', 'files': ['file2.txt'], 'content': 'task 2'},
        {'id': 't3', 'files': ['file3.txt'], 'content': 'task 3'},
        {'id': 't4', 'files': ['file4.txt'], 'content': 'task 4'},
    ]

    results = session.execute_parallel(tasks)

    assert len(results) == 4
    assert all(r['success'] for r in results)
    assert session.get_conflicts() == []
```

### 3. Scenario 2: File Dependencies (1.5 hours)
Test file locking prevents concurrent write conflicts.

```python
def test_file_locking_prevents_conflicts(test_repo):
    """File locking prevents concurrent writes to same file"""
    from core.parallel.file_lock import FileLockManager
    from concurrent.futures import ThreadPoolExecutor

    lock_mgr = FileLockManager(test_repo)

    # Two tasks want same file
    shared_file = test_repo / 'shared.txt'
    results = []

    def write_task(task_id):
        try:
            with lock_mgr.acquire('shared.txt', task_id):
                # Simulate work
                content = shared_file.read_text() if shared_file.exists() else ''
                content += f'{task_id}\n'
                time.sleep(0.1)  # Simulate processing
                shared_file.write_text(content)
                return {'success': True, 'task_id': task_id}
        except FileLockError:
            return {'success': False, 'task_id': task_id, 'error': 'locked'}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(write_task, 't1'),
            executor.submit(write_task, 't2')
        ]
        results = [f.result() for f in futures]

    # One should succeed immediately, one should wait or fail
    successes = [r for r in results if r['success']]
    assert len(successes) >= 1  # At least one succeeded

    # File should not be corrupted
    content = shared_file.read_text()
    assert 't1' in content or 't2' in content
    assert content.count('\n') <= 2  # No corruption
```

### 4. Scenario 3: Worker Failure Recovery (1 hour)
Test system recovers when worker fails.

```python
def test_worker_failure_recovery(test_repo):
    """System recovers when worker fails mid-execution"""
    from core.parallel.worker_coordinator import WorkerCoordinator

    coordinator = WorkerCoordinator(test_repo)
    coordinator.start_workers(3)

    # Queue tasks
    tasks = [{'id': f't{i}'} for i in range(10)]
    coordinator.queue_tasks(tasks)

    # Simulate worker failure after 2 tasks
    time.sleep(1)
    worker_id = coordinator.workers[0].id
    coordinator.kill_worker(worker_id)

    # Check health
    health = coordinator.check_health()
    assert len(health['failed_workers']) == 1

    # Verify tasks redistribute
    coordinator.redistribute_tasks(worker_id)
    remaining = coordinator.get_pending_tasks()
    assert remaining  # Tasks moved to other workers

    # Recovery
    coordinator.restart_worker(worker_id)
    final_health = coordinator.check_health()
    assert len(final_health['healthy_workers']) == 3
```

### 5. Scenario 4: Dashboard Updates (1 hour)
Test real-time progress updates.

```python
def test_dashboard_real_time_updates(test_repo):
    """Dashboard receives real-time progress updates"""
    from core.parallel.session_manager import SessionManager
    from core.parallel.dashboard import Dashboard

    session = SessionManager(test_repo)
    dashboard = Dashboard(session)

    updates = []
    dashboard.subscribe(lambda state: updates.append(state))

    # Execute tasks
    tasks = [{'id': f't{i}'} for i in range(5)]
    session.execute_parallel(tasks)

    # Verify updates received
    assert len(updates) >= 5  # At least one per task

    # Verify progression
    assert updates[0]['completed'] < updates[-1]['completed']

    # Verify final state
    final = dashboard.get_state()
    assert final['completed'] == 5
    assert final['failed'] == 0
```

## Acceptance Criteria
- [ ] All 4 E2E scenarios passing
- [ ] Real git worktrees created and cleaned up
- [ ] File locking validated with concurrent writes
- [ ] Worker coordination tested
- [ ] Dashboard updates tested
- [ ] Tests isolated (use tmp_path)
- [ ] No test flakiness (reproducible)
- [ ] Quality check passes

## Notes
- Use subprocess for real git operations
- Clean up worktrees in fixtures
- Use tmp_path for isolation
- Handle race conditions in concurrent tests
- Add timeouts to prevent hangs
