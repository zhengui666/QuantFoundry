import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { api, ApiError, auth, ContractError, queryKeysForEvent, streamEvents } from './client';
import { errorCopy } from '../ui';
import type { Schema } from './client';
import { EventObjectExamples, EventTypeObjectTypeMap } from './generated/runtime-schemas';

const base = '*';
const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  auth.clear();
  sessionStorage.clear();
  vi.useRealTimers();
});
afterAll(() => server.close());

const setupRequest = { configuration_revision: 1 } satisfies Schema<'SetupCompleteRequest'>;
const activeConfiguration = {
  active_revision: 1,
  last_known_good_revision: 1,
  catalog_version: 'v1',
  values: [
    {
      key: 'ui.locale',
      sensitivity: 'PUBLIC',
      configured: true,
      value: 'zh-CN',
      masked_hint: null,
    },
  ],
  snapshot_sha256: 'a'.repeat(64),
  consumer_states: [
    {
      consumer: 'frontend',
      desired_revision: 1,
      applied_revision: 1,
      ack: 'ACKED',
      error_code: null,
      heartbeat_at: '2026-08-10T00:00:00Z',
    },
  ],
  updated_at: '2026-08-10T00:00:00Z',
} satisfies Schema<'ConfigurationActive'>;

const ownerSession = (key_id = 'KEY-1', csrf_token = 'csrf-1') =>
  ({
    principal: 'OWNER',
    auth_method: 'GENERAL_ACCESS_KEY',
    key_id,
    issued_at: '2026-08-10T00:00:00Z',
    last_seen_at: '2026-08-10T00:00:00Z',
    expires_at: '2026-08-11T00:00:00Z',
    csrf_token,
  }) satisfies Schema<'OwnerSessionView'>;

const strategySpecification = {
  thesis: 'Canonical quality thesis.',
  universe: { asset_class: 'EQUITY', symbols: ['SPY'], universe_id: null },
  signals: [
    {
      factor_id: 'FAC-701PW0JDPSYYMVWDY210EKMTVQ',
      factor_version: 1,
      direction: 'LONG',
      weight: '1',
    },
  ],
  rules: {
    selection_count: 20,
    weighting: 'EQUAL',
    rebalance_frequency: 'MONTHLY',
    long_short: false,
    leverage_limit: '1',
    position_limit: '0.1',
  },
  cost_model_id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF',
  benchmark: 'SPY',
  research_period: { start: '2010-01-01', end: '2018-12-31' },
  validation_period: { start: '2019-01-01', end: '2022-12-31' },
  holdout_period: { start: '2023-01-01', end: '2025-12-31' },
  known_failure_modes: ['Crowding'],
  spec_sha256: 'a'.repeat(64),
} satisfies Schema<'StrategySpecification'>;

const strategyResponse = {
  strategy_id: 'STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG',
  name: 'Canonical strategy',
  version: 4,
  lifecycle_state: 'FROZEN',
  is_frozen: true,
  ...strategySpecification,
  specification: strategySpecification,
  latest_backtest: { state: 'EMPTY', result: null, metrics: [], chart: null },
  validation_summary: null,
  artifacts: [],
  provenance: [],
  frozen_at: '2026-08-10T00:00:00Z',
  frozen_by: 'owner',
  revision: 5,
  action_capabilities: [],
  created_at: '2026-08-09T00:00:00Z',
} satisfies Schema<'StrategyVersionDetail'>;

const availableBacktest = {
  state: 'AVAILABLE',
  result: {
    experiment: {
      type: 'experiment',
      id: 'EXP-6HASHPMWTVXN1E1KFT7YMMBE17',
      version: null,
      revision: 1,
    },
    status: 'COMPLETED',
    validity_state: 'VALID',
    result_sha256: 'd'.repeat(64),
    job_id: null,
    provenance: { provenance_id: 'PROV-4B6866SF8D8VPTTJSV3JFVVEPS' },
    started_at: null,
    finished_at: '2026-08-10T01:00:00Z',
  },
  metrics: [{ key: 'sharpe', value: '1.25', unit: 'ratio' }],
  chart: {
    schema_version: 1,
    chart_id: 'strategy-equity',
    chart_type: 'EQUITY_CURVE',
    metric_key: 'nav',
    x_axis: { kind: 'TIME', timezone: 'UTC' },
    series: [
      {
        series_id: 'strategy',
        series_key: 'strategy',
        display_label: 'Strategy',
        unit: 'USD',
        value_format: { kind: 'CURRENCY', precision: 2 },
        points: [{ x: '2026-01-01', y: '100' }],
      },
    ],
    period_markers: [],
    assumptions: [],
    summary: {
      template_key: 'chart.equity_curve.summary',
      params: { ending_nav: '100', benchmark_ending_nav: null },
    },
    downsampling: { applied: false, source_points: 1, returned_points: 1, method: null },
    provenance: { provenance_id: 'PROV-4B6866SF8D8VPTTJSV3JFVVEPS' },
    generated_at: '2026-08-10T01:00:00Z',
  },
} satisfies Extract<Schema<'StrategyLatestBacktest'>, { state: 'AVAILABLE' }>;

describe('canonical P0 network behavior', () => {
  it('submits the installation configuration revision with cookie-session CSRF', async () => {
    let received: unknown;
    server.use(
      http.post(`${base}/api/v1/setup/complete`, async ({ request }) => {
        received = await request.json();
        expect(request.headers.get('Idempotency-Key')).toBeTruthy();
        expect(request.headers.get('X-CSRF-Token')).toBe('csrf-1');
        return HttpResponse.json(activeConfiguration, { headers: { ETag: 'W/"config:1"' } });
      }),
    );
    auth.establish(ownerSession());
    await expect(api.completeSetup(setupRequest, 'W/"config:1"', 'SETUP-1')).resolves.toMatchObject(
      {
        body: activeConfiguration,
        etag: 'W/"config:1"',
      },
    );
    expect(received).toEqual(setupRequest);
  });

  it('replays the same setup idempotency key without client mutation', async () => {
    const keys: string[] = [];
    const bodies: unknown[] = [];
    server.use(
      http.post(`${base}/api/v1/setup/complete`, async ({ request }) => {
        keys.push(request.headers.get('Idempotency-Key') ?? '');
        bodies.push(await request.json());
        return HttpResponse.json(activeConfiguration, { headers: { ETag: 'W/"config:1"' } });
      }),
    );
    const first = await api.completeSetup(setupRequest, 'W/"config:1"', 'SETUP-INTENT-REPLAY-0001');
    const replay = await api.completeSetup(
      setupRequest,
      'W/"config:1"',
      'SETUP-INTENT-REPLAY-0001',
    );
    expect(first).toEqual(replay);
    expect(first.etag).toBe('W/"config:1"');
    expect(keys).toEqual(['SETUP-INTENT-REPLAY-0001', 'SETUP-INTENT-REPLAY-0001']);
    expect(bodies).toEqual([setupRequest, setupRequest]);
  });

  it('decodes the closed active-configuration response and surfaces API problems once', async () => {
    let calls = 0;
    server.use(
      http.post(`${base}/api/v1/setup/complete`, () => {
        calls += 1;
        return HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Configuration invalid',
            status: 422,
            code: 'CONFIGURATION_VALIDATION_FAILED',
            detail: 'Candidate configuration is invalid.',
            instance: null,
            request_id: 'REQ-CONFIG-1',
            retryable: false,
            field_errors: [],
            context: {},
          } satisfies Schema<'ApiProblem'>,
          { status: 422 },
        );
      }),
    );
    await expect(
      api.completeSetup(setupRequest, 'W/"config:1"', 'SETUP-INVALID-1'),
    ).rejects.toSatisfy(
      (error: unknown) =>
        error instanceof ApiError && error.problem.code === 'CONFIGURATION_VALIDATION_FAILED',
    );
    expect(calls).toBe(1);
  });

  it('P09 decodes current and explicit identity, Content-Location, and every spec mirror field', async () => {
    let response: unknown = strategyResponse;
    server.use(
      http.get(`${base}/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/current-version`, () =>
        HttpResponse.json(response as Record<string, unknown>, {
          headers: {
            ETag: 'W/"strategy:5"',
            'Content-Location': '/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4',
          },
        }),
      ),
      http.get(`${base}/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4`, () =>
        HttpResponse.json(response as Record<string, unknown>, {
          headers: { ETag: 'W/"strategy:5"' },
        }),
      ),
    );
    await expect(
      api.currentStrategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG'),
    ).resolves.toMatchObject({ body: { version: 4 }, etag: 'W/"strategy:5"' });
    await expect(api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 4)).resolves.toMatchObject(
      { body: { version: 4 } },
    );

    const corruptValues: Record<string, unknown> = {
      thesis: 'Different thesis',
      universe: { asset_class: 'EQUITY', symbols: ['QQQ'], universe_id: null },
      signals: [],
      rules: { ...strategySpecification.rules, selection_count: 10 },
      cost_model_id: 'COST-3ATWHJE111SKP4CAH92T3TYNNW',
      benchmark: 'QQQ',
      research_period: { start: '2011-01-01', end: '2018-12-31' },
      validation_period: { start: '2019-01-01', end: '2021-12-31' },
      holdout_period: { start: '2024-01-01', end: '2025-12-31' },
      known_failure_modes: ['Different valid limitation'],
      spec_sha256: 'b'.repeat(64),
    };
    for (const [field, value] of Object.entries(corruptValues)) {
      response = { ...strategyResponse, [field]: value };
      await expect(
        api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 4),
        field,
      ).rejects.toBeInstanceOf(ContractError);
    }
    response = { ...strategyResponse, strategy_id: 'STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP' };
    await expect(api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 4)).rejects.toThrow(
      'identity',
    );
    response = { ...strategyResponse, version: 5 };
    await expect(api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 4)).rejects.toThrow(
      'identity',
    );
    response = strategyResponse;
    await expect(api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 0)).rejects.toBeInstanceOf(
      ContractError,
    );
  });

  it('P09 accepts only closed AVAILABLE/EMPTY/LOCKED information-boundary bodies', async () => {
    let response: unknown = strategyResponse;
    server.use(
      http.get(`${base}/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4`, () =>
        HttpResponse.json(response as Record<string, unknown>),
      ),
    );
    for (const latest_backtest of [
      availableBacktest,
      { state: 'EMPTY', result: null, metrics: [], chart: null },
      { state: 'LOCKED', result: null, metrics: [], chart: null },
    ] satisfies Schema<'StrategyLatestBacktest'>[]) {
      response = { ...strategyResponse, latest_backtest };
      await expect(
        api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 4),
      ).resolves.toMatchObject({ body: { latest_backtest: { state: latest_backtest.state } } });
    }
    for (const leaked of [
      {
        state: 'EMPTY',
        result: availableBacktest.result,
        metrics: [],
        chart: null,
      },
      {
        state: 'LOCKED',
        result: null,
        metrics: availableBacktest.metrics,
        chart: null,
      },
      {
        state: 'LOCKED',
        result: null,
        metrics: [],
        chart: availableBacktest.chart,
      },
    ]) {
      response = { ...strategyResponse, latest_backtest: leaked };
      await expect(
        api.strategyVersion('STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', 4),
      ).rejects.toBeInstanceOf(ContractError);
    }
  });

  it('P09 validates every create/freeze/backtest mutation response at runtime', async () => {
    let strategyMutation: unknown = { ...strategyResponse, leaked: true };
    let jobMutation: unknown = { leaked: true };
    server.use(
      http.post(`${base}/api/v1/strategies`, () =>
        HttpResponse.json(strategyMutation as Record<string, unknown>),
      ),
      http.post(
        `${base}/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4/freeze`,
        () => HttpResponse.json(strategyMutation as Record<string, unknown>),
      ),
      http.post(
        `${base}/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4/backtests`,
        () => HttpResponse.json(jobMutation as Record<string, unknown>, { status: 202 }),
      ),
    );
    const create = {
      research_id: 'RSCH-399GM4EKDQ6VFNPE5EQ50HTV2J',
      name: 'Canonical strategy',
      thesis: strategySpecification.thesis,
      universe: strategySpecification.universe,
      signals: strategySpecification.signals,
      rules: strategySpecification.rules,
      cost_model_id: strategySpecification.cost_model_id,
      benchmark: strategySpecification.benchmark,
      research_period: strategySpecification.research_period,
      validation_period: strategySpecification.validation_period,
      holdout_period: strategySpecification.holdout_period,
      known_failure_modes: strategySpecification.known_failure_modes,
    } satisfies Schema<'StrategyCreateRequest'>;
    await expect(api.createStrategy(create)).rejects.toBeInstanceOf(ContractError);
    await expect(
      api.freezeStrategy(strategyResponse.strategy_id, 4, 'W/"strategy:5"', {
        expected_spec_sha256: strategyResponse.spec_sha256,
      }),
    ).rejects.toBeInstanceOf(ContractError);
    await expect(
      api.runFastBacktest(strategyResponse.strategy_id, 4, {
        snapshot_id: 'DS-249YFX4XBC3W17QTNC1X3EBKW4',
        cost_model_id: strategyResponse.cost_model_id,
        engine_key: 'canonical',
        engine_version: '1',
        parameters: [],
      }),
    ).rejects.toBeInstanceOf(ContractError);
    strategyMutation = strategyResponse;
    jobMutation = {
      job_id: 'JOB-3VXQ8F5QZ7CXQRCB55YDERE3XT',
      status: 'QUEUED',
      progress: {
        mode: 'NONE',
        completed_units: null,
        total_units: null,
        unit: null,
        percent: null,
        current_step_key: null,
        current_step_label: null,
      },
      resource_ref: null,
      created_at: '2026-08-10T00:00:00Z',
    } satisfies Schema<'JobAccepted'>;
    await expect(api.createStrategy(create)).resolves.toMatchObject({ body: strategyResponse });
    await expect(
      api.freezeStrategy(strategyResponse.strategy_id, 4, 'W/"strategy:5"', {
        expected_spec_sha256: strategyResponse.spec_sha256,
      }),
    ).resolves.toMatchObject({ body: strategyResponse });
    await expect(
      api.runFastBacktest(strategyResponse.strategy_id, 4, {
        snapshot_id: 'DS-249YFX4XBC3W17QTNC1X3EBKW4',
        cost_model_id: strategyResponse.cost_model_id,
        engine_key: 'canonical',
        engine_version: '1',
        parameters: [],
      }),
    ).resolves.toMatchObject({ body: { status: 'QUEUED' } });
  });

  it('uses If-Match and idempotency for a holdout action', async () => {
    server.use(
      http.post(
        `${base}/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout-approval-requests`,
        async ({ request }) => {
          expect(request.headers.get('If-Match')).toBe('W/"val:1"');
          expect(request.headers.get('Idempotency-Key')).toBeTruthy();
          expect(await request.json()).toEqual({ reason: 'owner reviewed prerequisites' });
          return HttpResponse.json(
            {
              approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
              type: 'HOLDOUT_UNLOCK',
              subject: {
                type: 'VALIDATION',
                id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
                version: 1,
                revision: 1,
                sha256: 'a'.repeat(64),
              },
              requester: { type: 'OWNER', id: 'o' },
              reason: 'r',
              prerequisites: [],
              risk_summary: { risk_level: 'LOW', warning_codes: [] },
              effects: [],
              status: 'PENDING',
              requested_at: '2026-01-01T00:00:00Z',
              decided_at: null,
              revision: 1,
              action_capabilities: [],
            },
            { headers: { ETag: 'W/"apr:1"' } },
          );
        },
      ),
    );
    await api.requestHoldoutApproval('VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', 'W/"val:1"', {
      reason: 'owner reviewed prerequisites',
    });
  });

  it('uses cookie sessions, fresh CSRF values, and distinct idempotency keys for holdout runs', async () => {
    const authorization: Array<string | null> = [];
    const csrf: Array<string | null> = [];
    const keys: string[] = [];
    server.use(
      http.post(
        `${base}/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout-runs`,
        ({ request }) => {
          authorization.push(request.headers.get('Authorization'));
          csrf.push(request.headers.get('X-CSRF-Token'));
          keys.push(request.headers.get('Idempotency-Key') ?? '');
          expect(request.headers.get('If-Match')).toBe('W/"holdout:4"');
          return HttpResponse.json({
            job_id: `JOB-${crypto.randomUUID()}`,
            status: 'QUEUED',
            progress: {
              mode: 'NONE',
              completed_units: null,
              total_units: null,
              unit: null,
              percent: null,
              current_step_key: null,
              current_step_label: null,
            },
            resource_ref: null,
            created_at: '2026-01-01T00:00:00Z',
          });
        },
      ),
    );
    auth.establish(ownerSession('KEY-1', 'csrf-1'));
    await api.runHoldout('VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', 'W/"holdout:4"', {
      approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
    });
    auth.establish(ownerSession('KEY-2', 'csrf-2'));
    await Promise.all([
      api.runHoldout('VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', 'W/"holdout:4"', {
        approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
      }),
      api.runHoldout('VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', 'W/"holdout:4"', {
        approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
      }),
    ]);
    expect(authorization).toEqual([null, null, null]);
    expect(csrf).toEqual(['csrf-1', 'csrf-2', 'csrf-2']);
    expect(new Set(keys).size).toBe(3);
    expect(keys.every(Boolean)).toBe(true);
  });

  it('posts canonical EXACT reproduce and rejects mismatched Location lineage', async () => {
    server.use(
      http.post(
        `${base}/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ/reproduce`,
        async ({ request }) => {
          expect(request.headers.get('Idempotency-Key')).toBe('REPRODUCE-INTENT-1');
          expect(await request.json()).toEqual({ mode: 'EXACT' });
          return HttpResponse.json(
            {
              job_id: 'JOB-53SPCRPW8DABZSX1MZY551DHWF',
              status: 'QUEUED',
              progress: {
                mode: 'NONE',
                completed_units: null,
                total_units: null,
                unit: null,
                percent: null,
                current_step_key: null,
                current_step_label: null,
              },
              resource_ref: {
                type: 'experiment',
                id: 'EXP-41JM536P4NGX0WHHTHVFZGPFVB',
                version: null,
                revision: 1,
              },
              source_experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
              source_provenance: { provenance_id: 'PROV-5C09CNJ1HB51GMZ29VSV9KK8NM' },
              reproduce_mode: 'EXACT',
              created_at: '2026-08-10T02:00:00Z',
            } satisfies Schema<'ExperimentReproduceAccepted'>,
            {
              status: 202,
              headers: { Location: '/api/v1/experiments/EXP-16G0GVD7YEQ71MQXBCGX1R7P09' },
            },
          );
        },
      ),
    );

    await expect(
      api.reproduceExperiment(
        'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
        { mode: 'EXACT' },
        'REPRODUCE-INTENT-1',
      ),
    ).rejects.toThrow('Reproduce Location or lineage does not match');
  });

  it('accepts explicit EXACT and all three controlled reproduce overrides only on HTTP 202', async () => {
    const received: unknown[] = [];
    let responseStatus = 202;
    server.use(
      http.post(
        `${base}/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ/reproduce`,
        async ({ request }) => {
          const body = await request.json();
          received.push(body);
          const mode =
            (body as { mode?: string }).mode === 'CONTROLLED_OVERRIDE'
              ? 'CONTROLLED_OVERRIDE'
              : 'EXACT';
          const acceptedIds = [
            'EXP-71H3WFBVC6Q951EGTPH30V511H',
            'EXP-5KRA9DBWKB97YSNVGPVZA2GP9X',
            'EXP-6VSXK4JYZ68KABY4XSWZ9MTNQD',
            'EXP-4P36Q6N0XJZ9DYTC98WDES2HTG',
          ] as const;
          const jobIds = [
            'JOB-56D0P46J719PSN3R3RPM9HZTAM',
            'JOB-2S8JHC91CK3R0NKX15T6PYVMWE',
            'JOB-4TKZAW16F5YJDE90SKRB8GX2CP',
            'JOB-1NV6QDYEFP4ZTCW3HJK7M8RXSA',
          ] as const;
          const acceptedId = acceptedIds[received.length - 1]!;
          return HttpResponse.json(
            {
              job_id: jobIds[received.length - 1]!,
              status: 'QUEUED',
              progress: {
                mode: 'NONE',
                completed_units: null,
                total_units: null,
                unit: null,
                percent: null,
                current_step_key: null,
                current_step_label: null,
              },
              resource_ref: {
                type: 'experiment',
                id: acceptedId,
                version: null,
                revision: 1,
              },
              source_experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
              source_provenance: { provenance_id: 'PROV-5C09CNJ1HB51GMZ29VSV9KK8NM' },
              reproduce_mode: mode,
              created_at: '2026-08-10T02:00:00Z',
            } satisfies Schema<'ExperimentReproduceAccepted'>,
            {
              status: responseStatus,
              headers: {
                Location: `/api/v1/experiments/${acceptedId}`,
              },
            },
          );
        },
      ),
    );
    await api.reproduceExperiment('EXP-4B0ZYVEPMH387DV8TG6244X6NZ', { mode: 'EXACT' }, 'KEY-EXACT');
    await api.reproduceExperiment(
      'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
      {
        mode: 'CONTROLLED_OVERRIDE',
        execution_overrides: {
          engine_version: '2.0.0',
          adapter_version: '3.0.0',
          code_version: 'commit-2',
        },
        reason: 'Compare all approved execution versions.',
      },
      'KEY-OVERRIDE',
    );
    expect(received).toEqual([
      { mode: 'EXACT' },
      {
        mode: 'CONTROLLED_OVERRIDE',
        execution_overrides: {
          engine_version: '2.0.0',
          adapter_version: '3.0.0',
          code_version: 'commit-2',
        },
        reason: 'Compare all approved execution versions.',
      },
    ]);
    responseStatus = 200;
    await expect(
      api.reproduceExperiment(
        'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
        { mode: 'EXACT' },
        'KEY-WRONG-STATUS',
      ),
    ).rejects.toThrow('Reproduce must return HTTP 202');
  });

  it.each([
    [401, 'UNAUTHENTICATED'],
    [403, 'PERMISSION_DENIED'],
    [404, 'RESOURCE_NOT_FOUND'],
    [409, 'IDEMPOTENCY_CONFLICT'],
    [409, 'IDEMPOTENCY_IN_PROGRESS'],
    [422, 'INVALID_REQUEST'],
    [429, 'MULTIPLE_TESTING_LIMIT_REACHED'],
  ] as const)('surfaces reproduce Problem %i/%s without client replay', async (status, code) => {
    let calls = 0;
    server.use(
      http.post(`${base}/api/v1/experiments/EXP-0VAHT8C2J3KAX71AF6P3J6ES5J/reproduce`, () => {
        calls += 1;
        return HttpResponse.json(
          {
            type: 'about:blank',
            title: code,
            status,
            code,
            detail: 'Canonical reproduce rejection.',
            instance: null,
            request_id: `REQ-${status}`,
            retryable: false,
            field_errors: [],
            context: {},
          },
          { status },
        );
      }),
    );
    auth.establish(ownerSession());
    await expect(
      api.reproduceExperiment('EXP-0VAHT8C2J3KAX71AF6P3J6ES5J', { mode: 'EXACT' }, `KEY-${status}`),
    ).rejects.toSatisfy(
      (error: unknown) => error instanceof ApiError && error.problem.code === code,
    );
    expect(calls).toBe(1);
    expect(auth.get()).toBe(status === 401 ? '' : 'session');
  });

  it('retains canonical error codes and request audit identity', async () => {
    server.use(
      http.get(`${base}/api/v1/approvals/APR-0T71YPB60APYFY39FY75RYTVZB`, () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'stale',
            status: 409,
            code: 'APPROVAL_STALE',
            detail: null,
            instance: null,
            request_id: 'req-123',
            retryable: false,
            field_errors: [],
            context: {},
          },
          { status: 409 },
        ),
      ),
    );
    await expect(api.approval('APR-0T71YPB60APYFY39FY75RYTVZB')).rejects.toSatisfy(
      (error: unknown) =>
        error instanceof ApiError &&
        error.problem.request_id === 'req-123' &&
        errorCopy[error.problem.code] === 'The approval is stale; review the latest state.',
    );
  });

  it('clears in-memory authentication on canonical 401', async () => {
    server.use(
      http.get(`${base}/api/v1/overview`, () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Unauthenticated',
            status: 401,
            code: 'UNAUTHENTICATED',
            detail: 'Token expired.',
            instance: null,
            request_id: 'REQ-AUTH-EXPIRED',
            retryable: false,
            field_errors: [],
            context: {},
          },
          { status: 401 },
        ),
      ),
    );
    auth.set('expired-token');
    await expect(api.overview()).rejects.toSatisfy(
      (error: unknown) => error instanceof ApiError && error.problem.status === 401,
    );
    expect(auth.get()).toBe('');
  });

  it('surfaces locked holdout 403 without decoding protected result fields', async () => {
    server.use(
      http.get(`${base}/api/v1/validations/VAL-70JTDFBF8N5AQ1CE7NF0KMHCT3/holdout/result`, () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Forbidden',
            status: 403,
            code: 'HOLDOUT_RESULT_FORBIDDEN',
            detail: 'Result remains protected.',
            instance: null,
            request_id: 'REQ-LOCKED',
            retryable: false,
            field_errors: [],
            context: { validation_id: 'VAL-70JTDFBF8N5AQ1CE7NF0KMHCT3' },
          },
          { status: 403 },
        ),
      ),
    );
    await expect(api.holdoutResult('VAL-70JTDFBF8N5AQ1CE7NF0KMHCT3')).rejects.toSatisfy(
      (error: unknown) =>
        error instanceof ApiError && error.problem.code === 'HOLDOUT_RESULT_FORBIDDEN',
    );
  });

  it('does not replay stale approval and agent precondition mutations', async () => {
    let approvalCalls = 0;
    let agentCalls = 0;
    server.use(
      http.post(
        `${base}/api/v1/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M/approve`,
        ({ request }) => {
          approvalCalls += 1;
          expect(request.headers.get('If-Match')).toBe('W/"approval:4"');
          expect(request.headers.get('Idempotency-Key')).toBeTruthy();
          return HttpResponse.json(
            {
              type: 'about:blank',
              title: 'Approval stale',
              status: 409,
              code: 'APPROVAL_STALE',
              detail: null,
              instance: null,
              request_id: 'REQ-APR-4F2AZ2JW99QY7PGMQJ9X3T500M',
              retryable: false,
              field_errors: [],
              context: { approval_id: 'APR-4F2AZ2JW99QY7PGMQJ9X3T500M' },
            },
            { status: 409 },
          );
        },
      ),
      http.put(`${base}/api/v1/agents/RESEARCH_DIRECTOR/config`, ({ request }) => {
        agentCalls += 1;
        expect(request.headers.get('If-Match')).toBe('W/"agent:4"');
        return HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Precondition required',
            status: 428,
            code: 'PRECONDITION_REQUIRED',
            detail: null,
            instance: null,
            request_id: 'REQ-AGENT-428',
            retryable: false,
            field_errors: [],
            context: {},
          },
          { status: 428 },
        );
      }),
    );
    await expect(
      api.approveApproval('APR-4F2AZ2JW99QY7PGMQJ9X3T500M', 'W/"approval:4"', {
        acknowledged_subject_sha256: 'a'.repeat(64),
      }),
    ).rejects.toSatisfy(
      (error: unknown) => error instanceof ApiError && error.problem.code === 'APPROVAL_STALE',
    );
    await expect(
      api.updateAgent('RESEARCH_DIRECTOR', 'W/"agent:4"', { enabled: false }),
    ).rejects.toSatisfy(
      (error: unknown) =>
        error instanceof ApiError && error.problem.code === 'PRECONDITION_REQUIRED',
    );
    expect({ approvalCalls, agentCalls }).toEqual({ approvalCalls: 1, agentCalls: 1 });
  });

  it('SSE isolates cursor and dedupe state across owner sessions', async () => {
    let calls = 0;
    const events: Schema<'SseEnvelope'>[] = [];
    const resync = vi.fn();
    const workspaceAJob = 'JOB-73MTX6YMDRFAZNRRNVCQDSQYH8';
    const workspaceBJob = 'JOB-0QAJSVRMV1KQSB49YFQHZJ72JK';
    const envelope = (
      sequence: number,
      eventType: Schema<'EventType'> = 'job.updated',
      payload = '{}',
      jobId = workspaceAJob,
    ) => {
      const objectType = EventTypeObjectTypeMap[eventType];
      const locator = EventObjectExamples[objectType];
      return `id: ${sequence}\ndata: ${JSON.stringify({
        schema_version: 1,
        event_id: 'EVT-7BSW7QFNPFN7FGSNW2WW07V82M',
        sequence,
        event_type: eventType,
        occurred_at: '2026-01-01T00:00:00Z',
        object_type: objectType,
        ...locator,
        object_id: objectType === 'job' ? jobId : locator.object_id,
        request_id: null,
        job_id: objectType === 'job' ? jobId : null,
        agent_run_id: null,
        tool_call_id: null,
        payload: JSON.parse(payload),
      })}\n\n`;
    };
    auth.establish(ownerSession('KEY-A', 'csrf-a'));
    const workspaceAScope = auth.scope();
    server.use(
      http.get(`${base}/api/v1/events/stream`, ({ request }) => {
        calls += 1;
        if (calls === 2) {
          expect(request.headers.get('Last-Event-ID')).toBeNull();
          expect(request.headers.get('Authorization')).toBeNull();
          expect(request.credentials).toBe('include');
        }
        const body =
          calls === 1
            ? envelope(7) +
              envelope(7) +
              envelope(6) +
              envelope(9) +
              envelope(10, 'system.resync_required', '{"resync_from_sequence":7}') +
              envelope(11, 'validation.holdout.updated', '{"metrics":[{"secret":true}]}')
            : envelope(7, 'job.updated', '{}', workspaceBJob);
        return new HttpResponse(body, { headers: { 'Content-Type': 'text/event-stream' } });
      }),
    );
    const stop = streamEvents((event) => events.push(event), resync);
    await vi.waitFor(() => expect(events.map((e) => e.sequence)).toEqual([7, 9]));
    expect(resync.mock.calls.length).toBeGreaterThanOrEqual(3);
    expect(sessionStorage.getItem(`qf.sse.cursor:${workspaceAScope}`)).toBe('10');
    auth.establish(ownerSession('KEY-B', 'csrf-b'));
    const workspaceBScope = auth.scope();
    expect(workspaceBScope).not.toBe(workspaceAScope);
    expect(sessionStorage.getItem(`qf.sse.cursor:${workspaceAScope}`)).toBeNull();
    await vi.waitFor(() => expect(events.map((event) => event.sequence)).toEqual([7, 9, 7]));
    expect(events.at(-1)?.object_id).toBe(workspaceBJob);
    expect(queryKeysForEvent(events.at(-1)!)).toContainEqual([
      workspaceBScope,
      'job',
      workspaceBJob,
    ]);
    expect(queryKeysForEvent(events.at(-1)!)).not.toContainEqual([
      workspaceAScope,
      'job',
      workspaceAJob,
    ]);
    stop();
  });

  it('SSE cases 04-07/12/16 fail closed and stop reconnect after persistent contract skew', async () => {
    let calls = 0;
    const events: Schema<'SseEnvelope'>[] = [];
    const states: string[] = [];
    const resync = vi.fn();
    const baseEnvelope = {
      schema_version: 1,
      event_id: 'EVT-7BSW7QFNPFN7FGSNW2WW07V82M',
      sequence: 1,
      event_type: 'experiment.updated',
      occurred_at: '2026-08-10T00:00:00Z',
      object_type: 'experiment',
      object_id: 'EXP-1CAT5P1NQA50TNSWXQRD3ZJF6G',
      object_version: null,
      object_revision: 1,
      request_id: null,
      job_id: null,
      agent_run_id: null,
      tool_call_id: null,
      payload: {},
    } satisfies Schema<'SseEnvelope'>;
    server.use(
      http.get(`${base}/api/v1/events/stream`, () => {
        calls += 1;
        const frames = [
          { ...baseEnvelope, event_type: 'experiment.future_completed' },
          {
            ...baseEnvelope,
            event_id: 'EVT-4V9MRDSPQPS3YCZXZ34PBT306X',
            sequence: 2,
            schema_version: 2,
          },
          {
            ...baseEnvelope,
            event_id: 'EVT-2MVNBFRCR3VPGS5KQKF2F77FS7',
            sequence: 3,
            event_type: 'validation.holdout.updated',
            payload: { metric: 'sharpe', value: '9.99' },
          },
        ];
        return new HttpResponse(
          frames
            .map((frame) => `id: ${frame.sequence}\ndata: ${JSON.stringify(frame)}\n\n`)
            .join(''),
          { headers: { 'Content-Type': 'text/event-stream' } },
        );
      }),
    );
    const stop = streamEvents(
      (event) => events.push(event),
      resync,
      (state) => states.push(state),
    );
    await vi.waitFor(() => expect(states).toContain('client-update-required'));
    expect(resync).toHaveBeenCalledTimes(3);
    expect(events).toEqual([]);
    expect(sessionStorage.getItem('qf.sse.cursor')).toBeNull();
    await new Promise((resolve) => window.setTimeout(resolve, 25));
    expect(calls).toBe(1);
    stop();
  });

  it('stops SSE retry and clears in-memory auth on canonical 401', async () => {
    let calls = 0;
    const states: string[] = [];
    const problems: ApiError[] = [];
    server.use(
      http.get(`${base}/api/v1/events/stream`, () => {
        calls += 1;
        return HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Unauthenticated',
            status: 401,
            code: 'UNAUTHENTICATED',
            detail: 'Session expired.',
            instance: null,
            request_id: 'REQ-SSE-401',
            retryable: false,
            field_errors: [],
            context: {},
          },
          { status: 401 },
        );
      }),
    );
    auth.establish(ownerSession('KEY-EXPIRED', 'csrf-expired'));
    const stop = streamEvents(
      vi.fn(),
      vi.fn(),
      (state) => states.push(state),
      (error) => problems.push(error),
    );
    await vi.waitFor(() => expect(problems).toHaveLength(1));
    expect(problems[0]?.problem.request_id).toBe('REQ-SSE-401');
    expect(states).toContain('reauthentication-required');
    expect(auth.get()).toBe('');
    await new Promise((resolve) => window.setTimeout(resolve, 25));
    expect(calls).toBe(1);
    stop();
  });

  it('stops SSE retry but preserves auth on canonical 403', async () => {
    let calls = 0;
    const states: string[] = [];
    const problems: ApiError[] = [];
    server.use(
      http.get(`${base}/api/v1/events/stream`, () => {
        calls += 1;
        return HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Forbidden',
            status: 403,
            code: 'PERMISSION_DENIED',
            detail: 'Stream scope denied.',
            instance: null,
            request_id: 'REQ-SSE-403',
            retryable: false,
            field_errors: [],
            context: {},
          },
          { status: 403 },
        );
      }),
    );
    auth.establish(ownerSession('KEY-AUTHORIZED', 'csrf-authorized'));
    const stop = streamEvents(
      vi.fn(),
      vi.fn(),
      (state) => states.push(state),
      (error) => problems.push(error),
    );
    await vi.waitFor(() => expect(problems).toHaveLength(1));
    expect(problems[0]?.problem.request_id).toBe('REQ-SSE-403');
    expect(states).toContain('permission-denied');
    expect(auth.get()).toBe('session');
    await new Promise((resolve) => window.setTimeout(resolve, 25));
    expect(calls).toBe(1);
    stop();
  });
});
