import AxeBuilder from '@axe-core/playwright';
import { expect, test } from 'playwright/test';

test('primary navigation has page state and no critical axe violations', async ({ page }) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ contentType: 'text/event-stream', body: '' }),
  );
  await page.goto('/strategies');
  await expect(page.getByRole('link', { name: /Strategies|策略/ })).toHaveAttribute(
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

test('viewport remains usable around the desktop breakpoint', async ({ page }) => {
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
  await expect(page.getByRole('alert')).toContainText(
    /SERVICE_DEGRADED|service is degraded|服务.*降级/,
  );
  await expect(page.getByRole('navigation', { name: /Primary|主导航/ })).toBeVisible();

  await page.setViewportSize({ width: 1180, height: 900 });
  const navigation = page.getByRole('navigation', { name: /Primary|主导航/ });
  await expect(navigation).toBeVisible();
  expect((await navigation.boundingBox())?.width).toBeGreaterThan(0);
  await expect(page.getByRole('link', { name: /Overview|总览/ })).toHaveAttribute(
    'aria-current',
    'page',
  );
});
