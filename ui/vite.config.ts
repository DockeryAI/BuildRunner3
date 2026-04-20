import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const LOG_MAX_BYTES = 500 * 1024; // 500 KB
const LOG_KEEP_BYTES = 250 * 1024; // keep last ~250 KB after rotation

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

// DEV-ONLY: configureServer() is a Vite dev-server hook — it is never
// called during `vite build`, so this plugin has zero production impact.
function supabaseLogPlugin(): Plugin {
  return {
    name: 'supabase-log',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.method === 'POST' && req.url === '/__supabase_log') {
          let body = '';
          req.on('data', (chunk: Buffer) => {
            body += chunk.toString();
          });
          req.on('end', () => {
            const logPath = path.resolve(__dirname, '..', '.buildrunner', 'supabase.log');
            fs.mkdirSync(path.dirname(logPath), { recursive: true });
            rotateLogIfNeeded(logPath);
            fs.appendFileSync(logPath, body + '\n');
            res.writeHead(204);
            res.end();
          });
          return;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), supabaseLogPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3001,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
  preview: {
    port: 3001,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['node_modules/**', '.dispatch-worktrees/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/', '**/*.d.ts', '**/*.config.*', '**/mockData.ts'],
    },
  },
});
