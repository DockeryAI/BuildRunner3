import { describe, it, expect, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

/**
 * Tests the log rotation logic from vite.config.ts.
 * Since rotateLogIfNeeded isn't exported, we replicate the exact same logic
 * here to validate the algorithm. The constants and function body match
 * vite.config.ts exactly.
 */

const LOG_MAX_BYTES = 500 * 1024;
const LOG_KEEP_BYTES = 250 * 1024;

function rotateLogIfNeeded(logPath: string): void {
  try {
    const stat = fs.statSync(logPath);
    if (stat.size > LOG_MAX_BYTES) {
      const content = fs.readFileSync(logPath, 'utf-8');
      const cutIndex = content.indexOf('\n', content.length - LOG_KEEP_BYTES);
      if (cutIndex !== -1) {
        fs.writeFileSync(logPath, content.slice(cutIndex + 1));
      }
    }
  } catch {
    // File doesn't exist yet — nothing to rotate
  }
}

describe('log rotation', () => {
  const tmpDir = path.join(os.tmpdir(), 'supalog-rotation-test');
  const logPath = path.join(tmpDir, 'test-supabase.log');

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('does not rotate when file is under 500KB', () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    const smallContent = 'line\n'.repeat(1000); // ~5KB
    fs.writeFileSync(logPath, smallContent);

    rotateLogIfNeeded(logPath);

    const result = fs.readFileSync(logPath, 'utf-8');
    expect(result).toBe(smallContent);
  });

  it('rotates when file exceeds 500KB, keeping ~250KB', () => {
    fs.mkdirSync(tmpDir, { recursive: true });

    // Generate a file over 500KB with numbered lines for verification
    const lines: string[] = [];
    let totalSize = 0;
    let lineNum = 0;
    while (totalSize < 600 * 1024) {
      const line = `[2026-02-26T00:00:00Z] [QUERY] GET /rest/v1/table ${lineNum}\n`;
      lines.push(line);
      totalSize += line.length;
      lineNum++;
    }
    fs.writeFileSync(logPath, lines.join(''));

    const sizeBefore = fs.statSync(logPath).size;
    expect(sizeBefore).toBeGreaterThan(LOG_MAX_BYTES);

    rotateLogIfNeeded(logPath);

    const sizeAfter = fs.statSync(logPath).size;
    // Should be roughly 250KB (within tolerance of nearest newline)
    expect(sizeAfter).toBeLessThanOrEqual(LOG_KEEP_BYTES + 200);
    expect(sizeAfter).toBeGreaterThan(0);

    // Should start at a line boundary (no partial lines)
    const result = fs.readFileSync(logPath, 'utf-8');
    expect(result).toMatch(/^\[2026/);
  });

  it('preserves complete lines after rotation', () => {
    fs.mkdirSync(tmpDir, { recursive: true });

    const line = '[2026-02-26T12:00:00Z] [QUERY] GET /rest/v1/data 200 10ms 128b\n';
    const count = Math.ceil((600 * 1024) / line.length);
    fs.writeFileSync(logPath, line.repeat(count));

    rotateLogIfNeeded(logPath);

    const content = fs.readFileSync(logPath, 'utf-8');
    const resultLines = content.split('\n').filter(Boolean);

    // Every line should be complete (starts with timestamp bracket)
    for (const l of resultLines) {
      expect(l).toMatch(/^\[2026-02-26T12:00:00Z\]/);
    }
  });

  it('handles non-existent file gracefully', () => {
    // Should not throw
    expect(() => rotateLogIfNeeded('/tmp/nonexistent-supalog-test.log')).not.toThrow();
  });
});
