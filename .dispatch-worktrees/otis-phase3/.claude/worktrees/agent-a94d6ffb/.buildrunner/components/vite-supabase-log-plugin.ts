/**
 * BR3 Supabase Log Plugin - Vite Dev Server
 * Receives Supabase operation logs from the client-side supabaseLogger
 * and writes them to .buildrunner/supabase.log with auto-rotation.
 *
 * DEV-ONLY: configureServer() is a Vite dev-server hook — never
 * called during `vite build`, so zero production impact.
 *
 * READONLY — DO NOT MODIFY. Part of BR3 infrastructure.
 */

import type { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';

const LOG_MAX_BYTES = 500 * 1024;   // 500 KB
const LOG_KEEP_BYTES = 250 * 1024;  // keep last ~250 KB after rotation

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

export function supabaseLogPlugin(): Plugin {
  const projectRoot = process.cwd();
  const logDir = path.join(projectRoot, '.buildrunner');
  const logFile = path.join(logDir, 'supabase.log');

  return {
    name: 'supabase-log',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.method === 'POST' && req.url === '/__supabase_log') {
          let body = '';
          req.on('data', (chunk: Buffer) => { body += chunk.toString(); });
          req.on('end', () => {
            try {
              if (!fs.existsSync(logDir)) {
                fs.mkdirSync(logDir, { recursive: true });
              }
              rotateLogIfNeeded(logFile);
              fs.appendFileSync(logFile, body + '\n');
              res.statusCode = 204;
              res.end();
            } catch {
              res.statusCode = 500;
              res.end();
            }
          });
          return;
        }
        next();
      });
    },
  };
}

export default supabaseLogPlugin;
