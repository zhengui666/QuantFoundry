import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page, type Route } from 'playwright/test';
import type { Schema } from '../src/api/client';
import {
  canonicalEngineFixtures,
  experimentProjection,
  researchProjection,
  strategyProjection,
} from './fixture-builders';

const capability = (action: string): Schema<'ActionCapability'> => ({
  action,
  visibility: 'SHOW',
  allowed: true,
  reason_code: null,
  reason_detail: null,
  requires_confirmation: true,
  idempotency_required: true,
  if_match_required: true,
  result_mode: 'IMMEDIATE',
  danger_level: 'STATE_CHANGE',
});

const progress = {
  mode: 'UNITS',
  completed_units: 4,
  total_units: 10,
  unit: 'experiments',
  percent: 40,
  current_step_key: 'test',
  current_step_label: 'Testing',
} satisfies Schema<'JobProgress'>;

const overview = {
  as_of: '2026-08-10T02:00:00Z',
  revision: 8,
  needs_attention: [],
  active_research: [
    {
      research_id: 'RSCH-10QAK5KS1BPEVRRDDZR68QTGCV',
      title: 'Visual research',
      status: 'RUNNING',
      evidence_status: 'MIXED',
      progress,
      current_agent: { role: 'FACTOR_SCIENTIST', agent_run_id: 'ARUN-7K6RZ6X2QVX09P3N3T427E417A' },
      revision: 2,
      action_capabilities: [],
      updated_at: '2026-08-10T01:00:00Z',
    },
  ],
  strategy_pipeline: { candidate: 1, frozen: 2, validating: 1, validated: 4, paper: 1 },
  paper_summary: {
    active_count: 1,
    total_nav: '104000',
    currency: 'USD',
    daily_return: '0.01',
    mtd_return: '0.03',
    since_start_return: '0.04',
    benchmark_since_start_return: '0.02',
    as_of_date: '2026-08-09',
    provenance: { provenance_id: 'PROV-70Z4DHXM4HQYPD84CTHRQT2T8N' },
  },
  paper_performance_chart: {
    schema_version: 1,
    chart_id: 'CHART-V',
    chart_type: 'EQUITY_CURVE',
    metric_key: 'nav',
    x_axis: { kind: 'TIME', timezone: 'UTC' },
    series: [
      {
        series_id: 'SER-V',
        series_key: 'portfolio_nav',
        display_label: 'Portfolio NAV',
        unit: 'USD',
        value_format: { kind: 'CURRENCY', precision: 2 },
        points: [
          { x: '2026-08-01', y: '100000' },
          { x: '2026-08-03', y: '101500' },
          { x: '2026-08-05', y: null },
          { x: '2026-08-07', y: '103000' },
          { x: '2026-08-09', y: '104000' },
        ],
      },
    ],
    period_markers: [
      { period_type: 'PAPER', start: '2026-08-01', end: '2026-08-09', state: 'EXPOSED' },
      { period_type: 'HOLDOUT', start: '2026-08-05', end: '2026-08-06', state: 'LOCKED' },
    ],
    assumptions: [{ key: 'currency', value: 'USD', unit: null }],
    summary: {
      template_key: 'chart.equity_curve.summary',
      params: { ending_nav: '104000', benchmark_ending_nav: '102000' },
    },
    downsampling: { applied: true, source_points: 2000, returned_points: 5, method: 'LTTB' },
    provenance: { provenance_id: 'PROV-3C0F9NE55ENKTXGQZ10FKYBMVD' },
    generated_at: '2026-08-10T02:00:00Z',
  },
  recent_findings: [
    {
      finding_id: 'FIND-V',
      evidence_status: 'SUPPORTIVE',
      finding: 'Evidence remains stable.',
      research: {
        type: 'research',
        id: 'RSCH-10QAK5KS1BPEVRRDDZR68QTGCV',
        version: null,
        revision: 2,
      },
      provenance: { provenance_id: 'PROV-72FKFV4QMJSN15BWNQR56E1J62' },
      updated_at: '2026-08-10T01:30:00Z',
    },
  ],
  agent_activity: [
    {
      agent_run_id: 'ARUN-7K6RZ6X2QVX09P3N3T427E417A',
      role: 'FACTOR_SCIENTIST',
      objective: 'Validate evidence',
      status: 'RUNNING',
      decision_summary: null,
      next_action: 'Complete tests',
      updated_at: '2026-08-10T01:40:00Z',
    },
  ],
  data_health: {
    state: 'HEALTHY',
    blocker_count: 0,
    warning_count: 0,
    checked_at: '2026-08-10T01:50:00Z',
    action_capabilities: [],
  },
  provenance: [{ provenance_id: 'PROV-70Z4DHXM4HQYPD84CTHRQT2T8N' }],
  action_capabilities: [],
} satisfies Schema<'OverviewReadModel'>;

const decimalChart = {
  ...overview.paper_performance_chart,
  series: [
    {
      ...overview.paper_performance_chart.series[0]!,
      value_format: { kind: 'CURRENCY', precision: 18 },
      points: [
        { x: '2026-08-01', y: '9007199254740993.12' },
        { x: '2026-08-03', y: '-12345678901234567890.123456789012345678' },
        { x: '2026-08-05', y: null },
        { x: '2026-08-07', y: '1.234567890123456789e-3' },
        { x: '2026-08-09', y: 'not-a-decimal' },
      ],
    },
  ],
  assumptions: [{ key: 'currency', value: '-1.2300e+2', unit: 'USD' }],
  summary: {
    template_key: 'chart.equity_curve.summary',
    params: {
      ending_nav: '9007199254740993.1200',
      benchmark_ending_nav: '-12345678901234567890.123456789012345678',
    },
  },
} satisfies Schema<'ChartAggregate'>;

const research = {
  research_id: 'RSCH-10QAK5KS1BPEVRRDDZR68QTGCV',
  title: 'Visual research',
  original_user_prompt: 'Does quality persist after costs?',
  normalized_question: 'Does quality persist after costs?',
  status: 'RUNNING',
  evidence_status: 'MIXED',
  current_revision_no: 2,
  active_plan_version: 1,
  research_policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
  director_agent_version: '1.0.0',
  current_agent_run_id: 'ARUN-7K6RZ6X2QVX09P3N3T427E417A',
  current_job_id: 'JOB-6YKPDNE04XR0MTQEH00YFVNZ31',
  ...researchProjection(true),
  revision: 2,
  action_capabilities: [],
  created_at: '2026-08-09T00:00:00Z',
  updated_at: '2026-08-10T01:00:00Z',
  completed_at: null,
} satisfies Schema<'ResearchDetail'>;

const experimentProvenance = {
  provenance_id: 'PROV-4B6866SF8D8VPTTJSV3JFVVEPS',
  schema_version: 1,
  experiment_id: 'EXP-6HASHPMWTVXN1E1KFT7YMMBE17',
  source_experiment_id: null,
  tool_call_id: 'TCALL-4W7DQE7QPCNW0QMN4MFK5ZRM6Y',
  data_snapshot_ids: ['DS-0K42SZRCB6QD40WD6R2D2C9PFG'],
  engine: { name: 'factor-engine', version: '1.0.0' },
  adapter: { name: 'market-adapter', version: '1.0.0' },
  code: { commit: 'abc123', build_id: 'build-v' },
  policies: [{ type: 'research_policy', id: 'RP-756FFQA659A84RCEVR0M9X8DMN', version: 1 }],
  strategy: null,
  factors: [],
  cost_model: { id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF', version: 1, sha256: 'c'.repeat(64) },
  parameters_sha256: 'a'.repeat(64),
  input_sha256: 'b'.repeat(64),
  output_sha256: 'd'.repeat(64),
  calculated_at: '2026-08-10T01:00:00Z',
} satisfies Schema<'Provenance'>;

const experiment = {
  experiment_id: 'EXP-6HASHPMWTVXN1E1KFT7YMMBE17',
  research_id: 'RSCH-10QAK5KS1BPEVRRDDZR68QTGCV',
  parent_experiment_id: null,
  source_experiment_id: null,
  research_revision_no: 2,
  objective: 'Measure quality persistence.',
  hypothesis: 'Quality remains positive after costs.',
  experiment_type: 'PARAMETER_SENSITIVITY',
  status: 'COMPLETED',
  validity_state: 'VALID',
  data_snapshot_id: 'DS-0K42SZRCB6QD40WD6R2D2C9PFG',
  factor_ref: { id: 'FAC-0WP55AJ610HQB62MPM0X6KJ9XE', version: 1 },
  strategy_ref: null,
  cost_model_id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF',
  parameters: [{ key: 'lookback', value: '252' }],
  parameters_sha256: 'a'.repeat(64),
  ...experimentProjection,
  engine: { name: 'factor-engine', version: '1.0.0' },
  adapter: { name: 'market-adapter', version: '1.0.0' },
  code_version: 'abc123',
  job_id: 'JOB-6YKPDNE04XR0MTQEH00YFVNZ31',
  provenance: experimentProvenance,
  action_capabilities: [],
  started_at: '2026-08-10T00:00:00Z',
  finished_at: '2026-08-10T01:00:00Z',
  created_at: '2026-08-10T00:00:00Z',
  invalidated_at: null,
  invalid_reason_code: null,
  invalid_reason_detail: null,
} satisfies Schema<'ExperimentDetail'>;

const strategySpecification = {
  thesis: 'Persistent quality with measured momentum.',
  universe: { asset_class: 'EQUITY', symbols: ['SPY', 'QQQ'], universe_id: null },
  signals: [
    {
      factor_id: 'FAC-701PW0JDPSYYMVWDY210EKMTVQ',
      factor_version: 2,
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
  known_failure_modes: ['Crowded unwind'],
  spec_sha256: 'a'.repeat(64),
} satisfies Parameters<typeof strategyProjection>[0];

const strategy = {
  strategy_id: 'STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP',
  name: 'Quality momentum',
  version: 4,
  lifecycle_state: 'FROZEN',
  is_frozen: true,
  ...strategySpecification,
  ...strategyProjection(strategySpecification),
  latest_backtest: {
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
      job_id: 'JOB-6YKPDNE04XR0MTQEH00YFVNZ31',
      provenance: { provenance_id: 'PROV-4B6866SF8D8VPTTJSV3JFVVEPS' },
      started_at: '2026-08-10T00:00:00Z',
      finished_at: '2026-08-10T01:00:00Z',
    },
    metrics: [{ key: 'sharpe', value: '1.25', unit: null }],
    chart: overview.paper_performance_chart,
  },
  validation_summary: {
    validation: {
      type: 'validation',
      id: 'VAL-03H10KRA33F1P8NDA3XEFHKT33',
      version: null,
      revision: 3,
    },
    status: 'COMPLETED',
    result: 'FAIL',
    holdout_state: 'LOCKED',
    test_counts: { pending: 0, running: 0, pass: 3, warn: 1, fail: 1, locked: 1, skipped: 0 },
    provenance: { provenance_id: 'PROV-5M85G0E30D079AZ7WRS6VR51V9' },
    revision: 3,
  },
  frozen_at: '2026-08-10T00:00:00Z',
  frozen_by: 'owner',
  revision: 5,
  action_capabilities: [],
  created_at: '2026-08-09T00:00:00Z',
} satisfies Schema<'StrategyVersionDetail'>;

const validation = {
  validation_id: 'VAL-03H10KRA33F1P8NDA3XEFHKT33',
  strategy: { id: 'STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP', version: 4 },
  policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
  strict_engine: {
    name: canonicalEngineFixtures.strictValidation.strict_engine_key,
    version: canonicalEngineFixtures.strictValidation.strict_engine_version,
  },
  status: 'COMPLETED',
  result: 'FAIL',
  test_suite_version: '1',
  tests: [
    {
      test_key: 'stability',
      attempt_no: 1,
      test_version: '1',
      state: 'FAIL',
      purpose: 'Parameter stability',
      configuration_summary: 'Neighboring parameters',
      calculated_result: 'Threshold missed',
      interpretation: 'Narrow stability region',
      failure_code: 'VALIDATION_FAILED',
      failure_detail: 'Mandatory test failed.',
      warning_codes: [],
      artifact_ids: [],
      provenance: null,
      override_permitted: false,
    },
  ],
  warnings: [],
  failures: ['stability'],
  holdout_state: 'LOCKED',
  red_team_run_id: null,
  job_id: null,
  revision: 3,
  action_capabilities: [],
  started_at: '2026-08-10T00:00:00Z',
  finished_at: '2026-08-10T01:00:00Z',
  created_at: '2026-08-10T00:00:00Z',
} satisfies Schema<'ValidationDetail'>;

const approval = {
  approval_id: 'APR-15EKXBZCVW4DYG2QK0MQX03X0R',
  type: 'HOLDOUT_UNLOCK',
  subject: {
    type: 'VALIDATION',
    id: 'VAL-03H10KRA33F1P8NDA3XEFHKT33',
    version: 4,
    revision: 3,
    sha256: 'b'.repeat(64),
  },
  requester: { type: 'OWNER', id: 'owner' },
  reason: 'Expose final holdout once.',
  prerequisites: [{ key: 'strict_validation', state: 'PASS', detail: 'Passed' }],
  risk_summary: { risk_level: 'HIGH', warning_codes: [] },
  effects: [{ code: 'EXPOSE_HOLDOUT', detail: 'Exposure count increments.' }],
  status: 'PENDING',
  requested_at: '2026-08-10T00:00:00Z',
  decided_at: null,
  revision: 3,
  action_capabilities: [capability('approve'), capability('reject')],
} satisfies Schema<'ApprovalDetail'>;

const agent = {
  role_key: 'RESEARCH_DIRECTOR',
  enabled: true,
  model_provider: 'openai',
  model_name: 'gpt-test',
  ai_connection_id: 'CODEX-DEFAULT',
  ai_connection_revision: 1,
  runtime_profile: 'default',
  tool_timeout_seconds: 60,
  max_steps_override: null,
  max_tool_calls_override: null,
  revision: 3,
  action_capabilities: [capability('update_agent_config')],
  created_at: '2026-08-10T00:00:00Z',
  updated_at: '2026-08-10T00:00:00Z',
} satisfies Schema<'AgentConfig'>;

async function mockCanonicalApi(
  page: Page,
  chart: Schema<'ChartAggregate'> = overview.paper_performance_chart,
) {
  const overviewResponse = { ...overview, paper_performance_chart: chart };
  const strategyResponse = {
    ...strategy,
    latest_backtest: { ...strategy.latest_backtest, chart },
  };
  await page.route('**/api/v1/**', (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === '/api/v1/auth/session')
      return route.fulfill({
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
    if (path === '/api/v1/events/stream')
      return route.fulfill({ contentType: 'text/event-stream', body: '' });
    if (path === '/api/v1/overview') return route.fulfill({ json: overviewResponse });
    if (path === '/api/v1/research/RSCH-10QAK5KS1BPEVRRDDZR68QTGCV')
      return route.fulfill({ json: research, headers: { ETag: 'W/"research:2"' } });
    if (path === '/api/v1/experiments/EXP-6HASHPMWTVXN1E1KFT7YMMBE17')
      return route.fulfill({ json: experiment, headers: { ETag: 'W/"experiment:1"' } });
    if (path === '/api/v1/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP/current-version')
      return route.fulfill({
        json: strategyResponse,
        headers: {
          ETag: 'W/"strategy:5"',
          'Content-Location': '/api/v1/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP/versions/4',
        },
      });
    if (path === '/api/v1/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP/versions/4')
      return route.fulfill({ json: strategyResponse, headers: { ETag: 'W/"strategy:5"' } });
    if (path === '/api/v1/validations/VAL-03H10KRA33F1P8NDA3XEFHKT33')
      return route.fulfill({ json: validation });
    if (path === '/api/v1/validations/VAL-03H10KRA33F1P8NDA3XEFHKT33/holdout')
      return route.fulfill({
        json: {
          validation_id: 'VAL-03H10KRA33F1P8NDA3XEFHKT33',
          state: 'LOCKED',
          exposure_count: 0,
          period: { start: '2023-01-01', end: '2025-12-31' },
          approval: null,
          action_capabilities: [],
          revision: 3,
        },
        headers: { ETag: 'W/"holdout:3"' },
      });
    if (path === '/api/v1/approvals/APR-15EKXBZCVW4DYG2QK0MQX03X0R')
      return route.fulfill({ json: approval, headers: { ETag: 'W/"approval:3"' } });
    if (path === '/api/v1/agents') return route.fulfill({ json: [agent] });
    if (path === '/api/v1/agents/RESEARCH_DIRECTOR/config')
      return route.fulfill({ json: agent, headers: { ETag: 'W/"agent:3"' } });
    return route.fulfill({ status: 404, json: {} });
  });
}

async function seedChartLocale(page: Page, language: 'en' | 'zh-CN') {
  await page.route('**/api/v1/configuration/active', (route) =>
    route.fulfill({
      headers: { ETag: 'W/"config:1"' },
      json: {
        active_revision: 1,
        last_known_good_revision: 1,
        catalog_version: 'UX001_D1_CATALOG_R1',
        values: [
          {
            key: 'appearance.locale',
            sensitivity: 'PUBLIC',
            configured: true,
            value: {
              language,
              timezone: 'UTC',
              number_format_locale: language === 'en' ? 'en-US' : 'zh-CN',
              theme: 'SYSTEM',
              density: 'COMFORTABLE',
            },
            masked_hint: null,
          },
        ],
        snapshot_sha256: '0'.repeat(64),
        consumer_states: [],
        updated_at: '2026-08-10T00:00:00Z',
      },
    }),
  );
}

async function verifyLocalizedChart(page: Page, language: 'en' | 'zh-CN') {
  const copy =
    language === 'en'
      ? {
          aria: 'Paper performance chart',
          summary:
            'Ending NAV 9,007,199,254,740,993.1200; benchmark -12,345,678,901,234,567,890.123456789012345678.',
          downsampling: /5 of 2,000 points shown using LTTB/,
          table: 'Chart data table',
          headers: ['Series', 'X', 'Y', 'Unit'],
          gap: 'Gap',
          unavailable: 'unavailable',
        }
      : {
          aria: '纸面业绩图表',
          summary:
            '期末净值 9,007,199,254,740,993.1200；基准 -12,345,678,901,234,567,890.123456789012345678。',
          downsampling: /显示 2,000 个数据点中的 5 个，方法为 LTTB/,
          table: '图表数据表',
          headers: ['序列', '横轴', '纵轴', '单位'],
          gap: '缺口',
          unavailable: '不可用',
        };
  await expect(page.getByRole('img', { name: copy.aria })).toBeVisible();
  await expect(page.locator('figcaption')).toContainText(copy.summary);
  await expect(page.getByText(copy.downsampling)).toBeVisible();
  await page.getByText(copy.table).click();
  const table = page.getByRole('table');
  for (const header of copy.headers)
    await expect(table.getByRole('columnheader', { name: header })).toBeVisible();
  for (const value of [
    '9,007,199,254,740,993.120000000000000000',
    '-12,345,678,901,234,567,890.123456789012345678',
    '0.001234567890123457',
    copy.gap,
    copy.unavailable,
  ])
    await expect(table.getByRole('cell', { name: value, exact: true })).toBeVisible();
  await expect(page.getByText(/-123\.00 USD/)).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.map((violation) => violation.id)).toEqual([]);
}

for (const [surface, path] of [
  ['P01', '/overview'],
  ['P09', '/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP?version=4&tab=backtests'],
] as const) {
  for (const language of ['en', 'zh-CN'] as const) {
    test(`${surface} chart exposes localized ${language} aria, summary, and text table`, async ({
      page,
    }) => {
      await mockCanonicalApi(page, decimalChart);
      await seedChartLocale(page, language);
      await page.goto(path);
      await verifyLocalizedChart(page, language);
    });
  }
}

const surfaces = [
  ['P01', '/overview'],
  ['P04', '/research/RSCH-10QAK5KS1BPEVRRDDZR68QTGCV?tab=overview'],
  ['P05', '/experiments/EXP-6HASHPMWTVXN1E1KFT7YMMBE17?tab=inputs'],
  ['P09', '/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP?version=4&tab=backtests'],
  ['P11', '/validation/VAL-03H10KRA33F1P8NDA3XEFHKT33'],
  ['P14', '/approvals/APR-15EKXBZCVW4DYG2QK0MQX03X0R'],
  ['P20', '/agents'],
] as const;

for (const width of [1440, 1280, 1180]) {
  for (const [surface, path] of surfaces) {
    test(`${surface} axe and visual at ${width}`, async ({ page }) => {
      await mockCanonicalApi(page);
      await page.setViewportSize({ width, height: 900 });
      await page.goto(path);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      await expect(page.getByRole('navigation', { name: /Primary|主导航/ })).toBeVisible();
      if (surface === 'P01' || surface === 'P09')
        await expect(page.locator('.chart canvas')).toBeVisible();
      if (width === 1180)
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1180);
      const accessibility = await new AxeBuilder({ page }).analyze();
      expect(accessibility.violations.map((violation) => violation.id)).toEqual([]);
      await expect(page).toHaveScreenshot(`${surface.toLowerCase()}-${width}.png`, {
        animations: 'disabled',
        fullPage: true,
        mask: surface === 'P01' ? [] : [page.locator('.topbar')],
        maskColor: '#e7eef3',
      });
    });
  }
}

for (const state of ['EMPTY', 'LOCKED'] as const) {
  test(`P09 ${state} closed boundary has no protected DOM and a11y visual`, async ({ page }) => {
    await mockCanonicalApi(page);
    await page.route('**/api/v1/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP/versions/4', (route) =>
      route.fulfill({
        json: {
          ...strategy,
          latest_backtest: { state, result: null, metrics: [], chart: null },
        } satisfies Schema<'StrategyVersionDetail'>,
        headers: { ETag: 'W/"strategy:5"' },
      }),
    );
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP?version=4&tab=backtests');
    await expect(
      page.getByText(
        state === 'EMPTY'
          ? /No canonical backtest|尚无 canonical 回测/
          : /information boundary|信息边界/,
      ),
    ).toBeVisible();
    await expect(page.getByText('1.25', { exact: false })).toHaveCount(0);
    await expect(page.locator('.chart')).toHaveCount(0);
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations.map((violation) => violation.id)).toEqual([]);
    await expect(page).toHaveScreenshot(`p09-${state.toLowerCase()}-1280.png`, {
      animations: 'disabled',
      fullPage: true,
      mask: [page.locator('.topbar')],
      maskColor: '#e7eef3',
    });
  });
}

test('P09 corrupt LOCKED payload fails closed before protected DOM exposure', async ({ page }) => {
  await mockCanonicalApi(page);
  await page.route('**/api/v1/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP/versions/4', (route) =>
    route.fulfill({
      json: {
        ...strategy,
        latest_backtest: {
          state: 'LOCKED',
          result: null,
          metrics: [{ key: 'protected_sharpe', value: '9.99', unit: 'ratio' }],
          chart: null,
        },
      },
    }),
  );
  await page.goto('/strategies/STRAT-7DM0RSF9KRZZ52QFV79PMX8YBP?version=4&tab=backtests');
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByText(/protected_sharpe|9\.99/)).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.map((violation) => violation.id)).toEqual([]);
});
