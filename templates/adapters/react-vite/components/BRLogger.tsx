import { useEffect } from 'react';

import { enqueueLog, flushLogs } from './brLoggerTransport';

type ConsoleLevel = 'log' | 'warn' | 'error';

function serializeArg(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function BRLogger(): null {
  useEffect(() => {
    const originalConsole = {
      log: console.log,
      warn: console.warn,
      error: console.error,
    };

    const intercept =
      (level: ConsoleLevel, original: (...args: unknown[]) => void) =>
      (...args: unknown[]) => {
        original(...args);
        enqueueLog({
          level,
          message: args.map(serializeArg).join(' '),
          source: 'browser',
        });
      };

    console.log = intercept('log', originalConsole.log);
    console.warn = intercept('warn', originalConsole.warn);
    console.error = intercept('error', originalConsole.error);

    const onError = (event: ErrorEvent) => {
      enqueueLog({
        level: 'error',
        message: event.message,
        source: 'window',
        stack: event.error instanceof Error ? event.error.stack : undefined,
      });
    };
    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      enqueueLog({
        level: 'error',
        message: `Unhandled rejection: ${serializeArg(event.reason)}`,
        source: 'promise',
      });
    };

    const flushTimer = window.setInterval(() => {
      void flushLogs();
    }, 1500);

    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onUnhandledRejection);
    window.addEventListener('beforeunload', flushLogs);

    return () => {
      console.log = originalConsole.log;
      console.warn = originalConsole.warn;
      console.error = originalConsole.error;
      window.clearInterval(flushTimer);
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onUnhandledRejection);
      window.removeEventListener('beforeunload', flushLogs);
      void flushLogs();
    };
  }, []);

  return null;
}

export default BRLogger;
