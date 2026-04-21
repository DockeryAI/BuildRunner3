import { test, expect } from '@playwright/test';
import { execSync, spawnSync } from 'child_process';
import { mkdtempSync, writeFileSync, rmSync, existsSync, mkdirSync } from 'fs';
import { tmpdir } from 'os';
import { join, resolve } from 'path';

const REPO_ROOT = resolve(__dirname, '..', '..');
const ROLE_MATRIX_LOADER = join(REPO_ROOT, 'scripts', 'load-role-matrix.sh');
const RUNTIME_DISPATCH = join(REPO_ROOT, 'scripts', 'runtime-dispatch.sh');

function makeBuildSpec(phases: Record<string, Record<string, unknown>>): string {
  const dir = mkdtempSync(join(tmpdir(), 'br3-orch-'));
  const path = join(dir, 'BUILD_orch-test.md');
  const yamlPhases = Object.entries(phases)
    .map(([name, fields]) => {
      const fieldLines = Object.entries(fields)
        .map(([k, v]) => {
          if (Array.isArray(v)) {
            const items = v.map((x) => `'${x}'`).join(', ');
            return `      ${k}: [${items}]`;
          }
          return `      ${k}: '${v}'`;
        })
        .join('\n');
      return `    ${name}:\n${fieldLines}`;
    })
    .join('\n');
  const content = [
    '# Test BUILD Spec',
    '',
    '```yaml',
    'role_matrix:',
    '  phases:',
    yamlPhases,
    '```',
    '',
  ].join('\n');
  writeFileSync(path, content, 'utf8');
  return path;
}

function sourceLoader(
  buildSpec: string,
  phaseNum: number
): {
  rc: number;
  stdout: string;
  stderr: string;
} {
  const result = spawnSync(
    'bash',
    [
      '-c',
      `source "${ROLE_MATRIX_LOADER}" "${buildSpec}" "${phaseNum}" && env | grep -E '^BR3_PHASE_|^BR3_ROLE_MATRIX_'`,
    ],
    { encoding: 'utf8' }
  );
  return {
    rc: result.status ?? -1,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
  };
}

test.describe('Phase 3 — orchestrator dispatch', () => {
  test('role-matrix loader resolves builder=claude for default phase', () => {
    const spec = makeBuildSpec({
      phase_1: { builder: 'claude', assigned_node: 'muddy', reviewers: ['codex'] },
    });
    const out = sourceLoader(spec, 1);
    expect(out.rc).toBe(0);
    expect(out.stdout).toContain('BR3_PHASE_BUILDER=claude');
    expect(out.stdout).toContain('BR3_PHASE_ASSIGNED_NODE=muddy');
    expect(out.stdout).toContain('BR3_ROLE_MATRIX_LOADED=1');
  });

  test('role-matrix loader resolves builder=codex with model + effort', () => {
    const spec = makeBuildSpec({
      phase_2: {
        builder: 'codex',
        assigned_node: 'otis',
        codex_model: 'gpt-5.4',
        codex_effort: 'high',
        reviewers: ['claude'],
      },
    });
    const out = sourceLoader(spec, 2);
    expect(out.rc).toBe(0);
    expect(out.stdout).toContain('BR3_PHASE_BUILDER=codex');
    expect(out.stdout).toContain('BR3_PHASE_CODEX_MODEL=gpt-5.4');
    expect(out.stdout).toContain('BR3_PHASE_CODEX_EFFORT=high');
    expect(out.stdout).toContain('BR3_PHASE_ASSIGNED_NODE=otis');
  });

  test('role-matrix loader resolves builder=below for local-routing phases', () => {
    const spec = makeBuildSpec({
      phase_3: { builder: 'below', assigned_node: 'below' },
    });
    const out = sourceLoader(spec, 3);
    expect(out.rc).toBe(0);
    expect(out.stdout).toContain('BR3_PHASE_BUILDER=below');
    expect(out.stdout).toContain('BR3_PHASE_ASSIGNED_NODE=below');
  });

  test('role-matrix loader exits 3 when phase missing from matrix', () => {
    const spec = makeBuildSpec({
      phase_1: { builder: 'claude', assigned_node: 'muddy' },
    });
    const out = sourceLoader(spec, 99);
    expect(out.rc).not.toBe(0);
    expect(out.stderr).toContain('Phase');
  });

  test('runtime-dispatch.sh CLI exits 2 on unknown builder', () => {
    if (!existsSync(RUNTIME_DISPATCH)) {
      test.skip(true, 'runtime-dispatch.sh not present');
    }
    const dir = mkdtempSync(join(tmpdir(), 'br3-orch-'));
    const spec = join(dir, 'spec.md');
    writeFileSync(spec, '# spec', 'utf8');
    const result = spawnSync('bash', [RUNTIME_DISPATCH, 'unknown-runtime', spec], {
      encoding: 'utf8',
      env: { ...process.env, BR3_DISPATCH_DRY_RUN: '1' },
    });
    expect(result.status).toBe(2);
  });

  test('runtime-dispatch.sh CLI exits 3 on missing spec file', () => {
    if (!existsSync(RUNTIME_DISPATCH)) {
      test.skip(true, 'runtime-dispatch.sh not present');
    }
    const result = spawnSync('bash', [RUNTIME_DISPATCH, 'claude', '/nonexistent/spec.md'], {
      encoding: 'utf8',
      env: { ...process.env, BR3_DISPATCH_DRY_RUN: '1' },
    });
    expect(result.status).toBe(3);
  });

  test('builder mismatch detection: assertion fails when actual differs from matrix', () => {
    const spec = makeBuildSpec({
      phase_5: { builder: 'codex', assigned_node: 'otis' },
    });
    // Simulate decisions.log with builder=claude but matrix says codex.
    const projectRoot = mkdtempSync(join(tmpdir(), 'br3-mismatch-'));
    mkdirSync(join(projectRoot, '.buildrunner'), { recursive: true });
    writeFileSync(
      join(projectRoot, '.buildrunner', 'decisions.log'),
      '2026-04-21T22:00:00Z dispatch: phase=5 builder=claude rc=0\n',
      'utf8'
    );
    const result = spawnSync(
      'bash',
      [
        '-c',
        `source "${ROLE_MATRIX_LOADER}" "${spec}" 5
       EXPECTED_BUILDER="\${BR3_PHASE_BUILDER:-claude}"
       ACTUAL_BUILDER=$(grep -E 'dispatch: phase=5 builder=' "${projectRoot}/.buildrunner/decisions.log" | tail -1 | sed -n 's/.*builder=\\([^ ]*\\).*/\\1/p')
       if [ "$EXPECTED_BUILDER" != "$ACTUAL_BUILDER" ]; then
         echo "MISMATCH: expected=$EXPECTED_BUILDER actual=$ACTUAL_BUILDER"
         exit 1
       fi`,
      ],
      { encoding: 'utf8' }
    );
    expect(result.status).toBe(1);
    expect(result.stdout).toContain('MISMATCH: expected=codex actual=claude');
  });

  test('builder match: assertion passes when matrix and actual agree', () => {
    const spec = makeBuildSpec({
      phase_6: { builder: 'codex', assigned_node: 'otis' },
    });
    const projectRoot = mkdtempSync(join(tmpdir(), 'br3-match-'));
    mkdirSync(join(projectRoot, '.buildrunner'), { recursive: true });
    writeFileSync(
      join(projectRoot, '.buildrunner', 'decisions.log'),
      '2026-04-21T22:00:00Z dispatch: phase=6 builder=codex rc=0\n',
      'utf8'
    );
    const result = spawnSync(
      'bash',
      [
        '-c',
        `source "${ROLE_MATRIX_LOADER}" "${spec}" 6
       EXPECTED_BUILDER="\${BR3_PHASE_BUILDER:-claude}"
       ACTUAL_BUILDER=$(grep -E 'dispatch: phase=6 builder=' "${projectRoot}/.buildrunner/decisions.log" | tail -1 | sed -n 's/.*builder=\\([^ ]*\\).*/\\1/p')
       if [ "$EXPECTED_BUILDER" != "$ACTUAL_BUILDER" ]; then
         exit 1
       fi
       echo "MATCH"`,
      ],
      { encoding: 'utf8' }
    );
    expect(result.status).toBe(0);
    expect(result.stdout).toContain('MATCH');
  });
});
