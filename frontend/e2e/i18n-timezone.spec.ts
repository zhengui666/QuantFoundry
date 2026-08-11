import { expect, test, type Page } from 'playwright/test';
import { storybookDataCapabilities } from '../src/testing/msw-handlers';

async function openDataWithServerSettings(
  page: Page,
  settings: { language: 'zh-CN' | 'en'; timezone: string },
) {
  await page.addInitScript((serverSettings) => {
    localStorage.setItem('qf.server-settings.locale', JSON.stringify(serverSettings));
  }, settings);
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: '' }),
  );
  await page.route('**/api/v1/data/capabilities', (route) =>
    route.fulfill({ status: 200, json: storybookDataCapabilities }),
  );
  await page.goto('/data');
}

test('restores English Settings and formats canonical UTC in America/New_York', async ({
  page,
}) => {
  await openDataWithServerSettings(page, { language: 'en', timezone: 'America/New_York' });
  await expect(page.getByRole('heading', { name: 'Data capabilities' })).toBeVisible();
  await expect(page.locator('time')).toContainText('2026-08-09 22:00:00');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.locator('html')).toHaveAttribute('data-timezone', 'America/New_York');
});

test('restores Chinese Settings and formats canonical UTC in Asia/Shanghai', async ({ page }) => {
  await openDataWithServerSettings(page, { language: 'zh-CN', timezone: 'Asia/Shanghai' });
  await expect(page.getByRole('heading', { name: '数据能力' })).toBeVisible();
  await expect(page.locator('time')).toContainText('2026-08-10 10:00:00');
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
  await expect(page.locator('html')).toHaveAttribute('data-timezone', 'Asia/Shanghai');
});

test('fails closed to UTC when restored server Settings timezone is invalid', async ({ page }) => {
  await openDataWithServerSettings(page, { language: 'en', timezone: 'Invalid/Zone' });
  await expect(page.locator('time')).toContainText('2026-08-10 02:00:00 UTC');
  await expect(page.locator('html')).toHaveAttribute('data-timezone', 'UTC');
});
