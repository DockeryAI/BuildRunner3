import http from 'node:http';

import type { Plugin } from 'vite';

const BR_PROXY_PORT = 5710;

export function brUnifiedPlugin(): Plugin {
  return {
    name: 'br-unified-plugin',
    config() {
      return {
        define: {
          __BR_DEBUG__: JSON.stringify(true),
        },
      };
    },
    configureServer(server) {
      server.middlewares.use('/api/br-log', (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405;
          res.end('Method Not Allowed');
          return;
        }

        const proxyRequest = http.request(
          {
            host: '127.0.0.1',
            port: BR_PROXY_PORT,
            path: '/api/br-log',
            method: 'POST',
            headers: req.headers,
          },
          (proxyResponse) => {
            res.statusCode = proxyResponse.statusCode ?? 200;
            proxyResponse.pipe(res);
          }
        );

        req.pipe(proxyRequest);
        proxyRequest.on('error', () => {
          res.statusCode = 502;
          res.end('BR listener unavailable');
        });
      });
    },
  };
}

export default brUnifiedPlugin;
