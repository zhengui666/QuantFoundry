import { defineConfig } from 'playwright/test';

export default defineConfig({
  testDir: './e2e',
  webServer: {
    command: 'QF_E2E_MOCK_AUTH=1 pnpm dev --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
  },
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    // Locale is a server Control-DB projection; browser storage is never auth
    // or configuration truth.
    storageState: { cookies: [], origins: [] },
    locale: 'en-US',
    timezoneId: 'UTC',
  },
});
