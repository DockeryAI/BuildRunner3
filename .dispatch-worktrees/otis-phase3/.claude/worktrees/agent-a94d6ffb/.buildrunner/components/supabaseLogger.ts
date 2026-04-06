/**
 * BR3 Supabase Operation Logger — Dev Only
 * POSTs log lines to Vite dev server middleware at /__supabase_log,
 * which writes them to .buildrunner/supabase.log for Claude debugging.
 *
 * Usage in your supabase client:
 *   import { createInstrumentedFetch, logEvent } from '.buildrunner/components/supabaseLogger';
 *   const client = createClient(url, key, {
 *     global: { fetch: import.meta.env.DEV ? createInstrumentedFetch(fetch, url) : undefined }
 *   });
 *
 * READONLY — DO NOT MODIFY. Part of BR3 infrastructure.
 */

type OpType = 'QUERY' | 'AUTH' | 'STORAGE' | 'EDGE_FN' | 'REALTIME' | 'UNKNOWN';

interface LogEntry {
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

function logOperation(entry: LogEntry): void {
  if (!import.meta.env.DEV) return;

  const line = formatLine(entry);
  const warning = detectWarnings(entry);
  const payload = warning ? `${line}\n  ${warning}` : line;

  fetch('/__supabase_log', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: payload,
  }).catch(() => {});
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

/**
 * Wraps a fetch function to log all requests to the given Supabase URL.
 * Pass this as `global.fetch` in createClient options.
 */
export function createInstrumentedFetch(
  originalFetch: typeof globalThis.fetch,
  supabaseUrl: string
): typeof globalThis.fetch {
  return async (input, init) => {
    const url = typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;

    // Only instrument requests to our Supabase instance
    if (!url.startsWith(supabaseUrl)) {
      return originalFetch(input, init);
    }

    const method = init?.method || 'GET';
    const start = performance.now();

    const response = await originalFetch(input, init);
    const durationMs = Math.round(performance.now() - start);

    let responseSize = 0;
    let debugLogs: string[] | undefined;
    try {
      const cloned = response.clone();
      const body = await cloned.text();
      responseSize = body.length;

      // Extract edge function debug logs from _debug field
      if (url.includes('/functions/')) {
        try {
          const json = JSON.parse(body);
          if (Array.isArray(json._debug)) {
            debugLogs = json._debug;
          }
        } catch { /* not JSON or no _debug */ }
      }
    } catch {
      // If clone/read fails, log 0
    }

    logOperation({ method, url, status: response.status, durationMs, responseSize });

    // Flush edge function internal logs
    if (debugLogs && debugLogs.length > 0) {
      const fnName = url.split('/functions/v1/')[1]?.split('?')[0] || 'unknown';
      const lines = debugLogs.map(l => `  [EDGE_FN:${fnName}] ${l}`).join('\n');
      fetch('/__supabase_log', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: lines,
      }).catch(() => {});
    }

    return response;
  };
}
