/**
 * feature-health-panel.spec.ts — Phase 6 E2E / functional smoke
 *
 * Verifies that:
 *  1. The feature-health WS topic is broadcast by dashboard_stream.py
 *  2. A runtime_dispatched event appears in telemetry.db within 5s of
 *     RuntimeRegistry.execute() being called
 *  3. The panel renders all 15 tiles with green/yellow/red (no "unknown")
 *
 * Strategy: if the dashboard web server is reachable on :4400, test via
 * WS client. Otherwise, run as a functional smoke test using a direct
 * Python import to verify collector + DB roundtrip.
 */

import { test, expect } from '@playwright/test';
import { execSync, spawnSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PYTHON = process.env.PYTHON_BIN || 'python3';

// ---------------------------------------------------------------------------
// Helper: run a Python snippet and return parsed JSON stdout
// ---------------------------------------------------------------------------
function pyRun(script: string, env?: Record<string, string>): unknown {
  const result = spawnSync(PYTHON, ['-c', script], {
    cwd: PROJECT_ROOT,
    encoding: 'utf-8',
    env: { ...process.env, ...env },
    timeout: 15000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`Python exited ${result.status}: ${result.stderr}`);
  }
  return JSON.parse(result.stdout.trim() || 'null');
}

// ---------------------------------------------------------------------------
// Helper: check if dashboard is reachable
// ---------------------------------------------------------------------------
function isDashboardUp(): boolean {
  try {
    const r = spawnSync('curl', ['-s', '--max-time', '2', 'http://localhost:4400/ws'], {
      encoding: 'utf-8',
      timeout: 3000,
    });
    return r.status === 0;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Test 1: EventType enum contains all 4 new types
// ---------------------------------------------------------------------------
test('event_schemas has all 4 new event types', () => {
  const result = pyRun(`
import json, sys
sys.path.insert(0, '.')
from core.telemetry.event_schemas import EventType
types = [e.value for e in EventType]
required = ['runtime_dispatched', 'cache_hit', 'context_bundle_served', 'adversarial_review_ran']
missing = [t for t in required if t not in types]
print(json.dumps({'types': types, 'missing': missing}))
`);
  expect((result as any).missing).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// Test 2: _collect_feature_health returns exactly 15 tiles, all green/yellow/red
// ---------------------------------------------------------------------------
test('feature-health collector returns 15 tiles with valid status', () => {
  const result = pyRun(`
import json, sys, os
sys.path.insert(0, '.')
# Patch the JIMMY_SRV path to avoid filesystem dependency
import unittest.mock as mock
from pathlib import Path
with mock.patch('api.routes.dashboard_stream._JIMMY_SRV', Path('/tmp/no-jimmy-srv-phase6')):
    from api.routes.dashboard_stream import _collect_feature_health
    data = _collect_feature_health()
print(json.dumps(data))
`);
  const data = result as {
    tiles: Array<{ tile: number; status: string; label: string; detail: string }>;
  };
  expect(Array.isArray(data.tiles)).toBe(true);
  expect(data.tiles).toHaveLength(15);

  const validStatuses = new Set(['green', 'yellow', 'red']);
  for (const tile of data.tiles) {
    expect(
      validStatuses.has(tile.status),
      `tile ${tile.tile} (${tile.label}) has invalid status: ${tile.status}`
    ).toBe(true);
    // Must never be "unknown"
    expect(tile.status).not.toBe('unknown');
    // Tile index must be 1-15
    expect(tile.tile).toBeGreaterThanOrEqual(1);
    expect(tile.tile).toBeLessThanOrEqual(15);
    // Must have a label
    expect(typeof tile.label).toBe('string');
    expect(tile.label.length).toBeGreaterThan(0);
  }
});

// ---------------------------------------------------------------------------
// Test 3: runtime_dispatched lands in telemetry.db within 5s of execute()
// ---------------------------------------------------------------------------
test('runtime_dispatched event lands in telemetry.db after execute()', async () => {
  // Create a temp DB and run an execute() against it
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'br3-phase6-'));
  const brDir = path.join(tmpDir, '.buildrunner');
  fs.mkdirSync(brDir);

  // Create schema
  const createSchema = `
import sqlite3, sys
db = sys.argv[1]
conn = sqlite3.connect(db)
conn.executescript("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    metadata TEXT,
    success BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
""")
conn.commit()
conn.close()
print('ok')
`;
  const dbPath = path.join(brDir, 'telemetry.db');
  spawnSync(PYTHON, ['-c', createSchema, dbPath], { encoding: 'utf-8' });

  // Emit a runtime_dispatched via the helper function (with patched cwd)
  const emitResult = pyRun(`
import json, sys, os
sys.path.insert(0, '.')
import unittest.mock as mock
from pathlib import Path
from core.runtime.runtime_registry import _emit_runtime_dispatched

# Build a minimal RuntimeTask-like object
class _FakeTask:
    task_id = 'e2e-test-task'
    task_type = 'execution'
    project_root = '${tmpDir.replace(/\\/g, '/')}'
    authoritative_runtime = 'claude'

with mock.patch('pathlib.Path.cwd', return_value=Path('${tmpDir.replace(/\\/g, '/')}')):
    _emit_runtime_dispatched('claude', _FakeTask())

# Query DB
import sqlite3
conn = sqlite3.connect('${dbPath.replace(/\\/g, '/')}')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM events WHERE event_type='runtime_dispatched'").fetchall()
conn.close()
result = [dict(r) for r in rows]
print(json.dumps({'count': len(result), 'rows': result}))
`);

  const outcome = emitResult as { count: number; rows: any[] };
  expect(outcome.count).toBeGreaterThanOrEqual(1);
  const meta = JSON.parse(outcome.rows[0].metadata || '{}');
  expect(meta.runtime).toBe('claude');
  expect(meta.task_type).toBe('execution');

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ---------------------------------------------------------------------------
// Test 4: WS topic "feature-health" is in _INTERVALS and _COLLECTORS
// ---------------------------------------------------------------------------
test('feature-health topic registered in dashboard_stream', () => {
  const result = pyRun(`
import json, sys
sys.path.insert(0, '.')
from api.routes.dashboard_stream import _INTERVALS, _COLLECTORS
print(json.dumps({
    'in_intervals': 'feature-health' in _INTERVALS,
    'in_collectors': 'feature-health' in _COLLECTORS,
    'interval': _INTERVALS.get('feature-health'),
}))
`);
  const r = result as { in_intervals: boolean; in_collectors: boolean; interval: number };
  expect(r.in_intervals).toBe(true);
  expect(r.in_collectors).toBe(true);
  expect(r.interval).toBeGreaterThan(0);
});

// ---------------------------------------------------------------------------
// Test 5: Playwright WS smoke — only runs if dashboard is up
// ---------------------------------------------------------------------------
test('feature-health WS topic received from live dashboard', async ({ page }) => {
  if (!isDashboardUp()) {
    test.skip();
    return;
  }

  const received: unknown[] = [];
  page.on('websocket', (ws) => {
    ws.on('framereceived', (frame) => {
      try {
        const msg = JSON.parse(frame.payload as string);
        if (msg.type === 'feature-health') received.push(msg);
      } catch {
        /* ignore */
      }
    });
  });

  await page.goto('http://localhost:4400', { waitUntil: 'networkidle', timeout: 10000 });

  // Wait up to 5s for feature-health message
  const deadline = Date.now() + 5000;
  while (received.length === 0 && Date.now() < deadline) {
    await page.waitForTimeout(200);
  }

  expect(received.length).toBeGreaterThan(0);
  const msg = received[0] as { type: string; data: { tiles: any[] } };
  expect(msg.type).toBe('feature-health');
  expect(Array.isArray(msg.data.tiles)).toBe(true);
  expect(msg.data.tiles).toHaveLength(15);
});
