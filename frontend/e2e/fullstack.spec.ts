import { expect, test, type APIRequestContext, type Page } from 'playwright/test';
import type { Schema } from '../src/api/client';
import { ResearchDetailSchema } from '../src/api/generated/runtime-schemas';
import { createAuthenticatedStreamTracker } from '../src/testing/fullstack-stream-tracker';
import { startCanonicalSseProbe } from '../src/testing/fullstack-sse-probe';
import { SseRestReconciliationWitness } from '../src/testing/sse-rest-reconciliation';
import { canonicalEngineFixtures } from './fixture-builders';

const executeCapability = async (page: Page, action: string) => {
  const trigger = page.getByTestId(`capability-action-${action}`);
  const requiresConfirmation = await trigger.getAttribute('data-requires-confirmation');
  expect(['true', 'false']).toContain(requiresConfirmation);
  await trigger.click();
  if (requiresConfirmation === 'true')
    await page.getByTestId(`capability-confirm-${action}`).click();
};

const applicationUrl = process.env.QF_FULLSTACK_BASE_URL;
const bearerToken = process.env.QF_FULLSTACK_BEARER_TOKEN;
const factorId = process.env.QF_FULLSTACK_FACTOR_ID;
const snapshotId = process.env.QF_FULLSTACK_SNAPSHOT_ID;
const costModelId = process.env.QF_FULLSTACK_COST_MODEL_ID;
const validationPolicyId = process.env.QF_FULLSTACK_VALIDATION_POLICY_ID;
const enabled = Boolean(
  applicationUrl && bearerToken && factorId && snapshotId && costModelId && validationPolicyId,
);

const apiHeaders = (extra: Record<string, string> = {}) => ({
  Authorization: `Bearer ${bearerToken!}`,
  Accept: 'application/json',
  ...extra,
});

// The real Compose origin is different from the dev-server origin used by ordinary E2E.
// Seed the persisted server Settings projection per page, not a host/browser locale, so
// canonical English text locators stay deterministic while product default remains zh-CN.
const seedEnglishServerSettings = async (page: Page) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'qf.server-settings.locale',
      JSON.stringify({ language: 'en', timezone: 'UTC' }),
    );
  });
};

const createResearchThroughApi = async (request: APIRequestContext) => {
  const response = await request.post(new URL('/api/v1/research', applicationUrl!).href, {
    headers: apiHeaders({
      'Content-Type': 'application/json',
      'Idempotency-Key': crypto.randomUUID(),
    }),
    data: {
      title: `SSE causal ${crypto.randomUUID()}`,
      original_user_prompt: 'Prove decoded SSE causes exact active-query REST reconciliation.',
      research_policy_id: null,
    } satisfies Schema<'ResearchCreateRequest'>,
  });
  expect(response.status()).toBe(201);
  return ResearchDetailSchema.parse(await response.json()) as Schema<'ResearchDetail'>;
};

test.describe('platform-driven full-stack Golden Flow', () => {
  test.skip(
    !enabled,
    'Set QF_FULLSTACK_BASE_URL, bearer, factor, snapshot, cost-model, and policy IDs.',
  );

  test('proves decoded SSE causally refetches one active REST resource and converges UI', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
    const created = await createResearchThroughApi(request);
    const exactPath = `/api/v1/research/${created.research_id}`;
    const exactReads: string[] = [];
    page.on('request', (browserRequest) => {
      const url = new URL(browserRequest.url());
      if (browserRequest.method() === 'GET' && url.pathname === exactPath)
        exactReads.push(url.pathname);
    });

    await seedEnglishServerSettings(page);
    await page.goto(new URL(`/research/${created.research_id}?tab=overview`, applicationUrl!).href);
    await page.getByLabel('Bearer token').fill(bearerToken!);
    await page.getByRole('button', { name: 'Authenticate' }).click();
    await expect(page.getByRole('heading', { name: created.title })).toBeVisible();
    await expect(page.getByText('DRAFT', { exact: true })).toBeVisible();
    // StrictMode/route loader may perform more than one initial read. Freeze the
    // rendered query's actual baseline; no fixed count or timing assumption is made.
    const initialExactReads = exactReads.length;
    expect(initialExactReads).toBeGreaterThanOrEqual(1);

    const witness = new SseRestReconciliationWitness(
      'research',
      created.research_id,
      exactPath,
      initialExactReads,
    );
    exactReads.forEach((path) => witness.observeRest(path));
    const probe = await startCanonicalSseProbe(
      new URL('/api/v1/events/stream', applicationUrl!),
      bearerToken!,
    );
    const beforeMutation = await request.get(new URL(exactPath, applicationUrl!).href, {
      headers: apiHeaders(),
    });
    expect(beforeMutation.status()).toBe(200);
    const etag = beforeMutation.headers()['etag'];
    expect(etag).toBeTruthy();
    const canonicalBefore = ResearchDetailSchema.parse(
      await beforeMutation.json(),
    ) as Schema<'ResearchDetail'>;
    const refetchResponse = page.waitForResponse(
      (response) =>
        response.request().method() === 'GET' &&
        new URL(response.url()).pathname === exactPath &&
        response.status() === 200,
    );
    const start = await request.post(new URL(`${exactPath}/start`, applicationUrl!).href, {
      headers: apiHeaders({
        'Content-Type': 'application/json',
        'Idempotency-Key': crypto.randomUUID(),
        'If-Match': etag!,
      }),
      data: {
        research_revision_no: canonicalBefore.current_revision_no,
        capability_evaluation_confirmed: true,
      } satisfies Schema<'ResearchStartRequest'>,
    });
    expect(start.status()).toBe(202);
    const accepted = (await start.json()) as Schema<'JobAccepted'>;
    const frame = await probe.waitForFrame(
      ({ event }) =>
        event.event_type === 'research.updated' && event.object_id === created.research_id,
    );
    witness.observeEvent(frame);
    await refetchResponse;
    exactReads.slice(witness.baseline).forEach((path) => witness.observeRest(path));
    witness.assertReconciled();
    expect(exactReads.length).toBeGreaterThanOrEqual(initialExactReads + 1);
    expect(witness.snapshot().restReadsAfterBaseline).toBeGreaterThanOrEqual(1);
    await expect(page.getByText('RUNNING', { exact: true })).toBeVisible();
    await expect(page.getByText(`Job ${accepted.job_id}`)).toBeVisible();
    await probe.stop();
  });

  test('executes 11 canonical mutations against real server truth under continuous SSE', async ({
    page,
  }) => {
    test.setTimeout(10 * 60_000);
    const mutations: Array<{
      path: string;
      idempotency: string | null;
      ifMatch: string | null;
      body: unknown;
    }> = [];
    const reads: string[] = [];
    const streamTracker = createAuthenticatedStreamTracker(bearerToken!);
    page.on('request', (request) => {
      const url = new URL(request.url());
      if (
        url.pathname !== '/api/v1/events/stream' &&
        request.method() === 'GET' &&
        url.pathname.startsWith('/api/v1/')
      )
        reads.push(url.pathname);
      else if (request.method() === 'POST' && url.pathname.startsWith('/api/v1/'))
        mutations.push({
          path: url.pathname,
          idempotency: request.headers()['idempotency-key'] ?? null,
          ifMatch: request.headers()['if-match'] ?? null,
          body: request.postData() ? request.postDataJSON() : null,
        });
    });
    page.on('response', (response) => {
      const request = response.request();
      streamTracker.observeResponse({
        request,
        path: new URL(request.url()).pathname,
        status: response.status(),
        authorization: request.headers()['authorization'],
      });
    });
    page.on('requestfinished', (request) => streamTracker.observeTermination(request));
    page.on('requestfailed', (request) => streamTracker.observeTermination(request));

    await seedEnglishServerSettings(page);
    await page.goto(new URL('/overview', applicationUrl!).href);
    await page.getByLabel('Bearer token').fill(bearerToken!);
    await page.getByRole('button', { name: 'Authenticate' }).click();
    await expect(page.getByRole('heading', { name: /总览|Overview/ })).toBeVisible();
    await expect.poll(() => streamTracker.snapshot().authenticatedAccepted).toBe(true);
    const sseProbe = await startCanonicalSseProbe(
      new URL('/api/v1/events/stream', applicationUrl!),
      bearerToken!,
    );

    await executeCapability(page, 'create_research');
    await page.getByLabel('Title').fill(`Golden flow ${crypto.randomUUID()}`);
    await page.getByLabel('Research brief').fill('Test quality persistence after canonical costs.');
    await page.getByRole('button', { name: 'Create research' }).click();
    const researchLink = page.getByRole('link', { name: /^RSCH-/ }).last();
    const researchId = (await researchLink.textContent())!.trim();
    await sseProbe.waitForFrame(({ event }) => event.object_id === researchId);
    await researchLink.click();
    await executeCapability(page, 'start');
    await expect(page.getByText(/Research start accepted as job JOB-/)).toBeVisible();

    await page.getByRole('tab', { name: 'Experiments' }).click();
    const experimentLink = page.getByRole('link', { name: /^EXP-/ }).first();
    await expect(experimentLink).toBeVisible({ timeout: 120_000 });
    await experimentLink.click();
    await page.getByRole('button', { name: 'Reproduce' }).click();
    await page
      .getByRole('dialog', { name: 'Confirm experiment reproduction' })
      .getByRole('button', { name: 'Confirm reproduce' })
      .click();
    await expect(page.getByText(/Reproduce EXACT accepted as job JOB-/)).toBeVisible();

    await page.getByRole('link', { name: /策略|Strategies/ }).click();
    await page.getByLabel('Research ID').fill(researchId);
    await page.getByLabel('Strategy name').fill('Golden flow strategy');
    await page.getByLabel('Thesis').fill('Quality after measured costs.');
    await page.getByLabel('Symbols, comma separated').fill('SPY');
    await page.getByLabel('Factor ID').fill(factorId!);
    await page.getByLabel('Factor version').fill('1');
    await page.getByLabel('Selection count').fill('20');
    await page.getByLabel('Cost model ID').fill(costModelId!);
    await page.getByLabel('Benchmark').fill('SPY');
    for (const [label, value] of [
      ['Research start', '2010-01-01'],
      ['Research end', '2018-12-31'],
      ['Validation start', '2019-01-01'],
      ['Validation end', '2022-12-31'],
      ['Holdout start', '2023-01-01'],
      ['Holdout end', '2025-12-31'],
    ] as const)
      await page.getByLabel(label).fill(value);
    await page.getByLabel('Known failure mode').fill('Crowding');
    await page.getByRole('button', { name: 'Create candidate strategy' }).click();
    const strategyLink = page.getByRole('link', { name: /STRAT-.* v1/ });
    const strategyText = (await strategyLink.textContent())!;
    const strategyId = strategyText.match(/STRAT-[^ ]+/)![0];
    await strategyLink.click();

    await page.getByLabel('Snapshot ID').fill(snapshotId!);
    await page
      .getByLabel('Engine key', { exact: true })
      .fill(canonicalEngineFixtures.fastBacktest.engine_key);
    await page
      .getByLabel('Engine version', { exact: true })
      .fill(canonicalEngineFixtures.fastBacktest.engine_version);
    await page.getByLabel('Parameter key').fill('lookback');
    await page.getByLabel('Parameter value').fill('252');
    await executeCapability(page, 'run_fast_backtest');
    await expect(page.getByText(/Server job JOB-/)).toBeVisible();
    await expect
      .poll(
        () => mutations.find((mutation) => mutation.path.endsWith('/versions/1/backtests'))?.body,
      )
      .toEqual(expect.objectContaining(canonicalEngineFixtures.fastBacktest));
    await executeCapability(page, 'freeze');
    await expect(page.getByText(/FROZEN · This version is immutable/)).toBeVisible({
      timeout: 120_000,
    });

    await page.getByLabel('Validation policy ID').fill(validationPolicyId!);
    await page
      .getByLabel('Strict engine key')
      .fill(canonicalEngineFixtures.strictValidation.strict_engine_key);
    await page
      .getByLabel('Strict engine version')
      .fill(canonicalEngineFixtures.strictValidation.strict_engine_version);
    await page.getByLabel('Test suite version').fill('2026.1');
    await executeCapability(page, 'start_validation');
    await expect
      .poll(() => mutations.find((mutation) => mutation.path === '/api/v1/validations')?.body)
      .toEqual(expect.objectContaining(canonicalEngineFixtures.strictValidation));
    await page.getByRole('link', { name: /Open validation VAL-/ }).click();
    await expect(page.getByLabel('Approval reason')).toBeVisible({ timeout: 120_000 });
    await page.getByLabel('Approval reason').fill('One controlled exposure.');
    await executeCapability(page, 'request_holdout_approval');
    await page.getByRole('link', { name: /^APR-/ }).click();
    await executeCapability(page, 'approve');
    await expect(page.getByText('APPROVED')).toBeVisible();
    await page.getByRole('link', { name: /Open validation VAL-/ }).click();
    await executeCapability(page, 'run_holdout');

    await page.getByRole('link', { name: /备忘录|Memo/ }).click();
    await page.getByLabel('Strategy ID').fill(strategyId);
    await page.getByLabel('Strategy version').fill('1');
    await page.getByRole('button', { name: 'Generate evidence-bound memo' }).click();
    const memoLink = page.getByRole('link', { name: /Open memo MEMO-/ });
    await expect(memoLink).toBeVisible({
      timeout: 120_000,
    });
    const memoText = (await memoLink.textContent()) ?? '';
    const memoId = memoText.match(/MEMO-[^ ]+/)?.[0];
    expect(memoId).toBeTruthy();
    await sseProbe.waitForFrame(({ event }) => event.object_id === memoId);

    const expectedPaths = [
      '/api/v1/research',
      `/api/v1/research/${researchId}/start`,
      /\/api\/v1\/experiments\/EXP-[^/]+\/reproduce/,
      '/api/v1/strategies',
      new RegExp(`/api/v1/strategies/${strategyId}/versions/1/backtests`),
      new RegExp(`/api/v1/strategies/${strategyId}/versions/1/freeze`),
      '/api/v1/validations',
      /\/api\/v1\/validations\/VAL-[^/]+\/holdout-approval-requests/,
      /\/api\/v1\/approvals\/APR-[^/]+\/approve/,
      /\/api\/v1\/validations\/VAL-[^/]+\/holdout-runs/,
      '/api/v1/memos',
    ] as const;
    expect(mutations).toHaveLength(11);
    expectedPaths.forEach((expected, index) => {
      const actual = mutations[index]!;
      if (typeof expected === 'string') expect(actual.path).toBe(expected);
      else expect(actual.path).toMatch(expected);
      expect(actual.idempotency).toBeTruthy();
    });
    for (const index of [1, 5, 7, 8, 9]) expect(mutations[index]?.ifMatch).toBeTruthy();
    expect(reads.length).toBeGreaterThan(11);
    await expect
      .poll(async () => {
        const browserCursors = await page.evaluate(() =>
          Object.entries(sessionStorage)
            .filter(([key]) => key.startsWith('qf.sse.cursor:'))
            .map(([, value]) => Number(value)),
        );
        const probeCursors = sseProbe.snapshot().frames.map(({ cursor }) => cursor);
        return browserCursors.length === 1 && probeCursors.length > 0
          ? browserCursors[0]! - Math.max(...probeCursors)
          : null;
      })
      .toBe(0);
    const actualFrames = sseProbe.snapshot().frames;
    expect(sseProbe.snapshot().failure).toBeUndefined();
    expect(actualFrames.length).toBeGreaterThanOrEqual(11);
    expect(new Set(actualFrames.map(({ event }) => event.event_id)).size).toBe(actualFrames.length);
    expect(actualFrames.every(({ cursor, event }) => cursor === event.sequence)).toBe(true);
    expect(actualFrames.some(({ event }) => event.object_id === researchId)).toBe(true);
    expect(actualFrames.some(({ event }) => event.object_id === strategyId)).toBe(true);
    expect(actualFrames.some(({ event }) => event.object_id === memoId)).toBe(true);
    expect(reads.some((path) => path.includes(researchId))).toBe(true);
    expect(reads.some((path) => path.includes(strategyId))).toBe(true);
    expect(streamTracker.snapshot().authenticatedAccepted).toBe(true);
    expect(streamTracker.snapshot().authenticatedTerminated).toBe(false);
    await sseProbe.stop();
  });
});
