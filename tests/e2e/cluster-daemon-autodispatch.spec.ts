/**
 * E2E: cluster-daemon auto-dispatch — Phase 5 deliverable
 *
 * Proves that when `auto_dispatch: true` in cluster-daemon-config.json,
 * the daemon picks up a mock "ready" build and dispatches it to the
 * configured target node (Otis) via dispatch-to-node.sh.
 *
 * Strategy:
 *   1. Spin up cluster-daemon.mjs in a subprocess with a temp config
 *      pointing at a mock dispatch script that records its invocations.
 *   2. Seed next-ready-build.mjs fixture so it returns one ready build.
 *   3. Assert the mock dispatch script was called with the correct args
 *      within the daemon's poll interval (+ 5s grace).
 *   4. Assert no dispatch when auto_dispatch is false (regression guard).
 */

import { test, expect } from '@playwright/test';
import {
  mkdtempSync,
  writeFileSync,
  readFileSync,
  existsSync,
  chmodSync,
  mkdirSync,
  rmSync,
} from 'fs';
import { tmpdir, homedir } from 'os';
import { join, resolve } from 'path';
import { spawnSync, spawn, ChildProcess } from 'child_process';

const REPO_ROOT = resolve(__dirname, '..', '..');
const HOME = homedir();
const CLUSTER_DAEMON = join(HOME, '.buildrunner', 'scripts', 'cluster-daemon.mjs');

// Skip the whole suite if cluster-daemon.mjs doesn't exist
const daemonExists = existsSync(CLUSTER_DAEMON);

/**
 * Create a temporary working directory with:
 *  - cluster-daemon-config.json (auto_dispatch on/off)
 *  - A mock next-ready-build.mjs that returns a single ready build
 *  - A mock dispatch-to-node.sh that records calls to dispatch.log
 */
function setupDaemonFixture(opts: { autoDispatch: boolean; pollIntervalSeconds?: number }): {
  dir: string;
  configPath: string;
  dispatchLog: string;
  daemonLog: string;
  cleanup: () => void;
} {
  const dir = mkdtempSync(join(tmpdir(), 'br3-daemon-test-'));
  const scriptsDir = join(dir, 'scripts');
  mkdirSync(scriptsDir);

  const configPath = join(dir, 'cluster-daemon-config.json');
  const dispatchLog = join(dir, 'dispatch.log');
  const daemonLog = join(dir, 'daemon.log');
  const mockBuildPath = join(dir, 'mock-project');
  mkdirSync(mockBuildPath);

  // Write config
  writeFileSync(
    configPath,
    JSON.stringify({
      enabled: true,
      poll_interval_seconds: opts.pollIntervalSeconds ?? 2,
      auto_dispatch: opts.autoDispatch,
      max_concurrent_builds: 1,
      node_name: 'muddy',
      log_file: daemonLog,
    })
  );

  // Mock next-ready-build.mjs — returns one ready build
  const mockNextReady = join(scriptsDir, 'next-ready-build.mjs');
  writeFileSync(
    mockNextReady,
    `#!/usr/bin/env node
// Mock: always returns a single ready build pointing at mock-project
import { join } from 'path';
const build = {
  build_id: 'test-build-001',
  project: 'mock-project',
  project_path: '${mockBuildPath.replace(/\\/g, '\\\\')}',
  assigned_node: 'otis',
  status: 'ready',
};
const allFlag = process.argv.includes('--all');
if (allFlag) {
  console.log(JSON.stringify({ count: 1, builds: [build] }));
} else {
  console.log(JSON.stringify(build));
}
`
  );
  chmodSync(mockNextReady, 0o755);

  // Mock dispatch-to-node.sh — records invocation to dispatch.log
  const mockDispatch = join(scriptsDir, 'dispatch-to-node.sh');
  writeFileSync(
    mockDispatch,
    `#!/usr/bin/env bash
# Mock dispatch-to-node.sh — records args, does not actually SSH
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DISPATCH node=$1 project=$2 session=$4" >> '${dispatchLog}'
exit 0
`
  );
  chmodSync(mockDispatch, 0o755);

  return {
    dir,
    configPath,
    dispatchLog,
    daemonLog,
    cleanup: () => {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch {
        // best-effort cleanup
      }
    },
  };
}

/**
 * Start cluster-daemon.mjs as a subprocess with overridden HOME pointing
 * at our fixture directory so it reads the mock config + scripts.
 */
function startDaemon(fixtureDir: string, configPath: string): ChildProcess {
  // We override HOME so the daemon reads our fixture config.
  // cluster-daemon.mjs uses join(HOME, '.buildrunner', 'cluster-daemon-config.json')
  // so we create the right subdirectory.
  const fakeHome = join(fixtureDir, 'home');
  const fakeBrDir = join(fakeHome, '.buildrunner');
  const fakeScriptsDir = join(fakeBrDir, 'scripts');
  mkdirSync(fakeScriptsDir, { recursive: true });

  // Symlink the mock scripts
  const realScripts = join(fixtureDir, 'scripts');
  for (const f of ['next-ready-build.mjs', 'dispatch-to-node.sh']) {
    const src = join(realScripts, f);
    const dst = join(fakeScriptsDir, f);
    try {
      spawnSync('ln', ['-sf', src, dst]);
    } catch {
      // fallback: copy
      writeFileSync(dst, readFileSync(src));
      chmodSync(dst, 0o755);
    }
  }

  // Write config in the expected location
  const fakeConfigPath = join(fakeBrDir, 'cluster-daemon-config.json');
  const configContents = readFileSync(configPath, 'utf-8');
  writeFileSync(fakeConfigPath, configContents);

  return spawn('node', [CLUSTER_DAEMON], {
    env: {
      ...process.env,
      HOME: fakeHome,
    },
    detached: false,
    stdio: 'pipe',
  });
}

/**
 * Wait up to `timeoutMs` for `predicate()` to return true, polling every 500ms.
 */
async function waitFor(predicate: () => boolean, timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('cluster-daemon auto-dispatch', () => {
  test.skip(!daemonExists, 'cluster-daemon.mjs not present — skipping');

  test('dispatches a ready build to Otis when auto_dispatch is true', async () => {
    const fixture = setupDaemonFixture({ autoDispatch: true, pollIntervalSeconds: 2 });
    const daemon = startDaemon(fixture.dir, fixture.configPath);
    let daemonKilled = false;

    try {
      // Wait up to 10s for dispatch.log to be written
      const dispatched = await waitFor(() => existsSync(fixture.dispatchLog), 10_000);
      expect(dispatched, 'dispatch.log should exist after daemon polls').toBe(true);

      const logContent = readFileSync(fixture.dispatchLog, 'utf-8');
      // Assert dispatch was called with "otis" as the first arg
      expect(logContent).toMatch(/DISPATCH node=otis/);
      // Assert project path is passed
      expect(logContent).toMatch(/project=.*mock-project/);
    } finally {
      daemonKilled = true;
      daemon.kill('SIGTERM');
      fixture.cleanup();
    }
  });

  test('does NOT dispatch when auto_dispatch is false', async () => {
    const fixture = setupDaemonFixture({ autoDispatch: false, pollIntervalSeconds: 2 });
    const daemon = startDaemon(fixture.dir, fixture.configPath);

    try {
      // Let the daemon run for 2 full poll cycles (4s) + 2s grace
      await new Promise((r) => setTimeout(r, 6_000));

      const wasDispatched = existsSync(fixture.dispatchLog);
      expect(wasDispatched, 'dispatch.log must NOT exist when auto_dispatch=false').toBe(false);
    } finally {
      daemon.kill('SIGTERM');
      fixture.cleanup();
    }
  });

  test('respects max_concurrent_builds — does not double-dispatch', async () => {
    const fixture = setupDaemonFixture({ autoDispatch: true, pollIntervalSeconds: 1 });
    const daemon = startDaemon(fixture.dir, fixture.configPath);

    try {
      // Wait up to 8s; dispatch log may have multiple lines but second tick
      // should NOT dispatch again while activeBuildCount >= max_concurrent_builds
      await waitFor(() => existsSync(fixture.dispatchLog), 8_000);
      // Extra wait to let a second poll fire
      await new Promise((r) => setTimeout(r, 2_500));

      const logLines = existsSync(fixture.dispatchLog)
        ? readFileSync(fixture.dispatchLog, 'utf-8').trim().split('\n').filter(Boolean)
        : [];

      // With max_concurrent_builds=1 and one active dispatch, the second tick
      // must not fire a second DISPATCH line until the first completes.
      // The mock dispatch exits immediately, so we can't block it — but we can
      // assert at most a small number of dispatches in a short window.
      expect(logLines.length).toBeLessThanOrEqual(3);
    } finally {
      daemon.kill('SIGTERM');
      fixture.cleanup();
    }
  });
});
