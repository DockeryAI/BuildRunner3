import { useEffect } from 'react';
import { Platform } from 'react-native';

function post(level: 'log' | 'warn' | 'error', args: unknown[]): void {
  void fetch('http://127.0.0.1:5710/api/br-log', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      logs: [
        {
          ts: new Date().toISOString(),
          level,
          platform: Platform.OS,
          message: args.map((value) => String(value)).join(' '),
          source: 'expo-native',
        },
      ],
    }),
  }).catch(() => {});
}

export function BRLoggerNative(): null {
  useEffect(() => {
    const original = {
      log: console.log,
      warn: console.warn,
      error: console.error,
    };

    console.log = (...args: unknown[]) => {
      original.log(...args);
      post('log', args);
    };
    console.warn = (...args: unknown[]) => {
      original.warn(...args);
      post('warn', args);
    };
    console.error = (...args: unknown[]) => {
      original.error(...args);
      post('error', args);
    };

    return () => {
      console.log = original.log;
      console.warn = original.warn;
      console.error = original.error;
    };
  }, []);

  return null;
}

export default BRLoggerNative;
