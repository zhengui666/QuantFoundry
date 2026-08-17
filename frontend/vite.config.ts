import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'e2e-auth-session',
      configureServer(server) {
        if (process.env.QF_E2E_MOCK_AUTH !== '1' || process.env.QF_E2E_MODE !== '1') return;
        server.middlewares.use((request, response, next) => {
          const expectedToken = process.env.QF_E2E_MOCK_TOKEN;
          if (!expectedToken || request.headers['x-qf-e2e-mock-token'] !== expectedToken) {
            next();
            return;
          }
          if (request.url === '/api/v1/auth/session') {
            response.statusCode = 200;
            response.setHeader('content-type', 'application/json');
            response.end(
              JSON.stringify({
                principal: 'OWNER',
                auth_method: 'GENERAL_ACCESS_KEY',
                key_id: 'gak_e2e0000000000000',
                issued_at: '2026-08-10T00:00:00Z',
                last_seen_at: '2026-08-10T00:00:00Z',
                expires_at: '2099-01-01T00:00:00Z',
                csrf_token: 'e2e-csrf-token-0000000000000000000000',
              }),
            );
            return;
          }
          if (request.url === '/api/v1/configuration/active') {
            response.statusCode = 200;
            response.setHeader('content-type', 'application/json');
            response.setHeader('etag', 'W/"config:1"');
            response.end(
              JSON.stringify({
                active_revision: 1,
                last_known_good_revision: 1,
                catalog_version: 'UX001_D1_CATALOG_R1',
                values: [
                  {
                    key: 'appearance.locale',
                    sensitivity: 'PUBLIC',
                    configured: true,
                    value: {
                      language: 'en',
                      timezone: 'UTC',
                      number_format_locale: 'en-US',
                      theme: 'SYSTEM',
                      density: 'COMFORTABLE',
                    },
                    masked_hint: null,
                  },
                ],
                snapshot_sha256: '0'.repeat(64),
                consumer_states: [],
                updated_at: '2026-08-10T00:00:00Z',
              }),
            );
            return;
          }
          next();
        });
      },
    },
  ],
  test: { environment: 'jsdom', exclude: ['e2e/**', 'node_modules/**', 'dist/**'] },
});
