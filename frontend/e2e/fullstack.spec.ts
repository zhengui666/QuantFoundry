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
const generalKey = process.env.QF_FULLSTACK_GENERAL_KEY;
const factorId = process.env.QF_FULLSTACK_FACTOR_ID;
const snapshotId = process.env.QF_FULLSTACK_SNAPSHOT_ID;
const costModelId = process.env.QF_FULLSTACK_COST_MODEL_ID;
const validationPolicyId = process.env.QF_FULLSTACK_VALIDATION_POLICY_ID;
const enabled = Boolean(
  applicationUrl && generalKey && factorId && snapshotId && costModelId && validationPolicyId,
);

let apiCsrfToken = '';
const apiHeaders = (extra: Record<string, string> = {}) => ({
  Accept: 'application/json',
  ...(apiCsrfToken ? { 'X-CSRF-Token': apiCsrfToken } : {}),
  ...extra,
});

const authenticateApi = async (request: APIRequestContext) => {
  const response = await request.post(new URL('/api/v1/auth/login', applicationUrl!).href, {
    data: { key: generalKey! },
  });
  expect(response.status()).toBe(200);
  const body = (await response.json()) as Schema<'SessionBootstrapResponse'>;
  apiCsrfToken = body.session.csrf_token;
};

const sessionCookie = async (request: APIRequestContext) => {
  const state = await request.storageState();
  const cookie = state.cookies.find((item) => item.name === 'qf_session');
  expect(cookie?.value).toBeTruthy();
  return `qf_session=${cookie!.value}`;
};

const createResearchThroughApi = async (request: APIRequestContext) => {
  await authenticateApi(request);
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
    'Set QF_FULLSTACK_BASE_URL, general key, factor, snapshot, cost-model, and policy IDs.',
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

    await page.goto(new URL(`/research/${created.research_id}?tab=overview`, applicationUrl!).href);
    await page.getByLabel(/通用密钥|General access key/).fill(generalKey!);
    await page.getByRole('button', { name: /登录|Sign in/ }).click();
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
    exactReads.forEach((path, index) => witness.observeRest(path, index + 1));
    const probe = await startCanonicalSseProbe(
      new URL('/api/v1/events/stream', applicationUrl!),
      await sessionCookie(request),
      new URL(applicationUrl!).origin,
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
    const readsAtEvent = exactReads.length;
    witness.observeEvent(frame, readsAtEvent);
    await refetchResponse;
    exactReads
      .slice(readsAtEvent)
      .forEach((path, index) => witness.observeRest(path, readsAtEvent + index + 1));
    witness.assertReconciled();
    expect(exactReads.length).toBeGreaterThanOrEqual(initialExactReads + 1);
    expect(witness.snapshot().restReadsAfterBaseline).toBeGreaterThanOrEqual(1);
    // The agent worker may advance the accepted run to WAITING USER before the
    // browser consumes the causal refetch; both are valid server-authoritative
    // post-start states.
    await expect(page.getByText(/RUNNING|WAITING USER|等待用户/).first()).toBeVisible();
    await expect(page.getByText(new RegExp(`(?:Job|任务) ${accepted.job_id}`))).toBeVisible();
    await probe.stop();
  });

  test('executes 11 canonical mutations against real server truth under continuous SSE', async ({
    page,
    request,
  }) => {
    test.setTimeout(10 * 60_000);
    await authenticateApi(request);
    const mutations: Array<{
      path: string;
      idempotency: string | null;
      ifMatch: string | null;
      body: unknown;
    }> = [];
    const reads: string[] = [];
    let browserCookie = '';
    const streamTracker = createAuthenticatedStreamTracker(() => browserCookie);
    page.on('request', (request) => {
      const url = new URL(request.url());
      if (
        url.pathname !== '/api/v1/events/stream' &&
        request.method() === 'GET' &&
        url.pathname.startsWith('/api/v1/')
      )
        reads.push(url.pathname);
      else if (
        request.method() === 'POST' &&
        url.pathname.startsWith('/api/v1/') &&
        url.pathname !== '/api/v1/auth/login'
      )
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
        cookie: request.headers()['cookie'] ?? '',
      });
    });
    page.on('requestfinished', (request) => streamTracker.observeTermination(request));
    page.on('requestfailed', (request) => streamTracker.observeTermination(request));

    await page.goto(new URL('/overview', applicationUrl!).href);
    await page.getByLabel(/通用密钥|General access key/).fill(generalKey!);
    await page.getByRole('button', { name: /登录|Sign in/ }).click();
    await expect(page.getByRole('heading', { name: /总览|Overview/ })).toBeVisible();
    browserCookie = `qf_session=${(await page.context().cookies()).find((item) => item.name === 'qf_session')?.value ?? ''}`;
    await expect.poll(() => streamTracker.snapshot().authenticatedAccepted).toBe(true);
    const sseProbe = await startCanonicalSseProbe(
      new URL('/api/v1/events/stream', applicationUrl!),
      `qf_session=${(await page.context().cookies()).find((item) => item.name === 'qf_session')?.value}`,
      new URL(applicationUrl!).origin,
    );

    await executeCapability(page, 'create_research');
    await page.getByLabel(/Title|标题/).fill(`Golden flow ${crypto.randomUUID()}`);
    await page
      .getByLabel(/Research brief|研究简报/)
      .fill('Test quality persistence after canonical costs.');
    await page.getByRole('button', { name: /Create research|新建研究/ }).click();
    const researchLink = page.getByRole('link', { name: /^RSCH-/ }).last();
    const researchId = (await researchLink.textContent())!.trim();
    await sseProbe.waitForFrame(({ event }) => event.object_id === researchId);
    await researchLink.click();
    await executeCapability(page, 'start');
    await expect(
      page.getByText(/Research start accepted as job JOB-|研究启动已接受为任务 JOB-/),
    ).toBeVisible();

    await page.getByRole('tab', { name: /Experiments|实验/ }).click();
    const experimentLink = page.getByRole('link', { name: /^EXP-/ }).first();
    await expect(experimentLink).toBeVisible({ timeout: 120_000 });
    await experimentLink.click();
    await page.getByRole('button', { name: /Reproduce|复现/ }).click();
    await page
      .getByRole('dialog', { name: /Confirm experiment reproduction|确认复现实验/ })
      .getByRole('button', { name: /Confirm reproduce|确认复现/ })
      .click();
    await expect(
      page.getByText(/Reproduce EXACT accepted as job JOB-|复现 EXACT 已接受为任务 JOB-/),
    ).toBeVisible();

    await page.getByRole('link', { name: /策略|Strategies/ }).click();
    await page.getByLabel(/Research ID|研究 ID/).fill(researchId);
    await page.getByLabel(/Strategy name|策略名称/).fill('Golden flow strategy');
    await page.getByLabel(/Thesis|论点/).fill('Quality after measured costs.');
    await page.getByLabel(/Symbols, comma separated|标的代码，逗号分隔/).fill('SPY');
    await page.getByLabel(/Factor ID|因子 ID/).fill(factorId!);
    await page.getByLabel(/Factor version|因子版本/).fill('1');
    await page.getByLabel(/Selection count|选择数量/).fill('20');
    await page.getByLabel(/Cost model ID|成本模型 ID/).fill(costModelId!);
    await page.getByLabel(/Benchmark|基准/).fill('SPY');
    for (const [label, value] of [
      ['Research start', '2010-01-01'],
      ['Research end', '2018-12-31'],
      ['Validation start', '2019-01-01'],
      ['Validation end', '2022-12-31'],
      ['Holdout start', '2023-01-01'],
      ['Holdout end', '2025-12-31'],
    ] as const)
      await page
        .getByLabel(
          new RegExp(
            `${label}|${
              {
                'Research start': '研究起始日期',
                'Research end': '研究结束日期',
                'Validation start': '验证起始日期',
                'Validation end': '验证结束日期',
                'Holdout start': 'Holdout 起始日期',
                'Holdout end': 'Holdout 结束日期',
              }[label]
            }`,
          ),
        )
        .fill(value);
    await page.getByLabel(/Known failure mode|已知失败模式/).fill('Crowding');
    await page.getByRole('button', { name: /Create candidate strategy|创建候选策略/ }).click();
    const strategyLink = page.getByRole('link', { name: /STRAT-.* v1/ });
    const strategyText = (await strategyLink.textContent())!;
    const strategyId = strategyText.match(/STRAT-[^ ]+/)![0];
    await strategyLink.click();

    await page.getByLabel(/Snapshot ID|快照 ID/).fill(snapshotId!);
    await page
      .getByLabel(/Engine key|引擎键/, { exact: true })
      .fill(canonicalEngineFixtures.fastBacktest.engine_key);
    await page
      .getByLabel(/Engine version|引擎版本/, { exact: true })
      .fill(canonicalEngineFixtures.fastBacktest.engine_version);
    await page.getByLabel(/Parameter key|参数键/).fill('lookback');
    await page.getByLabel(/Parameter value|参数值/).fill('252');
    await executeCapability(page, 'run_fast_backtest');
    await expect(page.getByText(/Server job JOB-|服务端任务 JOB-/)).toBeVisible();
    await expect
      .poll(
        () => mutations.find((mutation) => mutation.path.endsWith('/versions/1/backtests'))?.body,
      )
      .toEqual(expect.objectContaining(canonicalEngineFixtures.fastBacktest));
    await executeCapability(page, 'freeze');
    await expect(
      page.getByText(/FROZEN · This version is immutable|已冻结 FROZEN · 此版本不可变/),
    ).toBeVisible({
      timeout: 120_000,
    });

    await page.getByLabel(/Validation policy ID|验证策略 ID/).fill(validationPolicyId!);
    await page
      .getByLabel(/Strict engine key|严格引擎键/)
      .fill(canonicalEngineFixtures.strictValidation.strict_engine_key);
    await page
      .getByLabel(/Strict engine version|严格引擎版本/)
      .fill(canonicalEngineFixtures.strictValidation.strict_engine_version);
    await page.getByLabel(/Test suite version|测试套件版本/).fill('2026.1');
    await executeCapability(page, 'start_validation');
    await expect
      .poll(() => mutations.find((mutation) => mutation.path === '/api/v1/validations')?.body)
      .toEqual(expect.objectContaining(canonicalEngineFixtures.strictValidation));
    const validationLink = page.getByRole('link', { name: /Open validation VAL-|打开验证 VAL-/ });
    const validationText = (await validationLink.textContent()) ?? '';
    const validationId = validationText.match(/VAL-[^ ]+/)?.[0];
    if (!validationId) throw new Error('Validation link did not expose a canonical validation ID.');
    await validationLink.click();
    await expect(page.getByLabel(/Approval reason|审批原因/)).toBeVisible({ timeout: 120_000 });
    await page.getByLabel(/Approval reason|审批原因/).fill('One controlled exposure.');
    await executeCapability(page, 'request_holdout_approval');
    await page.getByRole('link', { name: /^APR-/ }).click();
    await executeCapability(page, 'approve');
    await expect(page.getByText('APPROVED')).toBeVisible();
    await page.getByRole('link', { name: /Open validation VAL-|打开验证 VAL-/ }).click();
    await executeCapability(page, 'run_holdout');
    await expect
      .poll(
        async () => {
          const response = await request.get(
            new URL(`/api/v1/validations/${validationId}`, applicationUrl!).href,
            { headers: apiHeaders() },
          );
          if (response.status() !== 200) return null;
          const body = (await response.json()) as { holdout_state?: string };
          return body.holdout_state ?? null;
        },
        { timeout: 120_000 },
      )
      .toBe('EXPOSED');
    await sseProbe.waitForFrame(
      ({ event }) =>
        event.event_type === 'validation.holdout.updated' &&
        event.object_id === validationId &&
        event.payload.status === 'COMPLETED',
    );

    await page.getByRole('link', { name: /备忘录|Memo/ }).click();
    await page.getByLabel(/Strategy ID|策略 ID/).fill(strategyId);
    await page.getByLabel(/Strategy version|策略版本/).fill('1');
    await page
      .getByRole('button', { name: /Generate evidence-bound memo|生成证据绑定备忘录/ })
      .click();
    const memoLink = page.getByRole('link', { name: /Open memo MEMO-|打开备忘录 MEMO-/ });
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
            .map(([, value]) => value),
        );
        const probeCursors = sseProbe.snapshot().frames.map(({ cursor }) => cursor);
        if (browserCursors.length !== 1 || probeCursors.length === 0) return null;
        const latestProbeCursor = probeCursors.reduce((latest, cursor) =>
          BigInt(cursor) > BigInt(latest) ? cursor : latest,
        );
        return BigInt(browserCursors[0]!) === BigInt(latestProbeCursor) ? 0 : null;
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
