'use client';

import { useEffect } from 'react';

function send(level: 'log' | 'warn' | 'error', args: unknown[]): void {
  void fetch('/api/br-log', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      logs: [
        {
          ts: new Date().toISOString(),
          level,
          message: args.map((value) => String(value)).join(' '),
          source: 'next-client',
        },
      ],
    }),
    keepalive: true,
  }).catch(() => {});
}

export function BRLoggerNext(): null {
  useEffect(() => {
    const original = {
      log: console.log,
      warn: console.warn,
      error: console.error,
    };

    console.log = (...args: unknown[]) => {
      original.log(...args);
      send('log', args);
    };
    console.warn = (...args: unknown[]) => {
      original.warn(...args);
      send('warn', args);
    };
    console.error = (...args: unknown[]) => {
      original.error(...args);
      send('error', args);
    };

    return () => {
      console.log = original.log;
      console.warn = original.warn;
      console.error = original.error;
    };
  }, []);

  return null;
}

export default BRLoggerNext;
