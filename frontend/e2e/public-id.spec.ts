import { expect, test } from 'playwright/test';
import {
  canonicalPublicIdForms,
  publicIdNegativeCases,
  publicIdRouteCases,
} from '../src/api/public-id-test-cases';

test('QF-PID six routes accept both forms and reject every applicable 003..011 case pre-network', async ({
  page,
}) => {
  test.setTimeout(120_000);
  const resourceRequests: string[] = [];
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/v1/auth/session')
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        json: {
          principal: 'OWNER',
          auth_method: 'GENERAL_ACCESS_KEY',
          key_id: 'gak_e2e0000000000000',
          issued_at: '2026-08-10T00:00:00Z',
          last_seen_at: '2026-08-10T00:00:00Z',
          expires_at: '2099-01-01T00:00:00Z',
          csrf_token: 'e2e-csrf-token-0000000000000000000000',
        },
      });
    // Locale projection is control-plane state, not the resource under test.
    if (url.pathname === '/api/v1/configuration/active')
      return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
    if (url.pathname === '/api/v1/events/stream')
      return route.fulfill({ body: '', contentType: 'text/event-stream' });
    resourceRequests.push(url.pathname);
    return route.fulfill({
      status: 404,
      contentType: 'application/problem+json',
      json: {
        type: 'about:blank',
        title: 'Not found',
        status: 404,
        code: 'RESOURCE_NOT_FOUND',
        detail: null,
        instance: null,
        request_id: 'REQ-QF-PID-ROUTE',
        retryable: false,
        field_errors: [],
        context: {},
      },
    });
  });

  for (const { path, type } of publicIdRouteCases) {
    for (const id of canonicalPublicIdForms(type)) {
      const before = resourceRequests.length;
      await page.goto(`/${path}/${encodeURIComponent(id)}`, { waitUntil: 'domcontentloaded' });
      await expect
        .poll(() => resourceRequests.slice(before).some((requestPath) => requestPath.includes(id)))
        .toBe(true);
    }
    for (const invalid of publicIdNegativeCases(type)) {
      const before = resourceRequests.length;
      await page.goto(`/${path}/${encodeURIComponent(invalid.value)}`, {
        waitUntil: 'domcontentloaded',
      });
      await expect(
        page.getByText(/Invalid canonical .* public ID|公开 ID 不符合 canonical contract/i),
      ).toBeVisible();
      expect(resourceRequests, `${path}:${invalid.caseId}:${invalid.mutation}`).toHaveLength(
        before,
      );
    }
  }
});
