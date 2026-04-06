/**
 * BR3 Browser Logger Component — v3
 * Captures console output, network requests, and errors.
 *
 * DEV:  Sends to /__br_logger endpoint (Vite middleware → browser.log)
 * PROD: When activated via ?br_debug=1, broadcasts via Supabase Realtime
 *       to the dev machine's Vite plugin listener (→ browser.log)
 *
 * Key design decisions:
 *   - ALL interception (console, fetch, errors) at MODULE LOAD TIME
 *   - Realtime channel + client stored at module scope (survives GC + React lifecycle)
 *   - localStorage for flag persistence (survives clear-site-data + redirects)
 *   - beforeunload + visibilitychange ensures logs flush during navigation
 *   - Prod debug: every log flushed immediately (no batching delay)
 *   - Activate: add ?br_debug=1 to any prod URL (auto-expires 4 hours)
 *   - Deactivate: add ?br_debug=0 to any prod URL
 *
 * SETUP REQUIREMENTS:
 *   1. This file MUST be the FIRST import in src/main.tsx (module-scope interception)
 *   2. <BRLogger /> MUST be rendered in the React tree (for init message + dev flush)
 *   3. vite-br-logger-plugin.ts MUST be registered in vite.config.ts (receives logs)
 *   4. .env MUST have VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
 *
 * READONLY — DO NOT MODIFY unless explicitly fixing logging infrastructure.
 */

import { useEffect } from 'react';
import { createClient, type RealtimeChannel } from '@supabase/supabase-js';

interface LogEntry {
  timestamp: string;
  sessionId: string;
  type: 'console' | 'network' | 'error';
  level?: string;
  method?: string;
  url?: string;
  status?: number;
  duration?: number;
  message?: string;
  stack?: string;
}

const SESSION_ID = Math.random().toString(36).substring(2, 15);
const FLUSH_INTERVAL_DEV = 2000;
const MAX_BATCH_SIZE = 50;
const BR_DEBUG_KEY = 'br_debug';
const BR_DEBUG_EXPIRY_KEY = 'br_debug_expiry';
const BR_DEBUG_DURATION_MS = 4 * 60 * 60 * 1000; // 4 hours

// === MODULE-LEVEL SETUP (runs at import time, before React) ===

function checkBrDebug(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const params = new URLSearchParams(window.location.search);
    // Explicit deactivation
    if (params.get(BR_DEBUG_KEY) === '0') {
      localStorage.removeItem(BR_DEBUG_KEY);
      localStorage.removeItem(BR_DEBUG_EXPIRY_KEY);
      return false;
    }
    // Activation via URL param
    if (params.get(BR_DEBUG_KEY) === '1') {
      localStorage.setItem(BR_DEBUG_KEY, '1');
      localStorage.setItem(BR_DEBUG_EXPIRY_KEY, String(Date.now() + BR_DEBUG_DURATION_MS));
      return true;
    }
    // Check existing localStorage flag
    if (localStorage.getItem(BR_DEBUG_KEY) === '1') {
      const expiry = Number(localStorage.getItem(BR_DEBUG_EXPIRY_KEY) || '0');
      if (Date.now() < expiry) return true;
      localStorage.removeItem(BR_DEBUG_KEY);
      localStorage.removeItem(BR_DEBUG_EXPIRY_KEY);
    }
  } catch {
    /* localStorage blocked */
  }
  return false;
}

const IS_PROD = typeof import.meta !== 'undefined' && import.meta.env?.PROD === true;
const BR_DEBUG_ACTIVE = checkBrDebug();
const LOGGING_ENABLED = !IS_PROD || BR_DEBUG_ACTIVE;

// Module-level log buffer
const logBuffer: LogEntry[] = [];

// Realtime channel + client (module scope — survives React lifecycle AND GC)
let prodClient: ReturnType<typeof createClient> | null = null;
let prodChannel: RealtimeChannel | null = null;
let prodChannelReady = false;
const pendingBroadcasts: string[] = [];

if (IS_PROD && BR_DEBUG_ACTIVE && typeof window !== 'undefined') {
  try {
    const url = import.meta.env.VITE_SUPABASE_URL;
    const key = import.meta.env.VITE_SUPABASE_ANON_KEY;
    if (url && key) {
      prodClient = createClient(url, key, {
        auth: { autoRefreshToken: false, persistSession: false, storageKey: 'br-logger-auth' },
      });
      prodChannel = prodClient.channel('br-logs');
      prodChannel.subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          prodChannelReady = true;
          for (const lines of pendingBroadcasts) {
            prodChannel!.send({ type: 'broadcast', event: 'br_log', payload: { lines } });
          }
          pendingBroadcasts.length = 0;
        }
      });

      // Auth monitoring — separate client shares the app's session storage
      const authMonitor = createClient(url, key, {
        auth: { autoRefreshToken: false, persistSession: true },
      });
      authMonitor.auth.onAuthStateChange((event, session) => {
        addLog({
          type: 'console',
          level: 'info',
          message: `[AUTH] ${event} user=${session?.user?.id ?? 'none'}${session?.user?.email ? ` (${session.user.email})` : ''}`,
        });
      });
    }
  } catch {
    /* Supabase client creation failed */
  }
}

function sendLines(lines: string) {
  if (!IS_PROD) {
    fetch('/__br_logger', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: lines,
    }).catch(() => {});
  } else if (prodChannel) {
    if (prodChannelReady) {
      prodChannel.send({ type: 'broadcast', event: 'br_log', payload: { lines } });
    } else {
      pendingBroadcasts.push(lines);
    }
  }
}

function formatLog(log: LogEntry): string {
  const prefix = `[${log.timestamp}] [${log.sessionId.slice(0, 8)}]`;
  if (log.type === 'console') {
    return `${prefix} [${(log.level || 'log').toUpperCase()}] ${log.message || ''}\n`;
  }
  if (log.type === 'network') {
    const status = log.status ? ` ${log.status}` : ' ERR';
    const duration = log.duration ? ` ${log.duration}ms` : '';
    return `${prefix} [NET] ${log.method} ${log.url}${status}${duration}\n`;
  }
  if (log.type === 'error') {
    return `${prefix} [ERROR] ${log.message || 'Unknown'}\n${log.stack ? `  ${log.stack}\n` : ''}`;
  }
  return `${prefix} ${JSON.stringify(log)}\n`;
}

function formatLogs(logs: LogEntry[]): string {
  return logs.map(formatLog).join('');
}

function addLog(entry: Omit<LogEntry, 'timestamp' | 'sessionId'>) {
  const log: LogEntry = {
    ...entry,
    timestamp: new Date().toISOString(),
    sessionId: SESSION_ID,
  };
  logBuffer.push(log);
  // Prod debug: flush every log immediately (survive redirects)
  if ((IS_PROD && BR_DEBUG_ACTIVE) || logBuffer.length >= MAX_BATCH_SIZE) {
    flush();
  }
}

function flush() {
  if (logBuffer.length === 0) return;
  const logs = [...logBuffer];
  logBuffer.length = 0;
  sendLines(formatLogs(logs));
}

// === MODULE-LEVEL INTERCEPTION (before any other module captures references) ===

if (LOGGING_ENABLED && typeof window !== 'undefined') {
  // Console interception
  const origConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
    info: console.info,
    debug: console.debug,
  };

  const wrapConsole =
    (level: string, orig: (...args: unknown[]) => void) =>
    (...args: unknown[]) => {
      orig.apply(console, args);
      addLog({
        type: 'console',
        level,
        message: args.map((a) => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' '),
      });
    };

  console.log = wrapConsole('log', origConsole.log);
  console.warn = wrapConsole('warn', origConsole.warn);
  console.error = wrapConsole('error', origConsole.error);
  console.info = wrapConsole('info', origConsole.info);
  console.debug = wrapConsole('debug', origConsole.debug);

  // Fetch interception
  const origFetch = window.fetch.bind(window);
  const fetchWrapper = async (...args: Parameters<typeof fetch>) => {
    const start = Date.now();
    const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request)?.url || 'unknown';
    const method = ((args[1] as RequestInit)?.method || 'GET').toUpperCase();

    if (
      url.includes('__br_logger') ||
      url.includes('__supabase_log') ||
      url.includes('/realtime/')
    ) {
      return origFetch(...args);
    }

    try {
      const res = await origFetch(...args);
      addLog({ type: 'network', method, url, status: res.status, duration: Date.now() - start });
      return res;
    } catch (e) {
      addLog({
        type: 'network',
        method,
        url,
        status: 0,
        duration: Date.now() - start,
        message: e instanceof Error ? e.message : 'Error',
      });
      throw e;
    }
  };
  window.fetch = fetchWrapper;
  // Ensure globalThis/self also point to wrapper (Supabase SDK reads globalThis.fetch)
  if (typeof globalThis !== 'undefined') globalThis.fetch = fetchWrapper;
  if (typeof self !== 'undefined') (self as any).fetch = fetchWrapper;

  // Error handlers
  window.addEventListener('error', (e: ErrorEvent) => {
    addLog({ type: 'error', message: e.message, stack: e.error?.stack });
  });

  window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
    addLog({
      type: 'error',
      message: `Unhandled: ${e.reason?.message || e.reason}`,
      stack: e.reason?.stack,
    });
  });

  // Flush handlers for navigation
  window.addEventListener('beforeunload', () => {
    flush();
    if (!IS_PROD) {
      navigator.sendBeacon('/__br_logger', formatLogs(logBuffer));
    }
  });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
}

// === REACT COMPONENT (init message + dev flush timer) ===

export function BRLogger() {
  useEffect(() => {
    if (!LOGGING_ENABLED) return;

    // Dev: batch flush on interval (prod flushes immediately in addLog)
    let timer: ReturnType<typeof setInterval> | null = null;
    if (!IS_PROD) {
      timer = setInterval(flush, FLUSH_INTERVAL_DEV);
    }

    addLog({
      type: 'console',
      level: 'info',
      message: `[BR3] Session: ${SESSION_ID} at ${window.location.href}${IS_PROD ? ' [PROD DEBUG]' : ''}`,
    });

    return () => {
      if (timer) clearInterval(timer);
      flush();
    };
  }, []);

  return null;
}

export default BRLogger;
