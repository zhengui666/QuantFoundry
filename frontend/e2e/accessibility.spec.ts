import AxeBuilder from '@axe-core/playwright';
import { expect, test } from 'playwright/test';

test('primary navigation has page state and no critical axe violations', async ({ page }) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ contentType: 'text/event-stream', body: '' }),
  );
  await page.goto('/strategies');
  await expect(page.getByRole('link', { name: 'Strategies' })).toHaveAttribute(
    'aria-current',
    'page',
  );
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations
      .filter((v) => ['critical', 'serious'].includes(v.impact ?? ''))
      .map((v) => v.id),
  ).toEqual([]);
});

test('viewport boundary blocks below 1180 and collapses sidebar to 64px at 1180', async ({
  page,
}) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ contentType: 'text/event-stream', body: '' }),
  );
  await page.route('**/api/v1/overview', (route) =>
    route.fulfill({
      status: 503,
      json: {
        type: 'about:blank',
        title: 'Unavailable',
        status: 503,
        code: 'SERVICE_DEGRADED',
        detail: null,
        instance: null,
        request_id: 'REQ-VIEWPORT',
        retryable: true,
        field_errors: [],
        context: {},
      },
    }),
  );

  await page.setViewportSize({ width: 1179, height: 900 });
  await page.goto('/overview');
  await expect(page.getByRole('alert')).toContainText('Minimum supported width: 1180px.');
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeHidden();

  await page.setViewportSize({ width: 1180, height: 900 });
  const navigation = page.getByRole('navigation', { name: 'Primary' });
  await expect(navigation).toBeVisible();
  expect((await navigation.boundingBox())?.width).toBe(64);
  await expect(page.getByRole('link', { name: 'Overview' })).toHaveAttribute(
    'aria-current',
    'page',
  );
});
