import type { Schema } from '../src/api/client';

type CanonicalEngineFixtures = {
  fastBacktest: Pick<Schema<'BacktestRequest'>, 'engine_key' | 'engine_version'>;
  strictValidation: Pick<
    Schema<'ValidationCreateRequest'>,
    'strict_engine_key' | 'strict_engine_version'
  >;
};

export const canonicalEngineFixtures = {
  fastBacktest: { test-api-key-unavailable, engine_version: '1.0.0' },
  strictValidation: {
    strict_engine_key: 'qf-validation-v1',
    strict_engine_version: '1.0.0',
  },
} as const satisfies CanonicalEngineFixtures;

export const readySetupStatus = {
  completed: false,
  owner_session_ready: true,
  ai_provider_configured: true,
  ai_connection_id: 'CONN-AI-VERIFIED',
  data_provider_configured: false,
  research_policy_active: true,
  research_policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
  risk_policy_active: true,
  risk_policy_id: 'RISK-7TTN4TSTQB0FXPTV60RHR5P7NH',
  cost_model_active: true,
  cost_model_id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF',
  fallback_step: null,
} satisfies Schema<'SetupStatus'>;

type ResearchProjection = Pick<
  Schema<'ResearchDetail'>,
  'overview' | 'plan' | 'timeline' | 'experiments' | 'evidence' | 'artifacts' | 'audit'
>;

export function researchProjection(started: boolean): ResearchProjection {
  const node: Schema<'ResearchPlanNodeReadModel'> = {
    node_key: 'quality-test',
    title: 'Test quality after costs',
    owner_agent_role: 'FACTOR_SCIENTIST',
    status: started ? 'RUNNING' : 'PENDING',
    depends_on: [],
    objective: 'Measure persistence after realistic costs.',
    finding_summary: null,
    experiment_count: started ? 1 : 0,
    sort_order: 1,
  };
  const page = { next_cursor: null, has_more: false } satisfies Schema<'PageInfo'>;
  const evidence: Schema<'ResearchEvidenceItem'> = {
    evidence: {
      type: 'evidence',
      id: 'EVID-01J77KCWBMWESD3FBAY4R8GGQT',
      version: null,
      revision: 1,
    },
    stance: 'SUPPORTING',
    claim: 'Quality remains positive after measured costs.',
    source_experiment: {
      type: 'experiment',
      id: 'EXP-6NRYG2G3MDMMT74S8B4SMZTRCV',
      version: null,
      revision: 1,
    },
    result_locator: {
      result_sha256: 'd'.repeat(64),
      metric_key: 'sharpe',
      artifact: {
        type: 'artifact',
        id: 'ART-1N71JE4YY6S21C6P56JB8ZXKNS',
        version: null,
        revision: 1,
      },
    },
    strength: 'MODERATE',
    limitations: 'Single market regime.',
    is_invalidated: false,
    provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
    created_at: '2026-08-10T00:30:00Z',
  };
  return {
    overview: {
      brief: {
        revision_no: 1,
        question: 'Does quality persist after costs?',
        hypothesis: 'Quality remains positive after costs.',
        economic_rationale: 'Quality may proxy durable profitability.',
        supporting_evidence_definition: 'Positive net risk-adjusted return.',
        disconfirming_evidence_definition: 'Negative net risk-adjusted return.',
        universe: { asset_class: 'EQUITY', symbols: ['SPY'], universe_id: null },
        benchmark: 'SPY',
        period: { start: '2010-01-01', end: '2018-12-31' },
        frequency: 'DAILY',
        content_sha256: 'b'.repeat(64),
      },
      current_conclusion: null,
      progress: [node],
      latest_evidence: started ? [evidence] : [],
      current_agent_work: started
        ? {
            agent_run_id: 'ARUN-62ARPFG8ZC6EAXFT8Q6YN5S0VZ',
            agent_role: 'FACTOR_SCIENTIST',
            status: 'RUNNING',
            objective: 'Measure persistence.',
            current_action: 'Run experiment',
            tool: { name: 'factor-engine', version: '1.0.0' },
            next_action: 'Review evidence',
            provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
            updated_at: '2026-08-10T00:00:00Z',
          }
        : null,
    },
    plan: started
      ? {
          plan_version: 1,
          source_revision_no: 1,
          status: 'ACTIVE',
          rationale_summary: 'Test the stated hypothesis.',
          nodes: [node],
          content_sha256: 'c'.repeat(64),
          provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
          created_at: '2026-08-10T00:00:00Z',
        }
      : null,
    timeline: {
      items: started
        ? [
            {
              event_id: 'EVT-6KCWBZ58V080B7HFKFYDHWZTHR',
              agent_role: 'FACTOR_SCIENTIST',
              objective: 'Measure persistence.',
              tool: { name: 'factor-engine', version: '1.0.0' },
              result_summary: 'Experiment completed.',
              decision_summary: 'Retain evidence.',
              next_action: 'Review validation readiness.',
              object: {
                type: 'experiment',
                id: 'EXP-6NRYG2G3MDMMT74S8B4SMZTRCV',
                version: null,
                revision: 1,
              },
              provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
              occurred_at: '2026-08-10T00:30:00Z',
            },
          ]
        : [],
      page,
    },
    experiments: {
      items: started
        ? [
            {
              experiment: {
                type: 'experiment',
                id: 'EXP-6NRYG2G3MDMMT74S8B4SMZTRCV',
                version: null,
                revision: 1,
              },
              objective: 'Measure quality after costs.',
              experiment_type: 'FAST_BACKTEST',
              status: 'COMPLETED',
              validity_state: 'VALID',
              job_id: 'JOB-2J7AWCVZ7HE7FBZAP2E953VCJV',
              provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
              created_at: '2026-08-10T00:00:00Z',
            },
          ]
        : [],
      page,
    },
    evidence: { items: started ? [evidence] : [], page },
    artifacts: {
      items: started
        ? [
            {
              artifact: {
                type: 'artifact',
                id: 'ART-1BEQMVTP6047PP2Q1TPS7G2KHJ',
                version: null,
                revision: 1,
              },
              kind: 'BACKTEST_REPORT',
              media_type: 'application/json',
              sha256: 'a'.repeat(64),
              size_bytes: 4096,
              provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
              created_at: '2026-08-10T00:40:00Z',
            },
          ]
        : [],
      page,
    },
    audit: {
      items: started
        ? [
            {
              event_id: 'AUD-6HZ717E5J2JYZ34NS01M8X0PSQ',
              action: 'research.started',
              actor: { type: 'OWNER', id: 'owner' },
              object: {
                type: 'research',
                id: 'RSCH-399GM4EKDQ6VFNPE5EQ50HTV2J',
                version: null,
                revision: 2,
              },
              request_id: 'REQ-FLOW',
              provenance: { provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B' },
              occurred_at: '2026-08-10T00:10:00Z',
            },
          ]
        : [],
      page,
    },
  };
}

export const experimentProjection = {
  search_space: [
    {
      parameter_key: 'lookback',
      value_type: 'INTEGER',
      kind: 'SET',
      values: ['126', '252'],
      minimum: null,
      maximum: null,
      step: null,
    },
    {
      parameter_key: 'threshold',
      value_type: 'DECIMAL',
      kind: 'RANGE',
      values: [],
      minimum: '0.1',
      maximum: '0.5',
      step: '0.1',
    },
  ],
  search_configuration: {
    method: 'GRID',
    objective_metric_key: 'sharpe',
    objective_direction: 'MAXIMIZE',
    max_evaluations: 8,
    seed: null,
  },
  search_result: {
    state: 'COMPLETED',
    evaluated_count: 8,
    selected_parameters: [{ key: 'lookback', value: '252' }],
    selected_metric: { key: 'sharpe', value: '1.25', unit: null },
    result_ref: {
      type: 'artifact',
      id: 'ART-6W79PDP11JVACR1K6D31EZW82A',
      version: null,
      revision: 1,
    },
    failure_code: null,
  },
  metrics: [{ key: 'sharpe', value: '1.25', unit: null }],
  artifacts: [],
} satisfies Pick<
  Schema<'ExperimentDetail'>,
  'search_space' | 'search_configuration' | 'search_result' | 'metrics' | 'artifacts'
>;

type StrategyInput = Pick<
  Schema<'StrategyVersionDetail'>,
  | 'thesis'
  | 'universe'
  | 'signals'
  | 'rules'
  | 'cost_model_id'
  | 'benchmark'
  | 'research_period'
  | 'validation_period'
  | 'holdout_period'
  | 'known_failure_modes'
  | 'spec_sha256'
>;

export function strategyProjection(
  input: StrategyInput,
): Pick<
  Schema<'StrategyVersionDetail'>,
  'specification' | 'latest_backtest' | 'validation_summary' | 'artifacts' | 'provenance'
> {
  return {
    specification: { ...input },
    latest_backtest: { state: 'EMPTY', result: null, metrics: [], chart: null },
    validation_summary: null,
    artifacts: [],
    provenance: [{ provenance_id: 'PROV-0NDJSGSG241E2XGDSHF7TS1736' }],
  };
}
