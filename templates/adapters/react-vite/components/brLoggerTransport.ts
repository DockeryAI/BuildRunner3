import { postLogBatch } from './supabaseLogger';

export interface BrowserLogEntry {
  level: 'log' | 'warn' | 'error';
  message: string;
  source: string;
  stack?: string;
  ts?: string;
}

const queue: BrowserLogEntry[] = [];

export function enqueueLog(entry: BrowserLogEntry): void {
  queue.push({
    ...entry,
    ts: entry.ts ?? new Date().toISOString(),
  });
}

export async function flushLogs(): Promise<void> {
  if (queue.length === 0) {
    return;
  }

  const batch = queue.splice(0, queue.length);
  try {
    await postLogBatch({ logs: batch });
  } catch {
    queue.unshift(...batch);
  }
}
