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
 * LIVE ERROR DETECTION + AUTO-FIX:
 *   Every incoming log line is checked for fixable error patterns.
 *   Fixes fire immediately — no polling, no cron, no delay.
 *   macOS notification on any critical/high error.
 *   Alert pushed to Walter for developer brief.
 */

import type { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';
import { execFile, exec } from 'child_process';
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

// --- Live Error Detection + Auto-Fix ---

const CLUSTER_CHECK = path.join(process.env.HOME || '', '.buildrunner/scripts/cluster-check.sh');
const ALERT_FILE = path.join(process.env.HOME || '', '.buildrunner/pending-alerts.jsonl');
const _fixedFingerprints = new Set<string>();
const _failedFixFingerprints = new Set<string>(); // tracks errors where redeploy didn't help

function fingerprint(s: string): string {
  // Simple hash to deduplicate — same error doesn't trigger twice
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return h.toString(36);
}

function escalateToClaude(error: string, context: string) {
  const alert = JSON.stringify({
    timestamp: new Date().toISOString(),
    error,
    context,
    project: path.basename(process.cwd()),
  });
  try {
    fs.appendFileSync(ALERT_FILE, alert + '\n');
    console.log(`\x1b[35m[br-autofix]\x1b[0m Escalated to Claude session`);
  } catch {}
}

function notify(title: string, msg: string) {
  const escaped = msg.replace(/"/g, '\\"').slice(0, 120);
  exec(`osascript -e 'display notification "${escaped}" with title "${title}" sound name "Basso"'`);
}

function pushToWalter(pattern: { pattern_type: string; severity: string; description: string; count?: number }) {
  exec(`${CLUSTER_CHECK} test-runner`, (_err, walterUrl) => {
    const url = walterUrl?.trim();
    if (!url) return;
    const data = JSON.stringify(pattern);
    exec(`curl -s --max-time 3 -X POST "${url}/api/alert" -H "Content-Type: application/json" -d '${data.replace(/'/g, "'\\''")}'`);
  });
}

function autoFixEdgeFunctionDeploy(fnName: string, reason: string) {
  const projectRoot = process.cwd();
  const fnDir = path.join(projectRoot, 'supabase', 'functions', fnName);
  if (!fs.existsSync(fnDir)) return;

  console.log(`\x1b[33m[br-autofix]\x1b[0m Deploying edge function '${fnName}' — ${reason}`);
  notify('BR3 Auto-Fix', `Deploying ${fnName}: ${reason}`);

  execFile('supabase', ['functions', 'deploy', fnName, '--no-verify-jwt'], { cwd: projectRoot, timeout: 120000 }, (err, stdout, stderr) => {
    if (err) {
      console.error(`\x1b[31m[br-autofix]\x1b[0m Deploy failed: ${stderr?.slice(0, 200)}`);
      notify('BR3 Auto-Fix FAILED', `${fnName} deploy failed`);
      pushToWalter({ pattern_type: 'auto_fix_failed', severity: 'critical', description: `Auto-deploy of ${fnName} failed: ${stderr?.slice(0, 100)}` });
    } else {
      console.log(`\x1b[32m[br-autofix]\x1b[0m ✓ Deployed ${fnName}`);
      notify('BR3 Auto-Fix', `✓ Deployed ${fnName}`);
      pushToWalter({ pattern_type: 'auto_fix_applied', severity: 'info', description: `Auto-deployed ${fnName}: ${reason}` });
    }
  });
}

function checkForFixableErrors(body: string) {
  const lines = body.split('\n').filter(Boolean);
  for (const line of lines) {
    const fp = fingerprint(line);
    if (_fixedFingerprints.has(fp)) continue;

    // --- Pattern 1: Edge function "Unknown action" → auto-deploy ---
    const unknownAction = line.match(/Unknown action:\s*(\w+).*?Valid actions:/);
    const fnUrlMatch = line.match(/\/functions\/v1\/([\w-]+)/);
    if (unknownAction && fnUrlMatch) {
      const action = unknownAction[1];
      const fn = fnUrlMatch[1];
      const indexPath = path.join(process.cwd(), 'supabase', 'functions', fn, 'index.ts');
      if (fs.existsSync(indexPath)) {
        const code = fs.readFileSync(indexPath, 'utf-8');
        if (code.includes(`'${action}'`) || code.includes(`"${action}"`)) {
          _fixedFingerprints.add(fp);
          autoFixEdgeFunctionDeploy(fn, `missing action '${action}' exists in local code`);
          continue;
        }
      }
    }

    // --- Pattern 2: Edge function timeout (ERR with high duration) ---
    const timeoutMatch = line.match(/\[NET\]\s+\w+\s+(https?:\/\/\S*\/functions\/v1\/([\w-]+))\s+ERR\s+(\d+)ms/);
    if (timeoutMatch) {
      const fn = timeoutMatch[2];
      const duration = parseInt(timeoutMatch[3]);
      if (duration > 30000) {
        pushToWalter({ pattern_type: 'edge_function_timeout', severity: 'critical', description: `${fn} timed out after ${Math.round(duration / 1000)}s` });
        notify('BR3: Edge Function Timeout', `${fn} timed out after ${Math.round(duration / 1000)}s`);

        if (_fixedFingerprints.has(fp) || _failedFixFingerprints.has(fn)) {
          // Redeploy already tried — escalate to Claude session
          _failedFixFingerprints.add(fn);
          escalateToClaude(
            `Edge function '${fn}' timed out after ${Math.round(duration / 1000)}s. Redeploy did not fix it. The handler is too slow — likely the Claude API call inside the handler exceeds Supabase's 150s limit. Fix the handler code.`,
            `Function: supabase/functions/${fn}/\nError: timeout after ${Math.round(duration / 1000)}s\nPrevious fix attempt: redeploy (failed)\nNeeded: reduce prompt size, lower effort level, or split into smaller calls`,
          );
        } else {
          // First attempt — try redeploy
          _fixedFingerprints.add(fp);
          autoFixEdgeFunctionDeploy(fn, `timeout after ${Math.round(duration / 1000)}s — clearing stale worker`);
        }
        continue;
      }
    }

    // --- Pattern 3: Edge function HTTP error (400, 500, etc.) → alert + attempt fix ---
    const httpErrMatch = line.match(/\[NET\]\s+\w+\s+(https?:\/\/\S*\/functions\/v1\/([\w-]+))\s+(\d{3})\s+\d+ms/);
    if (httpErrMatch) {
      const fn = httpErrMatch[2];
      const status = parseInt(httpErrMatch[3]);
      if (status >= 400) {
        _fixedFingerprints.add(fp);
        pushToWalter({ pattern_type: 'edge_function_error', severity: status >= 500 ? 'critical' : 'high', description: `${fn} returned ${status}` });
        notify('BR3: Edge Function Error', `${fn} returned ${status}`);
        continue;
      }
    }

    // --- Pattern 4: REST API error (PATCH/POST to /rest/v1/ returning 400+) → likely missing migration ---
    const restErrMatch = line.match(/\[NET\]\s+(PATCH|POST|PUT)\s+(https?:\/\/\S*\/rest\/v1\/([\w-]+)\S*)\s+(\d{3})\s+\d+ms/);
    if (restErrMatch) {
      const method = restErrMatch[1];
      const table = restErrMatch[3];
      const status = parseInt(restErrMatch[4]);
      if (status >= 400) {
        pushToWalter({ pattern_type: 'rest_api_error', severity: 'high', description: `${method} ${table} returned ${status} — possible missing migration or schema mismatch` });
        notify('BR3: Database Error', `${method} ${table} → ${status}`);

        // Check for unpushed migrations
        const migrationsDir = path.join(process.cwd(), 'supabase', 'migrations');
        if (fs.existsSync(migrationsDir)) {
          escalateToClaude(
            `REST API error: ${method} /rest/v1/${table} returned ${status}. This likely means a migration hasn't been pushed — a column or table is missing in prod.`,
            `Table: ${table}\nStatus: ${status}\nFix: run 'supabase db push' to apply pending migrations, then retry.`,
          );
          // Also try to auto-fix by pushing migrations
          console.log(`\x1b[33m[br-autofix]\x1b[0m ${method} ${table} returned ${status} — pushing pending migrations...`);
          execFile('supabase', ['db', 'push', '--include-all'], { cwd: process.cwd(), timeout: 60000 }, (err, stdout, stderr) => {
            if (err) {
              console.error(`\x1b[31m[br-autofix]\x1b[0m db push failed: ${stderr?.slice(0, 200)}`);
            } else {
              console.log(`\x1b[32m[br-autofix]\x1b[0m ✓ Migrations pushed`);
              notify('BR3 Auto-Fix', `✓ Pushed migrations for ${table}`);
              pushToWalter({ pattern_type: 'auto_fix_applied', severity: 'info', description: `Auto-pushed migrations after ${method} ${table} ${status}` });
            }
          });
        }
        _fixedFingerprints.add(fp);
        continue;
      }
    }

    // --- Pattern 5: Any [ERROR] line → alert Walter + escalate on repeat ---
    if (line.includes('[ERROR]') && !line.includes('[vite]')) {
      const msg = line.replace(/^\[.*?\]\s*\[\w+\]\s*/, '').slice(0, 120);
      pushToWalter({ pattern_type: 'runtime_error', severity: 'high', description: msg });
      notify('BR3: Runtime Error', msg);

      if (_fixedFingerprints.has(fp)) {
        // Same error again — escalate to Claude
        escalateToClaude(
          `Recurring runtime error: ${msg}`,
          `This error has occurred multiple times. Auto-fix did not resolve it. Investigate and fix the root cause.`,
        );
      }
      _fixedFingerprints.add(fp);
    }
  }
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
              // Live error detection — fires instantly, no polling
              checkForFixableErrors(body);
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
                  // Live error detection — works for prod logs too
                  checkForFixableErrors(lines);
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
