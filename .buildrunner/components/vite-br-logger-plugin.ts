/**
 * BR3 Browser Logger - Vite Plugin
 *
 * Two log sources:
 *   1. LOCAL:  POST /__br_logger from the dev browser (same as before)
 *   2. PROD:   Supabase Realtime broadcast on channel "br-logs"
 *              (activated on prod via ?br_debug=1)
 *
 * Both write to .buildrunner/browser.log with auto-rotation.
 *
 * READONLY — DO NOT MODIFY unless explicitly fixing logging infrastructure.
 */

import type { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';
import { config as loadDotenv } from 'dotenv';

const MAX_LOG_SIZE = 500 * 1024; // 500KB before rotation
const KEEP_BYTES = 250 * 1024; // keep last ~250KB after rotation

function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function rotateIfNeeded(logFile: string) {
  try {
    const stat = fs.statSync(logFile);
    if (stat.size > MAX_LOG_SIZE) {
      const content = fs.readFileSync(logFile, 'utf-8');
      const cutIndex = content.indexOf('\n', content.length - KEEP_BYTES);
      if (cutIndex !== -1) {
        fs.writeFileSync(logFile, content.slice(cutIndex + 1));
      }
    }
  } catch {
    // File doesn't exist yet
  }
}

function appendLog(logFile: string, data: string) {
  rotateIfNeeded(logFile);
  fs.appendFileSync(logFile, data);
}

export function brLoggerPlugin(): Plugin {
  const projectRoot = process.cwd();
  const logDir = path.join(projectRoot, '.buildrunner');
  const logFile = path.join(logDir, 'browser.log');

  ensureDir(logDir);

  return {
    name: 'br-logger',
    configureServer(server) {
      // --- Source 1: Local dev browser POST /__br_logger ---
      server.middlewares.use('/__br_logger', (req, res) => {
        if (req.method === 'POST') {
          let body = '';
          req.on('data', (chunk: Buffer) => {
            body += chunk.toString();
          });
          req.on('end', () => {
            try {
              appendLog(logFile, body);
              res.statusCode = 200;
              res.end('ok');
            } catch (e) {
              console.error('[br-logger] Write error:', e);
              res.statusCode = 500;
              res.end('error');
            }
          });
        } else {
          res.statusCode = 405;
          res.end('Method not allowed');
        }
      });

      // --- Source 2: Prod Realtime broadcast on "br-logs" channel ---
      // Vite plugins run before dotenv — load .env manually
      loadDotenv({ path: path.join(projectRoot, '.env') });
      const supabaseUrl = process.env.VITE_SUPABASE_URL;
      const supabaseKey =
        process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.VITE_SUPABASE_ANON_KEY;

      if (supabaseUrl && supabaseKey) {
        // Dynamic import to avoid requiring @supabase/supabase-js at plugin load time
        import('@supabase/supabase-js')
          .then(({ createClient }) => {
            const client = createClient(supabaseUrl, supabaseKey, {
              auth: { autoRefreshToken: false, persistSession: false },
            });

            let channel = client.channel('br-logs');
            let isSubscribed = false;

            function onBroadcast(payload: { payload?: { lines?: string } }) {
              const lines = payload?.payload?.lines;
              if (typeof lines === 'string' && lines.length > 0) {
                try {
                  appendLog(logFile, lines);
                } catch (e) {
                  console.error('[br-logger] Realtime write error:', e);
                }
              }
            }

            function subscribe() {
              channel.on('broadcast', { event: 'br_log' }, onBroadcast).subscribe((status) => {
                if (status === 'SUBSCRIBED') {
                  isSubscribed = true;
                  console.log('[br-logger] 📡 Listening for prod logs (2h window, auto-reconnect)');
                } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
                  isSubscribed = false;
                  console.log('[br-logger] ⚠️ Channel disconnected, will reconnect...');
                }
              });
            }

            subscribe();

            // Health check every 60s — reconnect if channel dropped
            setInterval(() => {
              if (!isSubscribed) {
                console.log('[br-logger] 🔄 Reconnecting Realtime channel...');
                try {
                  client.removeChannel(channel);
                } catch {}
                channel = client.channel('br-logs');
                subscribe();
              }
            }, 60_000);
          })
          .catch(() => {
            // @supabase/supabase-js not installed — skip Realtime listener
          });
      }
    },
  };
}

export default brLoggerPlugin;
