import { expect, test, type Page } from 'playwright/test';
import type { Schema } from '../src/api/client';
import { readySetupStatus } from './fixture-builders';

const capabilities = {
  providers: [],
  server_checked_at: '2026-08-10T00:00:00Z',
} satisfies Schema<'SetupCapabilityCatalog'>;

const completedStatus = {
  ...readySetupStatus,
  completed: true,
} satisfies Schema<'SetupStatus'>;

const aiFallback = {
  ...readySetupStatus,
  ai_provider_configured: false,
  ai_connection_id: null,
  fallback_step: 'AI_PROVIDER',
} satisfies Schema<'SetupStatus'>;

const costFallback = {
  ...readySetupStatus,
  cost_model_active: false,
  cost_model_id: null,
  fallback_step: 'RESEARCH_DEFAULTS',
} satisfies Schema<'SetupStatus'>;

const constitutionFallback = {
  ...readySetupStatus,
  research_policy_active: false,
  research_policy_id: null,
  fallback_step: 'RESEARCH_CONSTITUTION',
} satisfies Schema<'SetupStatus'>;

async function silenceEvents(page: Page) {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: '' }),
  );
}

async function routeCapabilities(page: Page) {
  await page.route('**/api/v1/setup/capabilities', (route) =>
    route.fulfill({ json: capabilities }),
  );
}

async function resumeSetup(page: Page) {
  await page.addInitScript(() => sessionStorage.setItem('qf.setup.started', 'true'));
}

async function reachReview(page: Page) {
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Skip optional data provider' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByText('Step 5 of 5')).toBeVisible();
}

for (const [name, status, expectedStep, reason] of [
  ['AI', aiFallback, 'Step 2 of 5', /No valid AI connection was detected/],
  ['cost model', costFallback, 'Step 4 of 5', /cost-model binding requires/],
  ['research constitution', constitutionFallback, 'Step 5 of 5', /bindings are required/],
] as const) {
  test(`P00 reload follows the server ${name} fallback`, async ({ page }) => {
    await silenceEvents(page);
    await resumeSetup(page);
    await routeCapabilities(page);
    await page.route('**/api/v1/setup/status', (route) => route.fulfill({ json: status }));
    await page.goto('/setup');
    await expect(page.getByText(expectedStep)).toBeVisible();
    await expect(page.getByText(reason)).toBeVisible();
  });
}

test('P00 reload trusts server completed status and leaves setup', async ({ page }) => {
  await silenceEvents(page);
  await routeCapabilities(page);
  await page.route('**/api/v1/setup/status', (route) => route.fulfill({ json: completedStatus }));
  await page.route('**/api/v1/overview', (route) =>
    route.fulfill({
      status: 401,
      json: {
        type: 'about:blank',
        title: 'Unauthenticated',
        status: 401,
        code: 'UNAUTHENTICATED',
        detail: 'Token required.',
        instance: null,
        request_id: 'REQ-AUTH',
        retryable: false,
        field_errors: [],
        context: {},
      } satisfies Schema<'ApiProblem'>,
    }),
  );
  await page.goto('/setup');
  await expect(page).toHaveURL(/\/overview$/);
  await expect(page.getByRole('heading', { name: 'First run setup' })).toHaveCount(0);
});

for (const [name, etag, message] of [
  ['missing', null, 'The server response did not match the canonical contract.'],
  ['malformed', 'SETTINGS-DEFAULT:3', 'The server response did not match the canonical contract.'],
  [
    'identity mismatch',
    'W/"SET-OTHER:3"',
    'The server response did not match the canonical contract.',
  ],
] as const) {
  test(`P00 ${name} setup ETag fails closed, does not replay, and converges with GET`, async ({
    page,
  }) => {
    await silenceEvents(page);
    await routeCapabilities(page);
    let postSeen = false;
    let posts = 0;
    let statusReads = 0;
    await page.route('**/api/v1/setup/status', (route) => {
      statusReads += 1;
      return route.fulfill({ json: postSeen ? costFallback : readySetupStatus });
    });
    await page.route('**/api/v1/setup/complete', async (route) => {
      posts += 1;
      postSeen = true;
      const request = (await route.request().postDataJSON()) as Schema<'SetupCompleteRequest'>;
      return route.fulfill({
        headers: etag ? { ETag: etag } : {},
        json: {
          settings_id: 'SETTINGS-DEFAULT',
          revision: 3,
          ...request,
          default_data_provider_id: request.default_data_provider_id ?? null,
          default_research_start: request.default_research_start ?? null,
          created_at: '2026-08-10T00:00:00Z',
          updated_at: '2026-08-10T00:01:00Z',
        } satisfies Schema<'SettingsDetail'>,
      });
    });
    await reachReview(page);
    await page.getByRole('button', { name: 'Finish setup' }).dblclick();
    await expect(page.getByText(message)).toBeVisible();
    await expect(page.getByText('Step 4 of 5')).toBeVisible();
    await expect.poll(() => statusReads).toBeGreaterThanOrEqual(3);
    expect(posts).toBe(1);
  });
}

test('P00 explicit replay keeps the exact body and idempotency key, then converges to completed GET', async ({
  page,
}) => {
  await silenceEvents(page);
  await routeCapabilities(page);
  let posts = 0;
  const keys: string[] = [];
  const bodies: unknown[] = [];
  await page.route('**/api/v1/setup/status', (route) =>
    route.fulfill({ json: posts >= 2 ? completedStatus : readySetupStatus }),
  );
  await page.route('**/api/v1/setup/complete', async (route) => {
    posts += 1;
    keys.push(route.request().headers()['idempotency-key'] ?? '');
    const request = (await route.request().postDataJSON()) as Schema<'SetupCompleteRequest'>;
    bodies.push(request);
    return route.fulfill({
      headers: { ETag: posts === 1 ? 'SETTINGS-DEFAULT:3' : 'W/"SETTINGS-DEFAULT:3"' },
      json: {
        settings_id: 'SETTINGS-DEFAULT',
        revision: 3,
        ...request,
        default_data_provider_id: request.default_data_provider_id ?? null,
        default_research_start: request.default_research_start ?? null,
        created_at: '2026-08-10T00:00:00Z',
        updated_at: '2026-08-10T00:01:00Z',
      } satisfies Schema<'SettingsDetail'>,
    });
  });
  await page.route('**/api/v1/overview', (route) => route.fulfill({ status: 503, body: '' }));
  await reachReview(page);
  await page.getByRole('button', { name: 'Finish setup' }).click();
  await expect(
    page.getByText('The server response did not match the canonical contract.'),
  ).toBeVisible();
  expect(posts).toBe(1);
  await page.getByRole('button', { name: 'Skip optional data provider' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Finish setup' }).click();
  await expect(page).toHaveURL(/\/overview$/);
  expect(posts).toBe(2);
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).toBe(keys[0]);
  expect(bodies[1]).toEqual(bodies[0]);
  expect(bodies[0]).toMatchObject({
    ai_connection_id: readySetupStatus.ai_connection_id,
    research_policy_id: readySetupStatus.research_policy_id,
    risk_policy_id: readySetupStatus.risk_policy_id,
    cost_model_id: readySetupStatus.cost_model_id,
  });
});
