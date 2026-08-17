import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from 'playwright/test';
import type { Schema } from '../src/api/client';
import { canonicalEngineFixtures, readySetupStatus, strategyProjection } from './fixture-builders';

const capability = (
  action: string,
  allowed = true,
  requiresConfirmation = true,
): Schema<'ActionCapability'> => ({
  action,
  visibility: 'SHOW',
  allowed,
  reason_code: allowed ? null : 'HOLDOUT_LOCKED',
  reason_detail: allowed ? null : 'Locked by server policy',
  requires_confirmation: requiresConfirmation,
  idempotency_required: true,
  if_match_required: true,
  result_mode: 'IMMEDIATE',
  danger_level: 'STATE_CHANGE',
});

async function silenceEvents(page: Page) {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: '' }),
  );
}

const validation = {
  validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
  strategy: { id: 'STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', version: 4 },
  policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
  strict_engine: {
    name: canonicalEngineFixtures.strictValidation.strict_engine_key,
    version: canonicalEngineFixtures.strictValidation.strict_engine_version,
  },
  status: 'COMPLETED',
  result: 'FAIL',
  test_suite_version: '2026.1',
  tests: [
    {
      test_key: 'parameter_stability',
      attempt_no: 1,
      test_version: '1',
      state: 'FAIL',
      purpose: 'Verify parameter robustness',
      configuration_summary: '24 neighboring configurations',
      calculated_result: '11/24 failed',
      interpretation: 'Performance is concentrated in a narrow region.',
      failure_code: 'VALIDATION_FAILED',
      failure_detail: 'Mandatory robustness threshold missed.',
      warning_codes: [],
      artifact_ids: ['ART-6C7M8NEP8K5HFEMKK0Q7DRNWKQ'],
      provenance: { provenance_id: 'PROV-0KAGD73GB3Z2AKJ4RRCBCKZFZG' },
      override_permitted: false,
    },
  ],
  warnings: [],
  failures: ['parameter_stability'],
  holdout_state: 'LOCKED',
  red_team_run_id: null,
  job_id: null,
  revision: 3,
  action_capabilities: [
    capability('return_to_research', true, false),
    capability('view_strategy', true, false),
  ],
  started_at: '2026-08-10T01:00:00Z',
  finished_at: '2026-08-10T02:00:00Z',
  created_at: '2026-08-10T00:00:00Z',
} satisfies Schema<'ValidationDetail'>;

const overview = {
  as_of: '2026-08-10T02:00:00Z',
  revision: 8,
  needs_attention: [],
  active_research: [
    {
      research_id: 'RSCH-7ZB18YZVDQZ6QCPE22E86T0AMK',
      title: 'Quality momentum research',
      status: 'RUNNING',
      evidence_status: 'SUPPORTIVE',
      progress: {
        mode: 'UNITS',
        completed_units: 12,
        total_units: 20,
        unit: 'experiments',
        percent: 60,
        current_step_key: 'backtest',
        current_step_label: 'Backtesting',
      },
      current_agent: { role: 'FACTOR_SCIENTIST', agent_run_id: 'ARUN-568XYY4RMECVTXTGGJKREHDW37' },
      revision: 2,
      action_capabilities: [capability('open_research')],
      updated_at: '2026-08-10T01:00:00Z',
    },
  ],
  strategy_pipeline: { candidate: 1, frozen: 2, validating: 1, validated: 4, paper: 1 },
  paper_summary: {
    active_count: 1,
    total_nav: '104000.00',
    currency: 'USD',
    daily_return: '0.01',
    mtd_return: '0.03',
    since_start_return: '0.04',
    benchmark_since_start_return: '0.02',
    as_of_date: '2026-08-09',
    provenance: { provenance_id: 'PROV-1VQMSE365J6REYKWJ5VA5H0W35' },
  },
  paper_performance_chart: {
    schema_version: 1,
    chart_id: 'CHART-1',
    chart_type: 'EQUITY_CURVE',
    metric_key: 'nav',
    x_axis: { kind: 'TIME', timezone: 'UTC' },
    series: [
      {
        series_id: 'SER-1',
        series_key: 'portfolio_nav',
        display_label: 'Portfolio NAV',
        unit: 'USD',
        value_format: { kind: 'CURRENCY', precision: 2 },
        points: [
          { x: '2026-08-01', y: '100000' },
          { x: '2026-08-05', y: null },
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
    downsampling: { applied: true, source_points: 2000, returned_points: 3, method: 'LTTB' },
    provenance: { provenance_id: 'PROV-7BNJN7GMBX1XQX20V6HAXX0QTN' },
    generated_at: '2026-08-10T02:00:00Z',
  },
  recent_findings: [
    {
      finding_id: 'FIND-1',
      evidence_status: 'SUPPORTIVE',
      finding: 'Quality signal survives neighboring parameters.',
      research: {
        type: 'research',
        id: 'RSCH-7ZB18YZVDQZ6QCPE22E86T0AMK',
        version: null,
        revision: 2,
      },
      provenance: { provenance_id: 'PROV-2FE5089W068EWMQYH3V7J20C3S' },
      updated_at: '2026-08-10T01:30:00Z',
    },
  ],
  agent_activity: [
    {
      agent_run_id: 'ARUN-568XYY4RMECVTXTGGJKREHDW37',
      role: 'FACTOR_SCIENTIST',
      objective: 'Test quality factor stability',
      status: 'RUNNING',
      decision_summary: null,
      next_action: 'Finish backtest batch',
      updated_at: '2026-08-10T01:45:00Z',
    },
  ],
  data_health: {
    state: 'HEALTHY',
    blocker_count: 0,
    warning_count: 1,
    checked_at: '2026-08-10T01:55:00Z',
    action_capabilities: [capability('inspect_data_health')],
  },
  provenance: [
    { provenance_id: 'PROV-1VQMSE365J6REYKWJ5VA5H0W35' },
    { provenance_id: 'PROV-7BNJN7GMBX1XQX20V6HAXX0QTN' },
  ],
  action_capabilities: [capability('refresh_overview')],
} satisfies Schema<'OverviewReadModel'>;

test('P01 renders the owner session without bearer-token controls', async ({ page }) => {
  await silenceEvents(page);
  await page.route('**/api/v1/overview', (route) => {
    return route.fulfill({ json: overview });
  });
  await page.goto('/overview');
  await expect(page.getByText('Quality momentum research')).toBeVisible();
  await expect(page.getByLabel(/Bearer token|通用密钥/)).toHaveCount(0);
  await expect(page.locator('.chart[role="img"]')).toBeVisible();
  await expect(page.getByText(/3 of 2,000 points shown using LTTB/)).toBeVisible();
  const chartTable = page.getByText('Chart data table');
  await chartTable.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('cell', { name: 'Gap' })).toBeVisible();
  const chartProvenance = page.locator('[title="Provenance: PROV-7BNJN7GMBX1XQX20V6HAXX0QTN"]');
  await expect(chartProvenance.first()).toBeVisible();
  await expect(chartProvenance).toHaveCount(2);
  for (const state of ['candidate', 'frozen', 'validating', 'validated', 'paper'])
    await expect(page.getByRole('heading', { name: state, exact: true })).toBeVisible();
  await expect(page.getByText('Quality signal survives neighboring parameters.')).toBeVisible();
  await expect(page.getByText('Test quality factor stability')).toBeVisible();
});

test('P09 renders canonical frozen strategy without edit controls', async ({ page }) => {
  await silenceEvents(page);
  let versionReads = 0;
  let backtestStarts = 0;
  let validationStarts = 0;
  const specification = {
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
    known_failure_modes: ['Crowded factor unwind'],
    spec_sha256: 'a'.repeat(64),
  } satisfies Parameters<typeof strategyProjection>[0];
  const strategy = {
    strategy_id: 'STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG',
    name: 'Quality momentum',
    version: 4,
    lifecycle_state: 'FROZEN',
    is_frozen: true,
    ...specification,
    ...strategyProjection(specification),
    frozen_at: '2026-08-10T00:00:00Z',
    frozen_by: 'owner',
    revision: 5,
    action_capabilities: [capability('run_fast_backtest'), capability('start_validation')],
    created_at: '2026-08-09T00:00:00Z',
  } satisfies Schema<'StrategyVersionDetail'>;
  await page.route(
    '**/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/current-version',
    (route) =>
      route.fulfill({
        json: strategy,
        headers: {
          ETag: 'W/"strategy:5"',
          'Content-Location': '/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4',
        },
      }),
  );
  await page.route('**/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4', (route) => {
    versionReads += 1;
    return route.fulfill({ json: strategy, headers: { ETag: 'W/"strategy:5"' } });
  });
  await page.route(
    '**/api/v1/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG/versions/4/backtests',
    async (route) => {
      backtestStarts += 1;
      expect(route.request().headers()['idempotency-key']).toBeTruthy();
      expect(await route.request().postDataJSON()).toEqual({
        snapshot_id: 'DS-249YFX4XBC3W17QTNC1X3EBKW4',
        cost_model_id: specification.cost_model_id,
        ...canonicalEngineFixtures.fastBacktest,
        parameters: [{ key: 'lookback', value: '252' }],
      } satisfies Schema<'BacktestRequest'>);
      return route.fulfill({
        status: 202,
        json: {
          job_id: 'JOB-33Z9AK7NF1KNGBVBDH8Y8G0D96',
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
        } satisfies Schema<'JobAccepted'>,
      });
    },
  );
  await page.route('**/api/v1/validations', async (route) => {
    validationStarts += 1;
    expect(route.request().headers()['idempotency-key']).toBeTruthy();
    expect(await route.request().postDataJSON()).toEqual({
      strategy_id: 'STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG',
      strategy_version: 4,
      policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
      ...canonicalEngineFixtures.strictValidation,
      test_suite_version: '2026.1',
    } satisfies Schema<'ValidationCreateRequest'>);
    return route.fulfill({
      status: 202,
      json: {
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
        resource_ref: {
          type: 'validation',
          id: 'VAL-318RQ1QJG1PEMKKM7C4D8TT944',
          version: null,
          revision: 1,
        },
        created_at: '2026-08-10T00:00:00Z',
      } satisfies Schema<'JobAccepted'>,
    });
  });
  const historyBefore = await page.evaluate(() => window.history.length);
  await page.goto('/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG');
  await expect(page).toHaveURL(/\/strategies\/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG\?version=4$/);
  expect(await page.evaluate(() => window.history.length)).toBe(historyBefore + 1);
  expect(versionReads).toBe(1);
  await expect(page.getByText('FROZEN · This version is immutable.')).toBeVisible();
  await expect(page.getByRole('textbox', { name: /thesis/i })).toHaveCount(0);
  await page.getByRole('link', { name: 'Specification' }).click();
  await expect(page.getByText('Canonical strategy specification')).toBeVisible();
  await expect(page.getByText('a'.repeat(64))).toBeVisible();
  await page.getByRole('link', { name: 'Backtests' }).click();
  await expect(page.getByText(/No canonical backtest is available/)).toBeVisible();
  await page.getByRole('link', { name: 'Risk' }).click();
  await expect(page.getByText('Crowded factor unwind')).toBeVisible();
  await page.getByRole('link', { name: 'Sensitivity' }).click();
  await expect(page.getByRole('link', { name: 'View provenance' })).toHaveAttribute(
    'href',
    '/activity?provenanceId=PROV-0NDJSGSG241E2XGDSHF7TS1736',
  );
  await page
    .getByRole('navigation', { name: 'Strategy details' })
    .getByRole('link', { name: 'Validation' })
    .click();
  await expect(page.getByText(/No validation has started/)).toBeVisible();
  await page.getByRole('link', { name: 'History' }).click();
  await expect(page.getByText('Version history')).toBeVisible();
  await page
    .getByRole('navigation', { name: 'Strategy details' })
    .getByRole('link', { name: 'Overview' })
    .click();
  await page.getByLabel('Snapshot ID').fill('DS-249YFX4XBC3W17QTNC1X3EBKW4');
  await page
    .getByLabel('Engine key', { exact: true })
    .fill(canonicalEngineFixtures.fastBacktest.engine_key);
  await page
    .getByLabel('Engine version', { exact: true })
    .fill(canonicalEngineFixtures.fastBacktest.engine_version);
  await page.getByLabel('Parameter key').fill('lookback');
  await page.getByLabel('Parameter value').fill('252');
  await page.getByTestId('capability-action-run_fast_backtest').click();
  await page.getByRole('button', { name: 'Confirm action' }).click();
  await expect(page.getByText(/Server job JOB-33Z9AK7NF1KNGBVBDH8Y8G0D96/)).toBeVisible();
  expect(backtestStarts).toBe(1);
  await page.getByLabel('Validation policy ID').fill('RP-756FFQA659A84RCEVR0M9X8DMN');
  await page
    .getByLabel('Strict engine key')
    .fill(canonicalEngineFixtures.strictValidation.strict_engine_key);
  await page
    .getByLabel('Strict engine version')
    .fill(canonicalEngineFixtures.strictValidation.strict_engine_version);
  await page.getByLabel('Test suite version').fill('2026.1');
  await page.getByTestId('capability-action-start_validation').click();
  await page.getByRole('button', { name: 'Confirm action' }).click();
  await expect(
    page.getByRole('link', { name: /Open validation VAL-318RQ1QJG1PEMKKM7C4D8TT944/ }),
  ).toBeVisible();
  expect(validationStarts).toBe(1);
});

// Retired setup wizard coverage: /setup now converges to the DB-backed Settings control plane.
// Equivalent control-plane coverage lives in setup-contract.spec.ts.
test.skip('P00 requires a verified AI connection ID before setup completion', async ({ page }) => {
  await silenceEvents(page);
  let completedBody: Record<string, unknown> | undefined;
  let completeRequests = 0;
  let aiReady = false;
  let dataReady = false;
  let completed = false;
  await page.route('**/api/v1/setup/status', (route) =>
    route.fulfill({
      json: {
        ...readySetupStatus,
        completed,
        ai_provider_configured: aiReady,
        ai_connection_id: aiReady ? 'CONN-AI-VERIFIED' : null,
        data_provider_configured: dataReady,
        fallback_step: aiReady ? null : 'AI_PROVIDER',
      },
    }),
  );
  await page.route('**/api/v1/setup/capabilities', (route) =>
    route.fulfill({
      json: {
        providers: [
          {
            provider_id: 'AI-OPENAI',
            display_name: 'OpenAI',
            kind: 'AI',
            connection_test_supported: true,
            models: [{ model_name: 'gpt-test', connection_test_supported: true }],
            data_capabilities: [],
          },
          {
            provider_id: 'DATA-PRIMARY',
            display_name: 'Primary Data',
            kind: 'DATA',
            connection_test_supported: true,
            models: [],
            data_capabilities: [
              {
                capability_id: 'CAP-35MYBZ1TNZM144QVG46FBY3HWF',
                provider_id: 'DATA-PRIMARY',
                capability_key: 'EOD_PRICES',
                state: 'SUPPORTED',
                asset_classes: ['EQUITY'],
                frequencies: ['DAILY'],
                coverage: { start: '2000-01-01', end: null },
                point_in_time: {
                  supported: true,
                  available_from: '2000-01-01',
                  semantics: 'as-published',
                },
                fields: ['close'],
                limitations: [],
                checked_at: '2026-08-10T00:00:00Z',
              },
            ],
          },
        ],
        server_checked_at: '2026-08-10T00:00:00Z',
      },
    }),
  );
  await page.route('**/api/v1/setup/provider-connections/validate', async (route) => {
    const request = (await route.request().postDataJSON()) as { kind: 'AI' | 'DATA' };
    if (request.kind === 'AI') aiReady = true;
    else dataReady = true;
    return route.fulfill({
      json: {
        connection_id: request.kind === 'AI' ? 'CONN-AI-VERIFIED' : 'CONN-DATA-VERIFIED',
        provider_id: request.kind === 'AI' ? 'AI-OPENAI' : 'DATA-PRIMARY',
        kind: request.kind,
        state: 'SUCCESS',
        detail: 'Verified',
        data_capabilities: [],
        checked_at: '2026-08-10T00:00:00Z',
      },
    });
  });
  await page.route('**/api/v1/overview', (route) => route.fulfill({ json: overview }));
  await page.route('**/api/v1/setup/complete', async (route) => {
    completeRequests += 1;
    completedBody = (await route.request().postDataJSON()) as Record<string, unknown>;
    completed = true;
    return route.fulfill({
      headers: { ETag: 'W/"SETTINGS-DEFAULT:1"' },
      json: {
        settings_id: 'SETTINGS-DEFAULT',
        revision: 1,
        ...completedBody,
        created_at: '2026-08-10T00:00:00Z',
        updated_at: '2026-08-10T00:00:00Z',
      },
    });
  });
  await page.goto('/setup');
  await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0);
  await expect(page.getByLabel(/语言|Language/)).toHaveValue('zh-CN');
  await expect(page.getByText(/实时状态/)).toBeVisible();
  await expect(page.getByRole('heading', { name: '首次运行设置' })).toBeVisible();
  await page.getByLabel(/语言|Language/).selectOption('en');
  await expect(page.getByText(/Realtime/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'First run setup' })).toBeVisible();
  await page.getByLabel('Language').selectOption('zh-CN');
  await expect(page.getByRole('heading', { name: '首次运行设置' })).toBeVisible();
  await page.getByLabel('语言').selectOption('en');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('button', { name: 'Continue' })).toBeDisabled();
  await expect(page.getByText(/Server setup status has not made this step eligible/)).toBeVisible();
  await page.getByLabel('AI provider').selectOption('AI-OPENAI');
  await page.getByLabel('Credential').fill('write-only-secret');
  await page.getByRole('button', { name: 'Test AI connection' }).click();
  await expect(page.getByText(/CONN-AI-VERIFIED/)).toBeVisible();
  await expect(page.getByLabel('Credential')).toHaveValue('');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('button', { name: 'Continue' })).toBeDisabled();
  await page.getByLabel('Default data provider').selectOption('DATA-PRIMARY');
  await expect(page.getByText('EOD_PRICES')).toBeVisible();
  await page.getByLabel('Data credential').fill('data-write-only-secret');
  await page.getByRole('button', { name: 'Test data connection' }).click();
  await expect(page.getByText(/CONN-DATA-VERIFIED/)).toBeVisible();
  await expect(page.getByLabel('Data credential')).toHaveValue('');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(
    page.getByText(
      /Server bindings: RP-756FFQA659A84RCEVR0M9X8DMN · RISK-7TTN4TSTQB0FXPTV60RHR5P7NH · COST-0QY70GRXXGT2HVM7HY8TMPXMVF/,
    ),
  ).toBeVisible();
  expect(completeRequests).toBe(0);
  await expect(page.getByText(/No look-ahead bias/)).toBeVisible();
  const setupA11y = await new AxeBuilder({ page }).analyze();
  expect(setupA11y.violations.map((violation) => violation.id)).toEqual([]);
  const finish = page.getByRole('button', { name: 'Finish setup' });
  await finish.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/overview$/);
  expect(completedBody?.ai_connection_id).toBe('CONN-AI-VERIFIED');
  expect(completedBody?.language).toBe('en');
  expect(completedBody?.default_data_provider_id).toBe('DATA-PRIMARY');
  expect(completedBody?.research_policy_id).toBe('RP-756FFQA659A84RCEVR0M9X8DMN');
  expect(completedBody?.risk_policy_id).toBe('RISK-7TTN4TSTQB0FXPTV60RHR5P7NH');
  expect(completedBody?.cost_model_id).toBe('COST-0QY70GRXXGT2HVM7HY8TMPXMVF');
  expect(completeRequests).toBe(1);
});

test.skip('P00 explicitly skips optional Data Provider and preserves capability limitations', async ({
  page,
}) => {
  await silenceEvents(page);
  await page.route('**/api/v1/setup/status', (route) =>
    route.fulfill({
      json: {
        ...readySetupStatus,
      } satisfies Schema<'SetupStatus'>,
    }),
  );
  await page.route('**/api/v1/setup/capabilities', (route) =>
    route.fulfill({
      json: {
        providers: [],
        server_checked_at: '2026-08-10T00:00:00Z',
      } satisfies Schema<'SetupCapabilityCatalog'>,
    }),
  );
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Skip optional data provider' }).click();
  await expect(page.getByText(/Some research capabilities are unavailable/)).toBeVisible();
  await expect(page.getByText(/Step 4 of 5/)).toBeVisible();
});

test.skip('P00 reload restores optional Data skip and completes with fresh server references', async ({
  page,
}) => {
  await silenceEvents(page);
  let completed = false;
  let submitted: Schema<'SetupCompleteRequest'> | undefined;
  await page.route('**/api/v1/setup/status', (route) =>
    route.fulfill({
      json: {
        ...readySetupStatus,
        completed,
      } satisfies Schema<'SetupStatus'>,
    }),
  );
  await page.route('**/api/v1/setup/capabilities', (route) =>
    route.fulfill({
      json: {
        providers: [],
        server_checked_at: '2026-08-10T00:00:00Z',
      } satisfies Schema<'SetupCapabilityCatalog'>,
    }),
  );
  await page.route('**/api/v1/setup/complete', async (route) => {
    submitted = (await route.request().postDataJSON()) as Schema<'SetupCompleteRequest'>;
    completed = true;
    return route.fulfill({
      headers: { ETag: 'W/"config:1"' },
      json: {
        active_revision: submitted.configuration_revision,
        last_known_good_revision: submitted.configuration_revision,
        catalog_version: 'v1',
        values: [],
        snapshot_sha256: 'a'.repeat(64),
        consumer_states: [],
        updated_at: '2026-08-10T00:00:00Z',
      } satisfies Schema<'SettingsDetail'>,
    });
  });
  await page.route('**/api/v1/overview', (route) => route.fulfill({ json: overview }));
  await page.goto('/setup');
  await expect(page.getByText('Step 1 of 5')).toBeVisible();
  await page.reload();
  await expect(page.getByText('Step 3 of 5')).toBeVisible();
  await expect(page.getByText(/server reports no optional data provider/i)).toBeVisible();
  await page.getByRole('button', { name: 'Skip optional data provider' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Finish setup' }).click();
  await expect(page).toHaveURL(/\/overview$/);
  expect(submitted?.configuration_revision).toBeGreaterThan(0);
});

test.skip('SSE resync refetches REST truth without clearing a P00 draft', async ({ page }) => {
  let releaseStream: () => void = () => {};
  const streamGate = new Promise<void>((resolve) => {
    releaseStream = resolve;
  });
  let statusReads = 0;
  await page.route('**/api/v1/events/stream', async (route) => {
    await streamGate;
    return route.fulfill({
      contentType: 'text/event-stream',
      body: 'data: {"schema_version":1,"event_id":"e1","sequence":1,"event_type":"system.resync_required","occurred_at":"2026-01-01T00:00:00Z","object_type":"system","object_id":"root","object_version":null,"object_revision":null,"request_id":null,"job_id":null,"agent_run_id":null,"tool_call_id":null,"payload":{"resync_from_sequence":1}}\n\n',
    });
  });
  await page.route('**/api/v1/setup/status', (route) => {
    statusReads += 1;
    return route.fulfill({
      json: {
        ...readySetupStatus,
        ai_provider_configured: false,
        ai_connection_id: null,
        research_policy_active: false,
        research_policy_id: null,
        risk_policy_active: false,
        risk_policy_id: null,
        cost_model_active: false,
        cost_model_id: null,
        fallback_step: 'AI_PROVIDER',
      },
    });
  });
  await page.route('**/api/v1/setup/capabilities', (route) =>
    route.fulfill({ json: { providers: [], server_checked_at: '2026-08-10T00:00:00Z' } }),
  );
  await page.goto('/setup');
  await page.getByLabel('base currency').fill('CNY');
  releaseStream();
  await expect.poll(() => statusReads).toBeGreaterThan(1);
  await expect(page.getByLabel('base currency')).toHaveValue('CNY');
});

test.skip('SSE contract skew uses safe resync and preserves the P00 draft', async ({ page }) => {
  let releaseStream: () => void = () => {};
  const streamGate = new Promise<void>((resolve) => {
    releaseStream = resolve;
  });
  let statusReads = 0;
  await page.route('**/api/v1/events/stream', async (route) => {
    await streamGate;
    return route.fulfill({
      contentType: 'text/event-stream',
      body: 'data: {"schema_version":1,"event_id":"e-skew","sequence":1,"event_type":"Experiment.Updated","occurred_at":"2026-01-01T00:00:00Z","object_type":"experiment","object_id":"EXP-5M931VPS47ACN5XT12773AK2DV","object_version":null,"object_revision":1,"request_id":null,"job_id":null,"agent_run_id":null,"tool_call_id":null,"payload":{"metric":"9.99"}}\n\n',
    });
  });
  await page.route('**/api/v1/setup/status', (route) => {
    statusReads += 1;
    return route.fulfill({
      json: {
        ...readySetupStatus,
        ai_provider_configured: false,
        ai_connection_id: null,
        fallback_step: 'AI_PROVIDER',
      } satisfies Schema<'SetupStatus'>,
    });
  });
  await page.route('**/api/v1/setup/capabilities', (route) =>
    route.fulfill({ json: { providers: [], server_checked_at: '2026-08-10T00:00:00Z' } }),
  );
  await page.goto('/setup');
  await page.getByLabel('base currency').fill('CNY');
  releaseStream();
  await expect.poll(() => statusReads).toBeGreaterThan(1);
  await expect(page.getByText(/Re-synchronizing/)).toBeVisible();
  await expect(page.getByLabel('base currency')).toHaveValue('CNY');
  await expect(page.getByText('9.99')).toHaveCount(0);
});

test('P11 shows mandatory FAIL in matrix/inspector and never requests locked holdout result', async ({
  page,
}) => {
  await silenceEvents(page);
  let resultRequests = 0;
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', (route) =>
    route.fulfill({ json: validation, headers: { ETag: 'W/"validation:3"' } }),
  );
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout', (route) =>
    route.fulfill({
      json: {
        validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
        state: 'LOCKED',
        exposure_count: 0,
        period: { start: '2023-01-01', end: '2025-12-31' },
        approval: null,
        action_capabilities: [capability('run_holdout', false)],
        revision: 3,
        validation,
      },
      headers: { ETag: 'W/"holdout:3"' },
    }),
  );
  await page.route(
    '**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout/result',
    (route) => {
      resultRequests += 1;
      return route.fulfill({ status: 403, json: {} });
    },
  );
  await page.setViewportSize({ width: 1180, height: 900 });
  await page.goto('/validation/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J');
  await expect(page.getByText('Mandatory validation failure.')).toBeVisible();
  await expect(page.getByRole('cell', { name: 'FAIL', exact: true })).toBeVisible();
  await expect(page.getByText('Override permitted: never')).not.toBeVisible();
  const inspector = page.getByRole('button', { name: 'Open test inspector' });
  await inspector.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog', { name: 'Validation inspector' })).toContainText(
    'Override permitted: never',
  );
  await expect(page.getByRole('dialog', { name: 'Validation inspector' })).toContainText(
    'ART-6C7M8NEP8K5HFEMKK0Q7DRNWKQ',
  );
  await expect(
    page.getByRole('dialog', { name: 'Validation inspector' }).getByText('View provenance'),
  ).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(inspector).toBeFocused();
  await expect(page.getByRole('link', { name: 'Return to Research' })).toHaveAttribute(
    'href',
    '/research',
  );
  expect(resultRequests).toBe(0);
  await page.getByRole('button', { name: 'view_strategy' }).click();
  await expect(page).toHaveURL(/\/strategies\/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG\?version=4$/);
  await page.goto('/validation/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J');
  await page.getByRole('button', { name: 'return_to_research' }).click();
  await expect(page).toHaveURL(/\/research$/);
});

test('P11 requests approval from Validation detail capability and converges both server projections', async ({
  page,
}) => {
  await silenceEvents(page);
  let requested = false;
  let validationReads = 0;
  let gateReads = 0;
  let approvalRequests = 0;
  let resultRequests = 0;
  const waitingValidation = {
    ...validation,
    status: 'WAITING_HOLDOUT',
    result: 'PASS',
    tests: validation.tests.map((result) => ({
      ...result,
      state: 'PASS' as const,
      failure_code: null,
      failure_detail: null,
    })),
    failures: [],
    holdout_state: 'LOCKED',
    revision: 3,
    action_capabilities: [capability('request_holdout_approval', true, false)],
  } satisfies Schema<'ValidationDetail'>;
  const deniedRun = {
    ...capability('run_holdout', false),
    reason_code: 'HOLDOUT_APPROVAL_REQUIRED',
    reason_detail: 'Owner approval is required.',
  } satisfies Schema<'ActionCapability'>;
  const approval = {
    approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
    type: 'HOLDOUT_UNLOCK',
    subject: {
      type: 'VALIDATION',
      id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
      version: 4,
      revision: 3,
      sha256: 'b'.repeat(64),
    },
    requester: { type: 'OWNER', id: 'owner' },
    reason: 'Controlled matrix holdout',
    prerequisites: [{ key: 'strict_validation', state: 'PASS', detail: 'Passed' }],
    risk_summary: { risk_level: 'HIGH', warning_codes: [] },
    effects: [{ code: 'EXPOSE_HOLDOUT', detail: 'Exposure count increments.' }],
    status: 'PENDING',
    requested_at: '2026-08-10T00:00:00Z',
    decided_at: null,
    revision: 1,
    action_capabilities: [],
  } satisfies Schema<'ApprovalDetail'>;
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', (route) => {
    validationReads += 1;
    return route.fulfill({
      json: requested
        ? {
            ...waitingValidation,
            holdout_state: 'APPROVAL_PENDING',
            revision: 4,
            action_capabilities: [],
          }
        : waitingValidation,
      headers: {
        ETag: requested
          ? 'W/"VAL-2GKYQRFB6BG5R4AVJSYCAJH56J:4"'
          : 'W/"VAL-2GKYQRFB6BG5R4AVJSYCAJH56J:3"',
      },
    });
  });
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout', (route) => {
    gateReads += 1;
    return route.fulfill({
      json: {
        validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
        state: requested ? 'APPROVAL_PENDING' : 'LOCKED',
        exposure_count: 0,
        period: { start: '2023-01-01', end: '2025-12-31' },
        approval: requested
          ? { approval_id: approval.approval_id, status: 'PENDING', revision: 1 }
          : null,
        action_capabilities: [deniedRun],
        revision: requested ? 4 : 3,
      } satisfies Schema<'HoldoutGate'>,
      headers: {
        ETag: requested
          ? 'W/"VAL-2GKYQRFB6BG5R4AVJSYCAJH56J:4"'
          : 'W/"VAL-2GKYQRFB6BG5R4AVJSYCAJH56J:3"',
      },
    });
  });
  await page.route(
    '**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout-approval-requests',
    async (route) => {
      approvalRequests += 1;
      expect(route.request().headers()['if-match']).toBe('W/"VAL-2GKYQRFB6BG5R4AVJSYCAJH56J:3"');
      expect(route.request().headers()['idempotency-key']).toBeTruthy();
      expect(await route.request().postDataJSON()).toEqual({ reason: 'Controlled matrix holdout' });
      requested = true;
      return route.fulfill({
        status: 201,
        json: approval,
        headers: { ETag: 'W/"APR-0T71YPB60APYFY39FY75RYTVZB:1"' },
      });
    },
  );
  await page.route(
    '**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout/result',
    (route) => {
      resultRequests += 1;
      return route.fulfill({ status: 403, json: {} });
    },
  );

  await page.goto('/validation/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J');
  const requestAction = page.getByTestId('capability-action-request_holdout_approval');
  await expect(requestAction).toBeDisabled();
  await expect(page.getByTestId('capability-action-run_holdout')).toBeDisabled();
  await expect(page.getByTestId('capability-action-run_holdout')).toHaveAttribute(
    'title',
    'Owner approval is required.',
  );
  await page.getByLabel('Approval reason').fill('Controlled matrix holdout');
  await expect(requestAction).toBeEnabled();
  await requestAction.click();
  // public-id-prose APR-
  await expect(page.getByText(/Holdout approval requested: APR-/)).toBeVisible();
  await expect(page.getByText('APPROVAL PENDING')).toBeVisible();
  await expect(requestAction).toHaveCount(0);
  expect(approvalRequests).toBe(1);
  expect(validationReads).toBeGreaterThan(1);
  expect(gateReads).toBeGreaterThan(1);
  expect(resultRequests).toBe(0);
  await expect(page.getByText('HOLDOUT_SENTINEL_SECRET')).toHaveCount(0);
});

test('P11 exposes only REST-authoritative result metrics with units', async ({ page }) => {
  await silenceEvents(page);
  let resultRequests = 0;
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', (route) =>
    route.fulfill({ json: { ...validation, holdout_state: 'EXPOSED' } }),
  );
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout', (route) =>
    route.fulfill({
      json: {
        validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
        state: 'EXPOSED',
        exposure_count: 1,
        period: { start: '2023-01-01', end: '2025-12-31' },
        approval: {
          approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
          status: 'APPROVED',
          revision: 2,
        },
        action_capabilities: [],
        revision: 4,
      },
      headers: { ETag: 'W/"holdout:4"' },
    }),
  );
  await page.route(
    '**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout/result',
    (route) => {
      resultRequests += 1;
      return route.fulfill({
        json: {
          validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
          exposure_id: 'HOLD-5CQ24N64HEPRNJK4MM74BBNR6Y',
          result: 'PASS',
          metrics: [{ key: 'sharpe', value: '1.21', unit: 'ratio' }],
          provenance: {
            provenance_id: 'PROV-1VXJNVW9YNJVYYMWPBR70QMHYW',
            schema_version: 1,
            experiment_id: null,
            source_experiment_id: null,
            tool_call_id: null,
            data_snapshot_ids: [],
            engine: { name: 'holdout-engine', version: '1.0.0' },
            adapter: null,
            code: { commit: 'abc123', build_id: 'build-1' },
            policies: [],
            strategy: null,
            factors: [],
            cost_model: null,
            parameters_sha256: null,
            input_sha256: 'a'.repeat(64),
            output_sha256: 'b'.repeat(64),
            calculated_at: '2026-08-10T03:00:00Z',
          },
          exposed_at: '2026-08-10T03:00:00Z',
        },
      });
    },
  );
  await page.goto('/validation/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J');
  await expect(page.getByText('HOLD-5CQ24N64HEPRNJK4MM74BBNR6Y')).toBeVisible();
  await expect(page.getByText(/1.21 ratio/)).toBeVisible();
  expect(resultRequests).toBe(1);
});

test('P11 holdout run confirms once, sends If-Match/idempotency, and surfaces already-exposed', async ({
  page,
}) => {
  await silenceEvents(page);
  let runs = 0;
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J', (route) =>
    route.fulfill({ json: { ...validation, result: 'PASS', holdout_state: 'UNLOCKED' } }),
  );
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout', (route) =>
    route.fulfill({
      json: {
        validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
        state: 'UNLOCKED',
        exposure_count: 0,
        period: { start: '2023-01-01', end: '2025-12-31' },
        approval: {
          approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
          status: 'APPROVED',
          revision: 2,
        },
        action_capabilities: [capability('run_holdout')],
        revision: 4,
      },
      headers: { ETag: 'W/"holdout:4"' },
    }),
  );
  await page.route('**/api/v1/validations/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J/holdout-runs', (route) => {
    runs += 1;
    expect(route.request().headers()['if-match']).toBe('W/"holdout:4"');
    expect(route.request().headers()['idempotency-key']).toBeTruthy();
    return route.fulfill({
      status: 409,
      json: {
        type: 'about:blank',
        title: 'Already exposed',
        status: 409,
        code: 'HOLDOUT_ALREADY_EXPOSED',
        detail: 'The protected result was already exposed.',
        instance: null,
        request_id: 'REQ-EXPOSED',
        retryable: false,
        field_errors: [],
        context: { validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J' },
      },
    });
  });
  await page.goto('/validation/VAL-2GKYQRFB6BG5R4AVJSYCAJH56J');
  await page.getByTestId('capability-action-run_holdout').click();
  await page.getByRole('button', { name: 'Confirm action' }).dblclick();
  await expect(page.getByText(/already exposed/i)).toBeVisible();
  expect(runs).toBe(1);
});

test('P14 412 revision mismatch stays in the complete confirmation modal', async ({ page }) => {
  await silenceEvents(page);
  let detailReads = 0;
  const detail = {
    approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
    type: 'HOLDOUT_UNLOCK',
    subject: {
      type: 'VALIDATION',
      id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
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
  await page.route('**/api/v1/approvals/APR-0T71YPB60APYFY39FY75RYTVZB', (route) => {
    detailReads += 1;
    const latest =
      detailReads === 1
        ? detail
        : {
            ...detail,
            subject: { ...detail.subject, revision: 4, sha256: 'd'.repeat(64) },
            revision: 4,
          };
    return route.fulfill({
      json: latest,
      headers: { ETag: detailReads === 1 ? 'W/"approval:3"' : 'W/"approval:4"' },
    });
  });
  await page.route('**/api/v1/approvals/APR-0T71YPB60APYFY39FY75RYTVZB/approve', async (route) => {
    expect(route.request().headers()['if-match']).toBe('W/"approval:4"');
    expect((await route.request().postDataJSON()).acknowledged_subject_sha256).toBe('d'.repeat(64));
    return route.fulfill({
      status: 412,
      json: {
        type: 'about:blank',
        title: 'Revision mismatch',
        status: 412,
        code: 'REVISION_MISMATCH',
        detail: 'Subject revision changed.',
        instance: null,
        request_id: 'REQ-STALE-1',
        retryable: false,
        field_errors: [],
        context: {
          object_type: 'approval',
          object_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
          object_version: null,
          object_revision: null,
        },
      },
    });
  });
  await page.goto('/approvals/APR-0T71YPB60APYFY39FY75RYTVZB');
  await page.getByRole('button', { name: 'Review and reject' }).click();
  const rejectDialog = page.getByRole('dialog', { name: 'Confirm rejection' });
  await expect(
    rejectDialog.getByRole('button', { name: 'Confirm versioned decision' }),
  ).toBeDisabled();
  await rejectDialog.getByLabel('Rejection reason').fill('Evidence does not support exposure.');
  await expect(
    rejectDialog.getByRole('button', { name: 'Confirm versioned decision' }),
  ).toBeEnabled();
  await rejectDialog.getByRole('button', { name: 'Cancel' }).click();
  const approveTrigger = page.getByTestId('capability-action-approve');
  await expect(approveTrigger).toHaveAttribute('data-requires-confirmation', 'true');
  await approveTrigger.click();
  const dialog = page.getByRole('dialog', { name: 'Confirm approval' });
  await expect(dialog).toContainText('VAL-2GKYQRFB6BG5R4AVJSYCAJH56J');
  await expect(dialog).toContainText('EXPOSE_HOLDOUT');
  await expect(dialog).toContainText('strict_validation');
  await expect(dialog).toContainText('d'.repeat(64));
  expect(detailReads).toBeGreaterThanOrEqual(3);
  await page.getByTestId('capability-confirm-approve').click();
  await expect(dialog.getByText(/This record changed/)).toBeVisible();
  await expect(dialog.getByRole('link', { name: /REQ-STALE-1/ })).toBeVisible();
  await expect(dialog).toBeVisible();
});

test('P14 executes directly when the server approval capability requires no confirmation', async ({
  page,
}) => {
  await silenceEvents(page);
  let approved = false;
  let approveRequests = 0;
  const detail = {
    approval_id: 'APR-4F2AZ2JW99QY7PGMQJ9X3T500M',
    type: 'HOLDOUT_UNLOCK',
    subject: {
      type: 'VALIDATION',
      id: 'VAL-77JDJ6EWBNXK7F83TKMJZAR7XS',
      version: 2,
      revision: 5,
      sha256: 'c'.repeat(64),
    },
    requester: { type: 'OWNER', id: 'owner' },
    reason: 'One-time exposure.',
    prerequisites: [{ key: 'strict_validation', state: 'PASS', detail: 'Passed' }],
    risk_summary: { risk_level: 'HIGH', warning_codes: [] },
    effects: [{ code: 'EXPOSE_HOLDOUT', detail: 'Exposure count increments.' }],
    status: 'PENDING',
    requested_at: '2026-08-10T00:00:00Z',
    decided_at: null,
    revision: 5,
    action_capabilities: [capability('approve', true, false)],
  } satisfies Schema<'ApprovalDetail'>;
  const approvedDetail = {
    ...detail,
    status: 'APPROVED',
    decided_at: '2026-08-10T01:00:00Z',
    revision: 6,
    action_capabilities: [],
  } satisfies Schema<'ApprovalDetail'>;
  await page.route('**/api/v1/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M', (route) =>
    route.fulfill({
      json: approved ? approvedDetail : detail,
      headers: { ETag: approved ? 'W/"approval:6"' : 'W/"approval:5"' },
    }),
  );
  await page.route('**/api/v1/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M/approve', async (route) => {
    approveRequests += 1;
    expect(route.request().headers()['if-match']).toBe('W/"approval:5"');
    expect(route.request().headers()['idempotency-key']).toBeTruthy();
    expect(await route.request().postDataJSON()).toEqual({
      acknowledged_subject_sha256: 'c'.repeat(64),
    });
    approved = true;
    return route.fulfill({
      json: {
        approval: approvedDetail,
        subject_ref: {
          type: 'validation',
          id: detail.subject.id,
          version: detail.subject.version,
          revision: detail.subject.revision,
        },
        next_job: null,
      } satisfies Schema<'ApprovalDecisionResult'>,
    });
  });
  await page.goto('/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M');
  const approve = page.getByTestId('capability-action-approve');
  await expect(approve).toHaveAttribute('data-requires-confirmation', 'false');
  await approve.click();
  await expect(page.getByRole('dialog', { name: 'Confirm approval' })).toHaveCount(0);
  await expect(page.getByText('APPROVED')).toBeVisible();
  expect(approveRequests).toBe(1);
  await expect(page.getByTestId('capability-confirm-approve')).toHaveCount(0);
});

test('P14 409 approval stale refetches to STALE and permanently removes decisions', async ({
  page,
}) => {
  await silenceEvents(page);
  let stale = false;
  const detail = {
    approval_id: 'APR-4F2AZ2JW99QY7PGMQJ9X3T500M',
    type: 'HOLDOUT_UNLOCK',
    subject: {
      type: 'VALIDATION',
      id: 'VAL-77JDJ6EWBNXK7F83TKMJZAR7XS',
      version: 2,
      revision: 5,
      sha256: 'c'.repeat(64),
    },
    requester: { type: 'OWNER', id: 'owner' },
    reason: 'One-time exposure.',
    prerequisites: [{ key: 'strict_validation', state: 'PASS', detail: 'Passed' }],
    risk_summary: { risk_level: 'HIGH', warning_codes: [] },
    effects: [{ code: 'EXPOSE_HOLDOUT', detail: 'Exposure count increments.' }],
    status: 'PENDING',
    requested_at: '2026-08-10T00:00:00Z',
    decided_at: null,
    revision: 5,
    action_capabilities: [capability('approve'), capability('reject')],
  } satisfies Schema<'ApprovalDetail'>;
  await page.route('**/api/v1/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M', (route) =>
    route.fulfill({
      json: stale ? { ...detail, status: 'STALE', action_capabilities: [] } : detail,
      headers: { ETag: stale ? 'W/"approval:6"' : 'W/"approval:5"' },
    }),
  );
  await page.route('**/api/v1/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M/approve', (route) => {
    stale = true;
    return route.fulfill({
      status: 409,
      json: {
        type: 'about:blank',
        title: 'Approval stale',
        status: 409,
        code: 'APPROVAL_STALE',
        detail: 'The subject changed.',
        instance: null,
        request_id: 'REQ-APPROVAL-STALE',
        retryable: false,
        field_errors: [],
        context: { approval_id: 'APR-4F2AZ2JW99QY7PGMQJ9X3T500M' },
      },
    });
  });
  await page.goto('/approvals/APR-4F2AZ2JW99QY7PGMQJ9X3T500M');
  await page.getByTestId('capability-action-approve').click();
  await page.getByTestId('capability-confirm-approve').click();
  await expect(page.getByText(/Approval is stale/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Review and approve' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Review and reject' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: /REQ-APPROVAL-STALE/ })).toBeVisible();
});

test('P15 memo keeps paper future-staged and passes axe at target viewport', async ({ page }) => {
  await silenceEvents(page);
  let paperMutations = 0;
  page.on('request', (request) => {
    if (request.method() !== 'GET' && request.url().toLowerCase().includes('paper'))
      paperMutations += 1;
  });
  await page.route('**/api/v1/memos/MEMO-7Z2PE0RP0Q2V5V062RXP9BCB84', (route) =>
    route.fulfill({
      json: {
        memo_id: 'MEMO-7Z2PE0RP0Q2V5V062RXP9BCB84',
        strategy: { id: 'STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG', version: 4 },
        status: 'FINAL',
        sections: [
          {
            section_key: 'thesis',
            title: 'Investment thesis',
            content: 'Evidence-bound conclusion.',
            evidence_links: [
              {
                experiment_id: 'EXP-1ARJ28R0P0Z6NFWK752RRR4QPN',
                provenance: { provenance_id: 'PROV-0KAGD73GB3Z2AKJ4RRCBCKZFZG' },
              },
            ],
          },
        ],
        provenance: [{ provenance_id: 'PROV-0KAGD73GB3Z2AKJ4RRCBCKZFZG' }],
        revision: 1,
        action_capabilities: [],
        created_at: '2026-08-10T00:00:00Z',
        updated_at: '2026-08-10T00:00:00Z',
      },
    }),
  );
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/memos/MEMO-7Z2PE0RP0Q2V5V062RXP9BCB84');
  await expect(page.getByRole('button', { name: /Request Paper Approval/ })).toBeDisabled();
  await expect(page.getByRole('button', { name: /Ask About Memo/ })).toBeDisabled();
  await expect(page.getByRole('button', { name: /Export PDF/ })).toBeDisabled();
  await expect(page.getByText('PROV-0KAGD73GB3Z2AKJ4RRCBCKZFZG')).toBeVisible();
  expect(paperMutations).toBe(0);
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((item) => item.impact === 'critical').map((item) => item.id),
  ).toEqual([]);
  await expect(page).toHaveScreenshot('memo-1440.png', {
    animations: 'disabled',
    fullPage: true,
    mask: [page.locator('.topbar')],
  });
});

test('P20 Disable uses config ETag, recovers stale revision, and never discovers runs', async ({
  page,
}) => {
  await silenceEvents(page);
  let configReads = 0;
  let runRequests = 0;
  let updateRequests = 0;
  const config = {
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
  await page.route('**/api/v1/agents', (route) => route.fulfill({ json: [config] }));
  await page.route('**/api/v1/agents/RESEARCH_DIRECTOR/config', async (route) => {
    if (route.request().method() === 'GET') {
      configReads += 1;
      return route.fulfill({ json: config, headers: { ETag: 'W/"agent:3"' } });
    }
    updateRequests += 1;
    expect(route.request().headers()['if-match']).toBe('W/"agent:3"');
    return route.fulfill({
      status: 412,
      json: {
        type: 'about:blank',
        title: 'Revision mismatch',
        status: 412,
        code: 'REVISION_MISMATCH',
        detail: 'Agent config changed.',
        instance: null,
        request_id: 'REQ-AGENT-STALE',
        retryable: false,
        field_errors: [],
        context: {},
      },
    });
  });
  page.on('request', (request) => {
    if (request.url().includes('/agent-runs')) runRequests += 1;
  });
  await page.goto('/agents');
  await expect(
    page.getByText(/Active durable runs and checkpoints are not cancelled/),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Disable future admission' }).click();
  await page.getByRole('button', { name: 'Confirm action' }).dblclick();
  await expect(page.getByText(/This record changed/)).toBeVisible();
  await expect.poll(() => configReads).toBeGreaterThan(1);
  expect(updateRequests).toBe(1);
  expect(runRequests).toBe(0);
});

test('P20 Disable recovers a 428 precondition with a config refetch', async ({ page }) => {
  await silenceEvents(page);
  let reads = 0;
  const config = {
    role_key: 'RESEARCH_DIRECTOR',
    enabled: true,
    model_provider: 'openai',
    model_name: 'gpt-test',
    ai_connection_id: 'CODEX-DEFAULT',
    ai_connection_revision: 1,
    runtime_profile: 'default',
    tool_timeout_seconds: 60,
    max_steps_override: 20,
    max_tool_calls_override: 40,
    revision: 4,
    action_capabilities: [capability('update_agent_config')],
    created_at: '2026-08-10T00:00:00Z',
    updated_at: '2026-08-10T00:00:00Z',
  } satisfies Schema<'AgentConfig'>;
  await page.route('**/api/v1/agents', (route) => route.fulfill({ json: [config] }));
  await page.route('**/api/v1/agents/RESEARCH_DIRECTOR/config', (route) => {
    if (route.request().method() === 'GET') {
      reads += 1;
      return route.fulfill({ json: config, headers: { ETag: 'W/"agent:4"' } });
    }
    return route.fulfill({
      status: 428,
      json: {
        type: 'about:blank',
        title: 'Precondition required',
        status: 428,
        code: 'PRECONDITION_REQUIRED',
        detail: 'Reload the current config.',
        instance: null,
        request_id: 'REQ-AGENT-428',
        retryable: false,
        field_errors: [],
        context: {},
      },
    });
  });
  await page.goto('/agents');
  await expect(page.getByText('20')).toBeVisible();
  await page.getByRole('button', { name: 'Disable future admission' }).click();
  await page.getByRole('button', { name: 'Confirm action' }).click();
  await expect(page.getByText(/Refresh and confirm the latest server state/)).toBeVisible();
  await expect.poll(() => reads).toBeGreaterThan(1);
});

test('P20 Disable succeeds once and updates future admission state', async ({ page }) => {
  await silenceEvents(page);
  let enabled = true;
  let updates = 0;
  const config = () =>
    ({
      role_key: 'RESEARCH_DIRECTOR',
      enabled,
      model_provider: 'openai',
      model_name: 'gpt-test',
      ai_connection_id: 'CODEX-DEFAULT',
      ai_connection_revision: 1,
      runtime_profile: 'default',
      tool_timeout_seconds: 60,
      max_steps_override: null,
      max_tool_calls_override: null,
      revision: enabled ? 3 : 4,
      action_capabilities: [capability('update_agent_config')],
      created_at: '2026-08-10T00:00:00Z',
      updated_at: '2026-08-10T00:00:00Z',
    }) satisfies Schema<'AgentConfig'>;
  await page.route('**/api/v1/agents', (route) => route.fulfill({ json: [config()] }));
  await page.route('**/api/v1/agents/RESEARCH_DIRECTOR/config', async (route) => {
    if (route.request().method() === 'GET')
      return route.fulfill({
        json: config(),
        headers: { ETag: enabled ? 'W/"agent:3"' : 'W/"agent:4"' },
      });
    updates += 1;
    expect(route.request().headers()['if-match']).toBe('W/"agent:3"');
    expect(await route.request().postDataJSON()).toEqual({ enabled: false });
    enabled = false;
    return route.fulfill({ json: config(), headers: { ETag: 'W/"agent:4"' } });
  });
  await page.goto('/agents');
  await page.getByRole('button', { name: 'Disable future admission' }).click();
  await page.getByRole('button', { name: 'Confirm action' }).dblclick();
  await expect(page.getByText('DISABLED')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Enable future admission' })).toBeEnabled();
  expect(updates).toBe(1);
});
