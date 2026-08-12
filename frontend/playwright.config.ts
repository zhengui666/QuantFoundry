import { defineConfig } from 'playwright/test';

export default defineConfig({
  testDir: './e2e',
  webServer: {
    command: 'pnpm dev --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
  },
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    // Product default remains zh-CN. CI seeds an explicit persisted server Settings
    // projection so role/text assertions cannot depend on a host/browser locale.
    storageState: {
      cookies: [],
      origins: [
        {
          origin: 'http://127.0.0.1:5173',
          localStorage: [
            { name: 'qf.server-settings.locale', value: '{"language":"en","timezone":"UTC"}' },
          ],
        },
      ],
    },
    locale: 'en-US',
    timezoneId: 'UTC',
  },
});
