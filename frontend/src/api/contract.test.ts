import { describe, expect, it, vi } from 'vitest';
import {
  api,
  auth,
  decodeCanonicalSseFrame,
  EVENT_QUERY_RULES,
  isSafeHoldoutNotification,
  queryKeysForEvent,
  queryPlanForEvent,
  workspaceQueryKey,
  type EventType,
  type Schema,
} from './client';
import { errorCopy } from '../ui';
import {
  CanonicalErrorCodeSchema,
  ConfigurationValueWriteSchema,
  ExperimentSearchDimensionSchema,
  ExperimentSearchResultSchema,
  EventObjectExamples,
  EventPayloadSchema,
  EventTypeObjectTypeMap,
  EventTypeSchema,
  EventWaitingOnSchema,
  SettingsDetailSchema,
  SetupStatusSchema,
  SseEnvelopeSchema,
} from './generated/runtime-schemas';

const readySetupStatus = {
  completed: false,
  owner_session_ready: true,
  ai_provider_configured: true,
  ai_connection_id: 'CONN-AI-1',
  data_provider_configured: false,
  research_policy_active: true,
  research_policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
  risk_policy_active: true,
  risk_policy_id: 'RISK-7TTN4TSTQB0FXPTV60RHR5P7NH',
  cost_model_active: true,
  cost_model_id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF',
  fallback_step: null,
} satisfies Schema<'SetupStatus'>;

const omit = (value: Record<string, unknown>, key: string): Record<string, unknown> =>
  Object.fromEntries(Object.entries(value).filter(([candidate]) => candidate !== key));

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
const policyFallback = {
  ...readySetupStatus,
  research_policy_active: false,
  research_policy_id: null,
  fallback_step: 'RESEARCH_CONSTITUTION',
} satisfies Schema<'SetupStatus'>;

const setupStatusMatrix: ReadonlyArray<readonly [string, unknown, boolean]> = [
  ['01 completed valid', { ...readySetupStatus, completed: true }, true],
  [
    '02 refs ready but session incomplete',
    { ...readySetupStatus, owner_session_ready: false },
    true,
  ],
  ['03 missing required fallback', omit(readySetupStatus, 'fallback_step'), false],
  ['04 unknown internal extra', { ...readySetupStatus, internal_policy_uuid: 'secret' }, false],
  ['05 AI true/null', { ...readySetupStatus, ai_connection_id: null }, false],
  [
    '06 AI false/non-null',
    { ...readySetupStatus, ai_provider_configured: false, fallback_step: 'AI_PROVIDER' },
    false,
  ],
  ['07 Research true/null', { ...readySetupStatus, research_policy_id: null }, false],
  [
    '08 Research false/non-null',
    { ...readySetupStatus, research_policy_active: false, fallback_step: 'RESEARCH_CONSTITUTION' },
    false,
  ],
  ['09 Risk true/null', { ...readySetupStatus, risk_policy_id: null }, false],
  [
    '10 Risk false/non-null',
    { ...readySetupStatus, risk_policy_active: false, fallback_step: 'RESEARCH_CONSTITUTION' },
    false,
  ],
  ['11 Cost true/null', { ...readySetupStatus, cost_model_id: null }, false],
  [
    '12 Cost false/non-null',
    { ...readySetupStatus, cost_model_active: false, fallback_step: 'RESEARCH_DEFAULTS' },
    false,
  ],
  [
    '13 completed/Owner contradiction',
    { ...readySetupStatus, completed: true, owner_session_ready: false },
    false,
  ],
  ['14 completed/ref contradiction', { ...costFallback, completed: true }, false],
  ['15 AI fallback', aiFallback, true],
  [
    '16 AI precedence',
    {
      ...aiFallback,
      cost_model_active: false,
      cost_model_id: null,
      research_policy_active: false,
      research_policy_id: null,
    },
    true,
  ],
  ['17 Cost fallback', costFallback, true],
  [
    '18 Cost precedence',
    {
      ...costFallback,
      research_policy_active: false,
      research_policy_id: null,
      risk_policy_active: false,
      risk_policy_id: null,
    },
    true,
  ],
  ['19 Policy fallback', policyFallback, true],
  ['20 all refs valid incomplete', readySetupStatus, true],
];

const settingsDetail = {
  active_revision: 3,
  last_known_good_revision: 3,
  catalog_version: 'v1',
  values: [],
  snapshot_sha256: 'a'.repeat(64),
  consumer_states: [],
  updated_at: '2026-08-10T00:01:00Z',
} satisfies Schema<'SettingsDetail'>;

const settingsDecoderCases: ReadonlyArray<readonly [string, unknown, boolean]> = [
  ['active configuration projection', settingsDetail, true],
  ['empty legacy projection rejected', {}, false],
  ['unknown persisted field rejected', { internal_owner_id: 'secret' }, false],
];

const eventEnvelope = (
  eventType: EventType,
  overrides: Partial<Schema<'SseEnvelope'>> = {},
): Schema<'SseEnvelope'> => {
  const objectType = EventTypeObjectTypeMap[eventType];
  return {
    schema_version: 1,
    event_id: 'EVT-7BSW7QFNPFN7FGSNW2WW07V82M',
    sequence: 1,
    occurred_at: '2026-08-10T00:00:00Z',
    object_type: objectType,
    ...EventObjectExamples[objectType],
    request_id: null,
    job_id: null,
    agent_run_id: null,
    tool_call_id: null,
    payload: {},
    ...overrides,
    event_type: eventType,
  };
};

describe('canonical transport', () => {
  it('enforces exactly one configuration value source', () => {
    expect(
      ConfigurationValueWriteSchema.safeParse({ key: 'runtime.mode', value: 'paper' }).success,
    ).toBe(true);
    expect(
      ConfigurationValueWriteSchema.safeParse({ key: 'runtime.mode', secret: 'encrypted' }).success,
    ).toBe(true);
    expect(
      ConfigurationValueWriteSchema.safeParse({
        key: 'runtime.mode',
        value: 'paper',
        secret: 'encrypted',
      }).success,
    ).toBe(false);
    expect(ConfigurationValueWriteSchema.safeParse({ key: 'runtime.mode' }).success).toBe(false);
  });

  it.each(setupStatusMatrix)('SetupStatus cases 01-20: %s', (_name, value, valid) => {
    expect(SetupStatusSchema.safeParse(value).success).toBe(valid);
  });

  it('SetupStatus case 03 rejects deletion of every new required ref/fallback field', () => {
    for (const key of ['research_policy_id', 'risk_policy_id', 'cost_model_id', 'fallback_step'])
      expect(SetupStatusSchema.safeParse(omit(readySetupStatus, key)).success).toBe(false);
  });

  it.each(settingsDecoderCases)('SettingsDetail closed decoder: %s', (_name, value, valid) => {
    expect(SettingsDetailSchema.safeParse(value).success).toBe(valid);
  });

  it('uses cookie session + CSRF for authenticated mutations', async () => {
    auth.establish({
      principal: 'OWNER',
      auth_method: 'GENERAL_ACCESS_KEY',
      key_id: 'gak_test',
      issued_at: '2026-08-10T00:00:00Z',
      last_seen_at: '2026-08-10T00:00:00Z',
      expires_at: '2026-08-11T00:00:00Z',
      csrf_token: 'csrf-token-abcdefghijklmnopqrstuvwxyz',
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          role_key: 'RESEARCH_DIRECTOR',
          enabled: false,
          model_provider: 'openai',
          model_name: 'gpt-test',
          ai_connection_id: 'CODEX-DEFAULT',
          ai_connection_revision: 1,
          runtime_profile: 'default',
          tool_timeout_seconds: 30,
          max_steps_override: null,
          max_tool_calls_override: null,
          revision: 3,
          action_capabilities: [],
          created_at: '2026-08-10T00:00:00Z',
          updated_at: '2026-08-10T00:00:00Z',
        } satisfies Schema<'AgentConfig'>),
        {
          status: 200,
          headers: { ETag: 'W/"agent:RESEARCH_DIRECTOR:3"' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    await api.updateAgent('RESEARCH_DIRECTOR', 'W/"agent:RESEARCH_DIRECTOR:3"', { enabled: false });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/agents/RESEARCH_DIRECTOR/config');
    expect(new Headers(init.headers).get('Authorization')).toBeNull();
    expect(new Headers(init.headers).get('X-CSRF-Token')).toBe(
      'csrf-token-abcdefghijklmnopqrstuvwxyz',
    );
    expect(init.credentials).toBe('include');
    expect(new Headers(init.headers).get('If-Match')).toBe('W/"agent:RESEARCH_DIRECTOR:3"');
  });

  it('maps all generated canonical errors', () => {
    expect(Object.keys(errorCopy)).toHaveLength(75);
    expect(CanonicalErrorCodeSchema.options).toHaveLength(75);
    expect(errorCopy.CONNECTION_VALIDATION_EXPIRED).toMatch(/expired/i);
  });

  it('SSE case 01 decodes all exact generated EventType members', () => {
    const eventTypes = EventTypeSchema.options.map((option) => option.value) as EventType[];
    expect(eventTypes).toHaveLength(35);
    expect(eventTypes.every((eventType) => eventType === eventType.toLowerCase())).toBe(true);
    for (const eventType of eventTypes)
      expect(SseEnvelopeSchema.safeParse(eventEnvelope(eventType)).success).toBe(true);
  });

  it('uses the production generated decoder for the exact wire cursor and rejects drift', () => {
    const event = eventEnvelope('research.updated', {
      sequence: 19,
      object_id: 'RSCH-5TVAJ93EJMXJXPPKEHE7YJGFVF',
    });
    expect(decodeCanonicalSseFrame(`id: 19\ndata: ${JSON.stringify(event)}`)).toEqual({
      cursor: 19,
      event,
    });
    expect(() => decodeCanonicalSseFrame(`id: 20\ndata: ${JSON.stringify(event)}`)).toThrow(
      'does not match',
    );
    expect(() =>
      decodeCanonicalSseFrame(`id: 19\ndata: ${JSON.stringify({ ...event, client_only: true })}`),
    ).toThrow('generated closed schema');
  });

  it('SSE case 02 has one generated compile-gated routing rule per EventType', () => {
    const eventTypes = EventTypeSchema.options.map((option) => option.value) as EventType[];
    expect(Object.keys(EVENT_QUERY_RULES)).toEqual(eventTypes);
    for (const eventType of eventTypes)
      expect(queryPlanForEvent(eventEnvelope(eventType))).toEqual(
        expect.objectContaining({ queryKeys: expect.any(Array) }),
      );
    expect(queryKeysForEvent(eventEnvelope('tool.call.updated'))).toEqual([
      workspaceQueryKey('overview'),
    ]);
    expect(
      queryKeysForEvent(
        eventEnvelope('tool.call.updated', { tool_call_id: 'TCALL-3N1BTANHV3ACWHTDYRWNPHNJCP' }),
      ),
    ).toEqual([
      workspaceQueryKey('tool-call', 'TCALL-3N1BTANHV3ACWHTDYRWNPHNJCP'),
      workspaceQueryKey('overview'),
    ]);
    expect(queryKeysForEvent(eventEnvelope('agent.run.updated'))).toEqual([
      workspaceQueryKey('overview'),
    ]);
    expect(
      queryKeysForEvent(
        eventEnvelope('agent.run.updated', { agent_run_id: 'ARUN-0J885BC0FRAJ76F3T3EKZP7VVH' }),
      ),
    ).toEqual([
      workspaceQueryKey('agent-run', 'ARUN-0J885BC0FRAJ76F3T3EKZP7VVH'),
      workspaceQueryKey('overview'),
    ]);
  });

  it('SSE case 03 rejects case drift', () => {
    expect(EventTypeSchema.safeParse('experiment.updated').success).toBe(true);
    for (const eventType of ['Experiment.Updated', 'EXPERIMENT.UPDATED', 'experiment.Updated'])
      expect(EventTypeSchema.safeParse(eventType).success).toBe(false);
  });

  it('SSE case 04 rejects an unknown future member', () => {
    expect(EventTypeSchema.safeParse('experiment.future_completed').success).toBe(false);
    expect(
      SseEnvelopeSchema.safeParse({
        ...eventEnvelope('experiment.updated'),
        event_type: 'experiment.future_completed',
      }).success,
    ).toBe(false);
  });

  it('SSE case 05 rejects every schema version except 1', () => {
    for (const schemaVersion of [0, 2, 999])
      expect(
        SseEnvelopeSchema.safeParse({
          ...eventEnvelope('job.updated'),
          schema_version: schemaVersion,
        }).success,
      ).toBe(false);
  });

  it('SSE case 06 keeps the envelope closed and every generated field required', () => {
    const event = eventEnvelope('job.updated');
    expect(SseEnvelopeSchema.safeParse({ ...event, client_only: true }).success).toBe(false);
    for (const key of Object.keys(SseEnvelopeSchema.shape))
      expect(SseEnvelopeSchema.safeParse(omit(event, key)).success).toBe(false);
  });

  it('SSE case 07 keeps EventPayload closed', () => {
    expect(EventPayloadSchema.safeParse({ state: 'RUNNING' }).success).toBe(true);
    expect(EventPayloadSchema.safeParse({ state: 'RUNNING', metric: '9.99' }).success).toBe(false);
    expect(
      SseEnvelopeSchema.safeParse({
        ...eventEnvelope('experiment.updated'),
        payload: { state: 'RUNNING', leaked: true },
      }).success,
    ).toBe(false);
  });

  it('SSE case 08 accepts exact waiting-on and routes only its known active Job key', () => {
    const waitingOn = { type: 'JOB', job_id: 'JOB-0QAJSVRMV1KQSB49YFQHZJ72JK' } as const;
    expect(EventWaitingOnSchema.safeParse(waitingOn).success).toBe(true);
    const event = eventEnvelope('research.updated', { payload: { waiting_on: waitingOn } });
    expect(SseEnvelopeSchema.safeParse(event).success).toBe(true);
    expect(queryKeysForEvent(event)).toContainEqual(
      workspaceQueryKey('job', 'JOB-0QAJSVRMV1KQSB49YFQHZJ72JK'),
    );
  });

  it('SSE case 09 rejects missing, non-const, and wrong-scalar waiting-on', () => {
    for (const waitingOn of [
      { job_id: 'JOB-73MTX6YMDRFAZNRRNVCQDSQYH8' },
      { type: 'JOB' },
      { type: 'AGENT', job_id: 'JOB-73MTX6YMDRFAZNRRNVCQDSQYH8' },
      { type: 'JOB', job_id: 1 },
    ])
      expect(EventWaitingOnSchema.safeParse(waitingOn).success).toBe(false);
  });

  it('SSE case 10 rejects waiting-on extra fields without constructing their keys', () => {
    const waitingOn = {
      type: 'JOB',
      job_id: 'JOB-73MTX6YMDRFAZNRRNVCQDSQYH8',
      object_id: 'EXP-5M931VPS47ACN5XT12773AK2DV',
    };
    expect(EventWaitingOnSchema.safeParse(waitingOn).success).toBe(false);
    expect(
      SseEnvelopeSchema.safeParse({
        ...eventEnvelope('job.updated'),
        payload: { waiting_on: waitingOn },
      }).success,
    ).toBe(false);
  });

  it('SSE case 11 accepts Holdout gate-only notification metadata', () => {
    const event = eventEnvelope('validation.holdout.updated', {
      object_id: 'VAL-6TPZY7STMTB0WNYQWYXSF1CWN0',
      payload: { state: 'LOCKED', reason_code: 'HOLDOUT_LOCKED' },
    });
    expect(SseEnvelopeSchema.safeParse(event).success).toBe(true);
    expect(isSafeHoldoutNotification(event)).toBe(true);
    expect(queryKeysForEvent(event)).toEqual([
      workspaceQueryKey('validation', 'VAL-6TPZY7STMTB0WNYQWYXSF1CWN0'),
      workspaceQueryKey('holdout', 'VAL-6TPZY7STMTB0WNYQWYXSF1CWN0'),
      workspaceQueryKey('holdout-result', 'VAL-6TPZY7STMTB0WNYQWYXSF1CWN0'),
    ]);
  });

  it('SSE case 12 rejects Holdout result/raw fields at schema or semantic boundary', () => {
    for (const leaked of [
      { metric: 'sharpe', value: '9.99' },
      { chart_point: { x: 1, y: 2 } },
      { credential: 'secret' },
      { raw_model_output: 'secret' },
    ])
      expect(EventPayloadSchema.safeParse(leaked).success).toBe(false);
    for (const leaked of [
      { objective: 'raw model output' },
      { progress_mode: 'NONE' as const },
      { completed_units: 1 },
      { current_step_key: 'secret result' },
      { research_id: 'RSCH-6VRN7G575SCV71N44X2QKR19EK' },
      { waiting_on: { type: 'JOB' as const, job_id: 'JOB-18SZH2JPA9AZ0Y6NWXZ0ZXT3FJ' } },
    ])
      expect(
        isSafeHoldoutNotification(eventEnvelope('validation.holdout.updated', { payload: leaked })),
      ).toBe(false);
  });

  it('SSE case 14 routes experiment.created to active child, Research, list, and Overview', () => {
    const event = eventEnvelope('experiment.created', {
      object_id: 'EXP-1M49GS2TJYQ2JPYV54YDGY7R59',
      payload: { research_id: 'RSCH-5TVAJ93EJMXJXPPKEHE7YJGFVF' },
    });
    expect(queryKeysForEvent(event)).toEqual([
      workspaceQueryKey('research', 'RSCH-5TVAJ93EJMXJXPPKEHE7YJGFVF'),
      workspaceQueryKey('research'),
      workspaceQueryKey('experiment', 'EXP-1M49GS2TJYQ2JPYV54YDGY7R59'),
      workspaceQueryKey('overview'),
    ]);
  });

  it('SSE case 15 routes experiment.updated to active detail, owning Research, and Overview', () => {
    const event = eventEnvelope('experiment.updated', {
      object_id: 'EXP-1M49GS2TJYQ2JPYV54YDGY7R59',
      payload: { research_id: 'RSCH-5TVAJ93EJMXJXPPKEHE7YJGFVF' },
    });
    expect(queryKeysForEvent(event)).toEqual([
      workspaceQueryKey('experiment', 'EXP-1M49GS2TJYQ2JPYV54YDGY7R59'),
      workspaceQueryKey('research', 'RSCH-5TVAJ93EJMXJXPPKEHE7YJGFVF'),
      workspaceQueryKey('overview'),
    ]);
  });

  it('validates both canonical search dimension variants', () => {
    const validDimensions: Schema<'ExperimentSearchDimension'>[] = [
      {
        parameter_key: 'window',
        value_type: 'INTEGER',
        kind: 'SET',
        values: ['20', '60'],
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
      {
        parameter_key: 'window',
        value_type: 'INTEGER',
        kind: 'RANGE',
        values: [],
        minimum: '20',
        maximum: '100',
        step: '20',
      },
    ];
    expect(
      validDimensions.every((value) => ExperimentSearchDimensionSchema.safeParse(value).success),
    ).toBe(true);
    const invalidDimensions = [
      { ...validDimensions[0], values: [] },
      { ...validDimensions[0], values: ['20', '20'] },
      { ...validDimensions[0], minimum: '1' },
      { ...validDimensions[1], minimum: '0.5', maximum: '0.1' },
      {
        ...validDimensions[1],
        minimum: '100000000000000000000.1',
        maximum: '100000000000000000000.01',
      },
      {
        ...validDimensions[1],
        minimum: '0.00000000000000000002',
        maximum: '0.00000000000000000002',
      },
      { ...validDimensions[1], step: '0' },
      { ...validDimensions[2], step: '0.5' },
      { ...validDimensions[2], values: ['20'] },
      { ...validDimensions[2], client_only: true },
    ];
    expect(
      invalidDimensions.every((value) => !ExperimentSearchDimensionSchema.safeParse(value).success),
    ).toBe(true);
  });

  it('validates all five mutually exclusive search-result states', () => {
    const states: Schema<'ExperimentSearchResult'>[] = [
      {
        state: 'NOT_APPLICABLE',
        evaluated_count: 0,
        selected_parameters: [],
        selected_metric: null,
        result_ref: null,
        failure_code: null,
      },
      {
        state: 'PENDING',
        evaluated_count: 0,
        selected_parameters: [],
        selected_metric: null,
        result_ref: null,
        failure_code: null,
      },
      {
        state: 'RUNNING',
        evaluated_count: 2,
        selected_parameters: [],
        selected_metric: null,
        result_ref: null,
        failure_code: null,
      },
      {
        state: 'COMPLETED',
        evaluated_count: 4,
        selected_parameters: [{ key: 'window', value: '60' }],
        selected_metric: { key: 'sharpe', value: '1.1', unit: null },
        result_ref: {
          type: 'artifact',
          id: 'ART-6W79PDP11JVACR1K6D31EZW82A',
          version: null,
          revision: 1,
        },
        failure_code: null,
      },
      {
        state: 'FAILED',
        evaluated_count: 2,
        selected_parameters: [],
        selected_metric: null,
        result_ref: null,
        failure_code: 'JOB_FAILED',
      },
    ];
    expect(states.every((value) => ExperimentSearchResultSchema.safeParse(value).success)).toBe(
      true,
    );
    expect(
      ExperimentSearchResultSchema.safeParse({ ...states[1], evaluated_count: 1 }).success,
    ).toBe(false);
    expect(
      ExperimentSearchResultSchema.safeParse({ ...states[3], selected_parameters: [] }).success,
    ).toBe(false);
    expect(
      ExperimentSearchResultSchema.safeParse({ ...states[4], failure_code: null }).success,
    ).toBe(false);
  });
});
