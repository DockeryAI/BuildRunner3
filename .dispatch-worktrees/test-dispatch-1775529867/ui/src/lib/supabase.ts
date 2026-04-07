/**
 * Instrumented Supabase client.
 * Wraps fetch to log all Supabase operations to .buildrunner/supabase.log via dev server.
 * Zero overhead in production — logger is a no-op when import.meta.env.DEV is false.
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { logOperation, logEvent } from './supabaseLogger';

let client: SupabaseClient | null = null;

function createInstrumentedFetch(originalFetch: typeof globalThis.fetch): typeof globalThis.fetch {
  return async (input, init) => {
    const url = typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;

    // Only instrument requests to our Supabase instance
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
    if (!url.startsWith(supabaseUrl)) {
      return originalFetch(input, init);
    }

    const method = init?.method || 'GET';
    const start = performance.now();

    const response = await originalFetch(input, init);
    const durationMs = Math.round(performance.now() - start);

    // Clone to read body size without consuming the stream
    let responseSize = 0;
    try {
      const cloned = response.clone();
      const body = await cloned.text();
      responseSize = body.length;
    } catch {
      // If clone/read fails, log 0 — not worth crashing over
    }

    logOperation({
      method,
      url,
      status: response.status,
      durationMs,
      responseSize,
    });

    return response;
  };
}

export function getSupabaseClient(): SupabaseClient {
  if (client) return client;

  const url = import.meta.env.VITE_SUPABASE_URL;
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY;

  if (!url || !key) {
    if (import.meta.env.DEV) {
      console.warn(
        '[supabase] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY in .env.local — Supabase calls will fail.'
      );
    }
    // Still create client so imports don't explode; calls will fail with clear errors
  }

  const instrumentedFetch = import.meta.env.DEV
    ? createInstrumentedFetch(globalThis.fetch.bind(globalThis))
    : undefined;

  client = createClient(url || '', key || '', {
    global: {
      ...(instrumentedFetch ? { fetch: instrumentedFetch } : {}),
    },
  });

  // Log auth state changes in dev
  if (import.meta.env.DEV) {
    client.auth.onAuthStateChange((event, session) => {
      logEvent('AUTH', `${event} user=${session?.user?.id ?? 'none'}`);
    });
  }

  return client;
}

/**
 * Helper to log realtime channel events. Pass as callback when subscribing:
 *   channel.on('postgres_changes', { ... }, logRealtimeEvent)
 */
export function logRealtimeEvent(payload: Record<string, unknown>): void {
  if (!import.meta.env.DEV) return;
  const table = (payload as { table?: string }).table ?? 'unknown';
  const eventType = (payload as { eventType?: string }).eventType ?? 'unknown';
  logEvent('REALTIME', `${eventType} on ${table}`);
}
