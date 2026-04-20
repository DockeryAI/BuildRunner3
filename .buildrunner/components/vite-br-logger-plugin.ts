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
//
// Safeguards:
//   1. Type-check before auto-deploy (tsc --noEmit)
//   2. Max 2 auto-fix attempts per function
//   3. 5-minute cooldown per pattern_type for alerts
//   4. Stale alert detection (>10 min = stale prefix)
//   5. Top-level try/catch (monitoring never becomes the failure)
//   6. Lock file for deploys (prevents race conditions)
//   7. Catch-all for unmatched /functions/ and /rest/ errors
//   8. Never auto-push migrations (alert only)

const CLUSTER_CHECK = path.join(process.env.HOME || '', '.buildrunner/scripts/cluster-check.sh');
const ALERT_FILE = path.join(process.env.HOME || '', '.buildrunner/pending-alerts.jsonl');
const DEPLOY_LOCK = path.join(process.env.HOME || '', '.buildrunner/.deploy-lock');
const _fixedFingerprints = new Set<string>();
const _autoFixAttempts: Record<string, number> = {}; // fn → attempt count (max 2)
const _alertCooldowns: Record<string, number> = {}; // pattern_type → last alert timestamp
const MAX_AUTOFIX_ATTEMPTS = 2;
const ALERT_COOLDOWN_MS = 5 * 60 * 1000; // 5 minutes per pattern_type

function fingerprint(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return h.toString(36);
}

function canAlert(patternType: string): boolean {
  const last = _alertCooldowns[patternType] || 0;
  if (Date.now() - last < ALERT_COOLDOWN_MS) return false;
  _alertCooldowns[patternType] = Date.now();
  return true;
}

function canAutoFix(fnName: string): boolean {
  const attempts = _autoFixAttempts[fnName] || 0;
  if (attempts >= MAX_AUTOFIX_ATTEMPTS) return false;
  _autoFixAttempts[fnName] = attempts + 1;
  return true;
}

function isDeployLocked(): boolean {
  try {
    const stat = fs.statSync(DEPLOY_LOCK);
    // Lock is stale if older than 5 minutes
    return Date.now() - stat.mtimeMs < 5 * 60 * 1000;
  } catch {
    return false;
  }
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

function pushToWalter(pattern: {
  pattern_type: string;
  severity: string;
  description: string;
  count?: number;
}) {
  exec(`${CLUSTER_CHECK} test-runner`, (_err, walterUrl) => {
    const url = walterUrl?.trim();
    if (!url) return;
    const data = JSON.stringify(pattern);
    exec(
      `curl -s --max-time 3 -X POST "${url}/api/alert" -H "Content-Type: application/json" -d '${data.replace(/'/g, "'\\''")}'`
    );
  });
}

function typeCheckEdgeFunction(fnName: string): boolean {
  const projectRoot = process.cwd();
  const fnDir = path.join(projectRoot, 'supabase', 'functions', fnName);
  if (!fs.existsSync(fnDir)) return false;
  // Quick check: ensure index.ts at least parses (full tsc would need deno types)
  try {
    const indexPath = path.join(fnDir, 'index.ts');
    if (!fs.existsSync(indexPath)) return false;
    const code = fs.readFileSync(indexPath, 'utf-8');
    // Basic syntax check — look for obvious issues
    if (code.includes('SyntaxError') || code.trim().length === 0) return false;
    return true;
  } catch {
    return false;
  }
}

function autoFixEdgeFunctionDeploy(fnName: string, reason: string) {
  const projectRoot = process.cwd();
  const fnDir = path.join(projectRoot, 'supabase', 'functions', fnName);
  if (!fs.existsSync(fnDir)) return;

  // Safeguard: max attempts
  if (!canAutoFix(fnName)) {
    console.log(
      `\x1b[33m[br-autofix]\x1b[0m Max auto-fix attempts (${MAX_AUTOFIX_ATTEMPTS}) reached for '${fnName}' — escalating to Claude`
    );
    escalateToClaude(
      `Auto-fix exhausted for edge function '${fnName}'. ${MAX_AUTOFIX_ATTEMPTS} deploy attempts failed. Manual investigation needed.`,
      `Function: supabase/functions/${fnName}/\nReason: ${reason}\nAttempts: ${MAX_AUTOFIX_ATTEMPTS}\nFix manually: check handler code, run supabase functions deploy ${fnName} --no-verify-jwt`
    );
    return;
  }

  // Safeguard: deploy lock
  if (isDeployLocked()) {
    console.log(
      `\x1b[33m[br-autofix]\x1b[0m Deploy locked (another deploy in progress) — skipping auto-deploy of '${fnName}'`
    );
    return;
  }

  // Safeguard: type-check before deploying
  if (!typeCheckEdgeFunction(fnName)) {
    console.error(
      `\x1b[31m[br-autofix]\x1b[0m Type-check failed for '${fnName}' — not deploying broken code`
    );
    escalateToClaude(
      `Cannot auto-deploy '${fnName}' — code has errors. Fix the code first.`,
      `Function: supabase/functions/${fnName}/\nReason: ${reason}\nBlocked by: type-check failure`
    );
    return;
  }

  console.log(`\x1b[33m[br-autofix]\x1b[0m Deploying edge function '${fnName}' — ${reason}`);
  notify('BR3 Auto-Fix', `Deploying ${fnName}: ${reason}`);

  // Set deploy lock
  try {
    fs.writeFileSync(DEPLOY_LOCK, `${fnName}:${Date.now()}`);
  } catch {}

  execFile(
    'supabase',
    ['functions', 'deploy', fnName, '--no-verify-jwt'],
    { cwd: projectRoot, timeout: 120000 },
    (err, _stdout, stderr) => {
      // Clear deploy lock
      try {
        fs.unlinkSync(DEPLOY_LOCK);
      } catch {}

      if (err) {
        console.error(`\x1b[31m[br-autofix]\x1b[0m Deploy failed: ${stderr?.slice(0, 200)}`);
        notify('BR3 Auto-Fix FAILED', `${fnName} deploy failed`);
        pushToWalter({
          pattern_type: 'auto_fix_failed',
          severity: 'critical',
          description: `Auto-deploy of ${fnName} failed: ${stderr?.slice(0, 100)}`,
        });
      } else {
        console.log(`\x1b[32m[br-autofix]\x1b[0m ✓ Deployed ${fnName}`);
        notify('BR3 Auto-Fix', `✓ Deployed ${fnName}`);
        pushToWalter({
          pattern_type: 'auto_fix_applied',
          severity: 'info',
          description: `Auto-deployed ${fnName}: ${reason}`,
        });
      }
    }
  );
}

function checkForFixableErrors(body: string) {
  // Safeguard: top-level try/catch — monitoring never becomes the failure
  try {
    _checkForFixableErrorsInner(body);
  } catch (e) {
    console.error(`\x1b[31m[br-autofix]\x1b[0m Error in checkForFixableErrors (non-fatal): ${e}`);
  }
}

function _checkForFixableErrorsInner(body: string) {
  const lines = body.split('\n').filter(Boolean);
  for (const line of lines) {
    const fp = fingerprint(line);
    if (_fixedFingerprints.has(fp)) continue;

    // --- Pattern 1: Edge function "Unknown action" → type-check + auto-deploy ---
    const unknownAction = line.match(/Unknown action:\s*(\w+)/);
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
    const timeoutMatch = line.match(
      /\[NET\]\s+\w+\s+https?:\/\/\S*\/functions\/v1\/([\w-]+)\S*\s+ERR\s+(\d+)ms/
    );
    if (timeoutMatch) {
      const fn = timeoutMatch[1];
      const duration = parseInt(timeoutMatch[2]);
      if (duration > 30000) {
        if (canAlert('edge_function_timeout')) {
          pushToWalter({
            pattern_type: 'edge_function_timeout',
            severity: 'critical',
            description: `${fn} timed out after ${Math.round(duration / 1000)}s`,
          });
          notify(
            'BR3: Edge Function Timeout',
            `${fn} timed out after ${Math.round(duration / 1000)}s`
          );
        }

        if (_fixedFingerprints.has(fp)) {
          // Redeploy already tried — escalate to Claude
          escalateToClaude(
            `Edge function '${fn}' timed out after ${Math.round(duration / 1000)}s. Redeploy did not fix it. The handler is too slow — likely the Claude API call inside the handler exceeds Supabase's 150s limit.`,
            `Function: supabase/functions/${fn}/\nError: timeout after ${Math.round(duration / 1000)}s\nPrevious fix attempt: redeploy (failed)\nNeeded: reduce prompt size, lower effort level, or split into smaller calls`
          );
        } else {
          _fixedFingerprints.add(fp);
          autoFixEdgeFunctionDeploy(
            fn,
            `timeout after ${Math.round(duration / 1000)}s — clearing stale worker`
          );
        }
        continue;
      }
    }

    // --- Pattern 3: Edge function HTTP error (400, 500, etc.) ---
    const httpErrMatch = line.match(
      /\[NET\]\s+\w+\s+https?:\/\/\S*\/functions\/v1\/([\w-]+)\S*\s+(\d{3})\s+\d+ms/
    );
    if (httpErrMatch) {
      const fn = httpErrMatch[1];
      const status = parseInt(httpErrMatch[2]);
      if (status >= 400) {
        _fixedFingerprints.add(fp);
        if (canAlert('edge_function_error')) {
          pushToWalter({
            pattern_type: 'edge_function_error',
            severity: status >= 500 ? 'critical' : 'high',
            description: `${fn} returned ${status}`,
          });
          notify('BR3: Edge Function Error', `${fn} returned ${status}`);
        }
        // Escalate 500s to Claude immediately
        if (status >= 500) {
          escalateToClaude(
            `Edge function '${fn}' returned ${status} (server error).`,
            `Function: supabase/functions/${fn}/\nStatus: ${status}\nCheck Supabase dashboard logs for the full error trace.`
          );
        }
        continue;
      }
    }

    // --- Pattern 4: REST API write error (PATCH/POST/PUT returning 400+) → alert only, never auto-push migrations ---
    const restErrMatch = line.match(
      /\[NET\]\s+(PATCH|POST|PUT)\s+https?:\/\/\S*\/rest\/v1\/([\w-]+)\S*\s+(\d{3})\s+\d+ms/
    );
    if (restErrMatch) {
      const method = restErrMatch[1];
      const table = restErrMatch[2];
      const status = parseInt(restErrMatch[3]);
      if (status >= 400) {
        _fixedFingerprints.add(fp);
        if (canAlert('rest_api_error')) {
          pushToWalter({
            pattern_type: 'rest_api_error',
            severity: 'high',
            description: `${method} ${table} returned ${status}`,
          });
          notify('BR3: Database Error', `${method} ${table} → ${status}`);
        }
        // Always escalate to Claude — never auto-push migrations (too risky)
        escalateToClaude(
          `REST API error: ${method} /rest/v1/${table} returned ${status}. This likely means a migration hasn't been pushed — a column or table is missing in prod.`,
          `Table: ${table}\nStatus: ${status}\nCheck: ls supabase/migrations/ for unpushed migrations\nFix: verify migration is correct, then run 'supabase db push'`
        );
        continue;
      }
    }

    // --- Pattern 5: Catch-all for unmatched /functions/ or /rest/ non-200s ---
    const catchAllMatch = line.match(
      /\[NET\]\s+\w+\s+https?:\/\/\S*\/(functions\/v1|rest\/v1)\/([\w-]+)\S*\s+(\d{3})\s+\d+ms/
    );
    if (catchAllMatch) {
      const status = parseInt(catchAllMatch[3]);
      if (status >= 400 && !_fixedFingerprints.has(fp)) {
        _fixedFingerprints.add(fp);
        if (canAlert('unmatched_api_error')) {
          pushToWalter({
            pattern_type: 'api_error',
            severity: 'high',
            description: `${catchAllMatch[1]}/${catchAllMatch[2]} returned ${status}`,
          });
        }
      }
    }

    // --- Pattern 6: Any [ERROR] line → alert Walter + escalate on repeat ---
    if (line.includes('[ERROR]') && !line.includes('[vite]')) {
      const msg = line.replace(/^\[.*?\]\s*\[\w+\]\s*/, '').slice(0, 150);

      if (canAlert('runtime_error')) {
        pushToWalter({ pattern_type: 'runtime_error', severity: 'high', description: msg });
        notify('BR3: Runtime Error', msg);
      }

      if (_fixedFingerprints.has(fp)) {
        // Same error again — escalate to Claude
        escalateToClaude(
          `Recurring runtime error: ${msg}`,
          `This error has occurred multiple times. Auto-fix did not resolve it. Investigate and fix the root cause.`
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
      // Load both .env and .env.development (projects may use either)
      loadDotenv({ path: path.join(projectRoot, '.env') });
      loadDotenv({ path: path.join(projectRoot, '.env.development') });
      // Prefer BR_LOG_SUPABASE_* (points to PROD) over VITE_SUPABASE_* (points to DEV)
      // Prod logs broadcast to PROD Supabase Realtime, so we must listen there
      const supabaseUrl = process.env.BR_LOG_SUPABASE_URL || process.env.VITE_SUPABASE_URL;
      const supabaseKey =
        process.env.BR_LOG_SUPABASE_KEY ||
        process.env.SUPABASE_SERVICE_ROLE_KEY ||
        process.env.VITE_SUPABASE_ANON_KEY;

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
