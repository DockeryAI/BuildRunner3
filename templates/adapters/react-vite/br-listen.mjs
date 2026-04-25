import { mkdir, appendFile } from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';

const port = 5710;
const logPath = path.join(process.cwd(), '.buildrunner', 'browser.log');

const server = http.createServer(async (req, res) => {
  if (req.method !== 'POST' || req.url !== '/api/br-log') {
    res.statusCode = 404;
    res.end('Not Found');
    return;
  }

  const chunks = [];
  req.on('data', (chunk) => chunks.push(chunk));
  req.on('end', async () => {
    try {
      await mkdir(path.dirname(logPath), { recursive: true });
      const raw = Buffer.concat(chunks).toString('utf8');
      const parsed = JSON.parse(raw);
      const lines = Array.isArray(parsed.logs) ? parsed.logs : [parsed];
      const output = lines.map((line) => JSON.stringify(line)).join('\n') + '\n';
      await appendFile(logPath, output, 'utf8');
      res.statusCode = 204;
      res.end();
    } catch (error) {
      res.statusCode = 400;
      res.end(error instanceof Error ? error.message : 'Invalid payload');
    }
  });
});

server.listen(port, () => {
  process.stdout.write(`BR listener running on :${port}\n`);
});
