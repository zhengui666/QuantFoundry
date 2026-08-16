import { expect, test, type Page } from 'playwright/test';
import type { Schema } from '../src/api/client';

const active = {
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
} as unknown as Schema<'ConfigurationActive'>;

const catalog = {
  catalog_version: 'UX001_D1_CATALOG_R1',
  entries: [
    {
      key: 'appearance.locale',
      group: 'appearance',
      schema_version: 1,
      scope: 'INSTALLATION',
      sensitivity: 'PUBLIC',
      apply_mode: 'LIVE_NEW_WORK',
      consumers: ['frontend'],
      dependencies: [],
      schema: {},
      validator: 'appearance.locale',
      safe_range: null,
    },
  ],
} satisfies Schema<'ConfigurationCatalog'>;

const keys = {
  items: [
    {
      key_id: 'gak_e2e0000000000000',
      label: 'primary',
      masked_hint: 'qfk_gak_e2e…abcd',
      status: 'ACTIVE',
      expires_at: null,
      last_used_at: '2026-08-10T00:00:00Z',
      revision: 1,
      created_at: '2026-08-10T00:00:00Z',
    },
  ],
} satisfies Schema<'GeneralAccessKeyList'>;

const database = {
  state: 'DATABASE_DISCONNECTED',
  active_revision: null,
  candidate_revision: null,
  last_known_good_revision: null,
  active: null,
  candidate: null,
  domain_operations: 'READ_ONLY_RECOVERY',
  checked_at: '2026-08-10T00:00:00Z',
} satisfies Schema<'DatabaseConnectionStatus'>;

async function routeSettings(page: Page) {
  await page.route('**/api/v1/configuration/catalog', (route) => route.fulfill({ json: catalog }));
  await page.route('**/api/v1/configuration/active', (route) =>
    route.fulfill({ json: active, headers: { ETag: 'W/"config:1"' } }),
  );
  await page.route('**/api/v1/auth/access-keys', (route) => route.fulfill({ json: keys }));
  await page.route('**/api/v1/database/connection', (route) =>
    route.fulfill({ json: database, headers: { ETag: 'W/"database:0"' } }),
  );
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: '' }),
  );
}

test('legacy setup entry converges to the single Settings control plane', async ({ page }) => {
  await routeSettings(page);
  await page.goto('/setup');
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await expect(page.getByText('Configuration catalog')).toBeVisible();
  await expect(page.getByText('General access keys')).toBeVisible();
});

test('Settings submits a typed candidate with ETag and activates only after validation', async ({
  page,
}) => {
  await routeSettings(page);
  let candidateBody: unknown;
  let activatedRevision = 0;
  await page.route('**/api/v1/configuration/candidate', async (route) => {
    candidateBody = await route.request().postDataJSON();
    return route.fulfill({
      json: {
        revision: 2,
        state: 'CANDIDATE',
        base_revision: 1,
        catalog_version: catalog.catalog_version,
        values: active.values,
        snapshot_sha256: '1'.repeat(64),
        created_at: '2026-08-10T00:00:00Z',
      } satisfies Schema<'ConfigurationCandidate'>,
    });
  });
  await page.route('**/api/v1/configuration/candidate/validate', (route) =>
    route.fulfill({
      json: {
        revision: 2,
        status: 'VALID',
        errors: [],
        warnings: [],
        validated_at: '2026-08-10T00:00:00Z',
      } satisfies Schema<'ConfigurationValidationResult'>,
    }),
  );
  await page.route('**/api/v1/configuration/activate', async (route) => {
    activatedRevision = (await route.request().postDataJSON()).revision;
    return route.fulfill({
      json: { ...active, active_revision: 2, last_known_good_revision: 2 },
      headers: { ETag: 'W/"config:2"' },
    });
  });
  await page.goto('/settings');
  await page
    .getByRole('textbox')
    .first()
    .fill(
      '{"language":"zh-CN","timezone":"Asia/Shanghai","number_format_locale":"zh-CN","theme":"SYSTEM","density":"COMFORTABLE"}',
    );
  await page.getByRole('button', { name: 'Validate and activate configuration' }).click();
  await expect(page.getByText('Configuration activated.')).toBeVisible();
  expect(candidateBody).toMatchObject({ base_revision: 1, values: [{ key: 'appearance.locale' }] });
  expect(activatedRevision).toBe(2);
});

test('Settings rotates and revokes an access key without exposing browser persistence', async ({
  page,
}) => {
  await routeSettings(page);
  let rotateCalls = 0;
  let revokeCalls = 0;
  await page.route('**/api/v1/auth/access-keys/gak_e2e0000000000000/rotate', (route) => {
    rotateCalls += 1;
    return route.fulfill({
      status: 201,
      json: {
        key: {
          key_id: 'gak_e2e0000000000000',
          label: 'primary',
          masked_hint: 'qfk_gak_e2e…abcd',
          status: 'ACTIVE',
          expires_at: null,
          last_used_at: '2026-08-10T00:00:00Z',
          revision: 1,
          created_at: '2026-08-10T00:00:00Z',
        },
        secret: 'qfk_gak_e2e0000000000000.' + 'A'.repeat(43),
      } satisfies Schema<'GeneralAccessKeyIssued'>,
    });
  });
  await page.route('**/api/v1/auth/access-keys/gak_e2e0000000000000/revoke', (route) => {
    revokeCalls += 1;
    return route.fulfill({ status: 204 });
  });
  page.on('dialog', (dialog) => dialog.accept());
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Rotate' }).click();
  await expect(page.getByText(/Copy this secret now/)).toBeVisible();
  await page.getByRole('button', { name: 'Revoke' }).click();
  expect(rotateCalls).toBe(1);
  expect(revokeCalls).toBe(1);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  expect(await page.evaluate(() => Object.keys(sessionStorage))).not.toContain(
    'qf.server-settings.locale',
  );
});
