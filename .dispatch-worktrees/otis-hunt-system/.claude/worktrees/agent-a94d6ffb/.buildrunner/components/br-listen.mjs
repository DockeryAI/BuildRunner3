#!/usr/bin/env node
/**
 * BR3 Standalone Log Listener
 * Subscribes to Supabase Realtime for remote device logs and writes to .buildrunner/*.log.
 * Works WITHOUT the Vite dev server — run alongside native app testing.
 *
 * Usage: node .buildrunner/br-listen.mjs
 *    or: npm run listen
 *
 * Part of BR3 infrastructure — shared across all projects.
 */

import fs from 'fs';
import path from 'path';
import { createClient } from '@supabase/supabase-js';

const LOG_TYPES = ['browser', 'supabase', 'device', 'query'];
const LOG_MAX_BYTES = 500 * 1024;
const LOG_KEEP_BYTES = 250 * 1024;

const projectRoot = process.cwd();
const logDir = path.join(projectRoot, '.buildrunner');

// --- Env parsing (same logic as vite-br-unified-plugin) ---
function loadEnv() {
  let supabaseUrl = '';
  let supabaseKey = '';

  const envPaths = [
    path.join(projectRoot, '.env.development'),
    path.join(projectRoot, '.env.local'),
    path.join(projectRoot, '.env'),
  ];

  for (const envPath of envPaths) {
    if (!fs.existsSync(envPath)) continue;
    const content = fs.readFileSync(envPath, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eq = trimmed.indexOf('=');
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      let val = trimmed.slice(eq + 1).trim();
      val = val.replace(/^["']|["']$/g, '');
      val = val.replace(/\s+#.*$/, '');
      if (key === 'VITE_SUPABASE_URL' && !supabaseUrl) supabaseUrl = val;
      if (key === 'VITE_SUPABASE_ANON_KEY' && !supabaseKey) supabaseKey = val;
    }
  }

  // Env var overrides
  if (process.env.BR_LOG_SUPABASE_URL) supabaseUrl = process.env.BR_LOG_SUPABASE_URL;
  if (process.env.BR_LOG_SUPABASE_KEY) supabaseKey = process.env.BR_LOG_SUPABASE_KEY;

  return { supabaseUrl, supabaseKey };
}

function getProjectName() {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(projectRoot, 'package.json'), 'utf-8'));
    return pkg.name || 'unknown';
  } catch {
    return 'unknown';
  }
}

// --- Log file helpers ---
function rotateIfNeeded(logPath) {
  try {
    if (!fs.existsSync(logPath)) return;
    const stat = fs.statSync(logPath);
    if (stat.size > LOG_MAX_BYTES) {
      const content = fs.readFileSync(logPath, 'utf-8');
      const cutIndex = content.indexOf('\n', content.length - LOG_KEEP_BYTES);
      if (cutIndex !== -1) {
        fs.writeFileSync(logPath, content.slice(cutIndex + 1));
      }
    }
  } catch {}
}

function appendLog(logPath, data) {
  if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
  rotateIfNeeded(logPath);
  const text = data.endsWith('\n') ? data : data + '\n';
  fs.appendFileSync(logPath, text);
}

// --- Main ---
const { supabaseUrl, supabaseKey } = loadEnv();
if (!supabaseUrl || !supabaseKey) {
  console.error('[BR3] No Supabase config found in .env files. Cannot listen for remote logs.');
  process.exit(1);
}

const projectName = getProjectName();
const logFiles = Object.fromEntries(
  LOG_TYPES.map((t) => [t, path.join(logDir, `${t}.log`)])
);

console.log(`[BR3] Listening for remote logs — project: ${projectName}`);
console.log(`[BR3] Supabase: ${supabaseUrl}`);
console.log(`[BR3] Log files: ${logDir}/`);
console.log('');

const supabase = createClient(supabaseUrl, supabaseKey);

supabase
  .channel('br-remote-logs')
  .on(
    'postgres_changes',
    { event: 'INSERT', schema: 'public', table: 'br_device_logs' },
    (payload) => {
      const row = payload.new;
      if (row.project !== projectName && row.project !== 'local-dev') return;

      const logType = row.log_type;
      if (!logFiles[logType]) return;

      const lines = row.content
        .split('\n')
        .filter(Boolean)
        .map((line) => {
          if (line.includes(`[${row.device_tag}]`)) return line;
          return line.replace(/^(\[[^\]]+\])/, `$1 [${row.device_tag}]`);
        })
        .join('\n');

      appendLog(logFiles[logType], lines);

      // Also print to terminal for live feedback
      const tag = `[${row.log_type}] [${row.device_tag}]`;
      for (const l of lines.split('\n').filter(Boolean)) {
        console.log(`${tag} ${l}`);
      }
    }
  )
  .subscribe((status) => {
    if (status === 'SUBSCRIBED') {
      console.log('[BR3] ✓ Connected — waiting for device logs...');
      console.log('[BR3] Use the app on your phone. Logs appear here + in .buildrunner/*.log');
      console.log('[BR3] Press Ctrl+C to stop.\n');
    } else if (status === 'CHANNEL_ERROR') {
      console.error('[BR3] ✗ Channel error — br_device_logs table may not exist. Run migration first.');
      process.exit(1);
    }
  });

// Keep alive
process.on('SIGINT', () => {
  console.log('\n[BR3] Stopped.');
  process.exit(0);
});
