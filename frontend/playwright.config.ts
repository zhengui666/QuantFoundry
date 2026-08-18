import { defineConfig } from 'playwright/test';

const fullstackBaseUrl = process.env.QF_FULLSTACK_BASE_URL;
if (fullstackBaseUrl) {
  const parsed = new URL(fullstackBaseUrl);
  const localHost = new Set(['127.0.0.1', 'localhost', '[::1]']).has(parsed.hostname);
  if (
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    !localHost ||
    !['http:', 'https:'].includes(parsed.protocol)
  )
    throw new Error('QF_FULLSTACK_BASE_URL must target an allowlisted loopback HTTP(S) host.');
}

export default defineConfig({
  testDir: './e2e',
  ...(fullstackBaseUrl
    ? { workers: 1 }
    : {
        webServer: {
          command:
            'token=$(node -e "process.stdout.write(require(\'node:crypto\').randomBytes(24).toString(\'hex\'))"); export QF_E2E_MOCK_TOKEN="$token" VITE_E2E_MOCK_TOKEN="$token" QF_E2E_MODE=1 QF_E2E_MOCK_AUTH=1; exec pnpm dev --host 127.0.0.1',
          url: 'http://127.0.0.1:5173',
          reuseExistingServer: false,
        },
      }),
  use: {
    baseURL: fullstackBaseUrl ?? 'http://127.0.0.1:5173',
    browserName: 'chromium',
    // Locale is a server Control-DB projection; browser storage is never auth
    // or configuration truth.
    storageState: { cookies: [], origins: [] },
    locale: 'en-US',
    timezoneId: 'UTC',
  },
});
