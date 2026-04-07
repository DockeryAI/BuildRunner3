/**
 * Supabase operation logger — dev only.
 * POSTs log lines to Vite dev server middleware at /__supabase_log,
 * which appends them to .buildrunner/supabase.log for Claude debugging.
 */

type OpType = 'QUERY' | 'AUTH' | 'STORAGE' | 'EDGE_FN' | 'REALTIME' | 'UNKNOWN';

export interface LogEntry {
  method: string;
  url: string;
  status: number;
  durationMs: number;
  responseSize: number;
}

function detectOpType(url: string): OpType {
  if (url.includes('/rest/')) return 'QUERY';
  if (url.includes('/auth/')) return 'AUTH';
  if (url.includes('/storage/')) return 'STORAGE';
  if (url.includes('/functions/')) return 'EDGE_FN';
  if (url.includes('/realtime/')) return 'REALTIME';
  return 'UNKNOWN';
}

function formatLine(entry: LogEntry): string {
  const ts = new Date().toISOString();
  const op = detectOpType(entry.url);
  const path = new URL(entry.url).pathname;
  return `[${ts}] [${op}] ${entry.method} ${path} ${entry.status} ${entry.durationMs}ms ${entry.responseSize}b`;
}

function detectWarnings(entry: LogEntry): string | null {
  if (entry.status === 200 && entry.responseSize === 0) {
    return '⚠ EMPTY_200 — possible RLS denial (200 OK but no data returned)';
  }
  if (entry.status >= 400 && entry.status < 500) {
    return `⚠ CLIENT_ERROR ${entry.status} — check auth/permissions`;
  }
  if (entry.status >= 500) {
    return `⚠ SERVER_ERROR ${entry.status} — Supabase issue`;
  }
  if (entry.url.includes('/auth/v1/token') && entry.status !== 200) {
    return `⚠ TOKEN_REFRESH_FAIL ${entry.status}`;
  }
  return null;
}

export function logOperation(entry: LogEntry): void {
  if (!import.meta.env.DEV) return;

  const line = formatLine(entry);
  const warning = detectWarnings(entry);
  const payload = warning ? `${line}\n  ${warning}` : line;

  fetch('/__supabase_log', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: payload,
  }).catch(() => {
    // Silently fail — don't pollute console if dev server middleware isn't running
  });
}

export function logEvent(category: string, message: string): void {
  if (!import.meta.env.DEV) return;

  const ts = new Date().toISOString();
  const payload = `[${ts}] [${category}] ${message}`;

  fetch('/__supabase_log', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: payload,
  }).catch(() => {});
}
