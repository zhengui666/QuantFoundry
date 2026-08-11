import AxeBuilder from '@axe-core/playwright';
import { expect, test } from 'playwright/test';
import type { Schema } from '../src/api/client';
import { experimentProjection } from './fixture-builders';

const reproduceCapability = {
  action: 'reproduce',
  visibility: 'SHOW',
  allowed: true,
  reason_code: null,
  reason_detail: null,
  requires_confirmation: true,
  idempotency_required: true,
  if_match_required: false,
  result_mode: 'JOB',
  danger_level: 'STATE_CHANGE',
} satisfies Schema<'ActionCapability'>;

const provenance = {
  provenance_id: 'PROV-5C09CNJ1HB51GMZ29VSV9KK8NM',
  schema_version: 1,
  experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
  source_experiment_id: null,
  tool_call_id: 'TCALL-3C56HJV662Q8B0CRDS9TMFWA1D',
  data_snapshot_ids: ['DS-6MP2ZFH625DXBRY8T9E53FP9E0'],
  engine: { name: 'factor-engine', version: '1.0.0' },
  adapter: { name: 'market-adapter', version: '2.0.0' },
  code: { commit: 'abc123', build_id: 'build-1' },
  policies: [{ type: 'research_policy', id: 'RP-756FFQA659A84RCEVR0M9X8DMN', version: 1 }],
  strategy: null,
  factors: [],
  cost_model: { id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF', version: 1, sha256: 'c'.repeat(64) },
  parameters_sha256: 'a'.repeat(64),
  input_sha256: 'b'.repeat(64),
  output_sha256: 'd'.repeat(64),
  calculated_at: '2026-08-10T01:00:00Z',
} satisfies Schema<'Provenance'>;

const source = {
  experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
  research_id: 'RSCH-7ZB18YZVDQZ6QCPE22E86T0AMK',
  parent_experiment_id: null,
  source_experiment_id: null,
  research_revision_no: 1,
  objective: 'Reproduce a canonical result.',
  hypothesis: 'The result is deterministic.',
  experiment_type: 'FACTOR_ANALYSIS',
  status: 'COMPLETED',
  validity_state: 'VALID',
  data_snapshot_id: 'DS-6MP2ZFH625DXBRY8T9E53FP9E0',
  factor_ref: { id: 'FAC-701PW0JDPSYYMVWDY210EKMTVQ', version: 1 },
  strategy_ref: null,
  cost_model_id: 'COST-0QY70GRXXGT2HVM7HY8TMPXMVF',
  parameters: [{ key: 'lookback', value: '252' }],
  parameters_sha256: 'a'.repeat(64),
  ...experimentProjection,
  engine: { name: 'factor-engine', version: '1.0.0' },
  adapter: { name: 'market-adapter', version: '2.0.0' },
  code_version: 'abc123',
  job_id: 'JOB-0MG0J89T1AYNZ1F44ZXBVFFSVC',
  provenance,
  action_capabilities: [reproduceCapability],
  started_at: '2026-08-10T00:00:00Z',
  finished_at: '2026-08-10T01:00:00Z',
  created_at: '2026-08-10T00:00:00Z',
  invalidated_at: null,
  invalid_reason_code: null,
  invalid_reason_detail: null,
} satisfies Schema<'ExperimentDetail'>;

const accepted = (mode: 'EXACT' | 'CONTROLLED_OVERRIDE', index: number) =>
  ({
    job_id: [
      'JOB-56D0P46J719PSN3R3RPM9HZTAM',
      'JOB-2S8JHC91CK3R0NKX15T6PYVMWE',
      'JOB-4TKZAW16F5YJDE90SKRB8GX2CP',
      'JOB-1NV6QDYEFP4ZTCW3HJK7M8RXSA',
    ][index - 1]!,
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
      id: [
        'EXP-71H3WFBVC6Q951EGTPH30V511H',
        'EXP-5KRA9DBWKB97YSNVGPVZA2GP9X',
        'EXP-6VSXK4JYZ68KABY4XSWZ9MTNQD',
        'EXP-4P36Q6N0XJZ9DYTC98WDES2HTG',
      ][index - 1]!,
      version: null,
      revision: 1,
    },
    source_experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
    source_provenance: { provenance_id: 'PROV-5C09CNJ1HB51GMZ29VSV9KK8NM' },
    reproduce_mode: mode,
    created_at: '2026-08-10T02:00:00Z',
  }) satisfies Schema<'ExperimentReproduceAccepted'>;

test('P05 SSE refetches the active Experiment from REST without enumerating inactive related IDs', async ({
  page,
}) => {
  let releaseStream: () => void = () => {};
  const streamGate = new Promise<void>((resolve) => {
    releaseStream = resolve;
  });
  let experimentReads = 0;
  let streamReleased = false;
  let inactiveExperimentReads = 0;
  let researchReads = 0;
  let toolCallReads = 0;
  const envelope = (
    sequence: number,
    eventType: Schema<'EventType'>,
    objectId: string,
    payload: Schema<'EventPayload'>,
    references: Pick<Schema<'SseEnvelope'>, 'agent_run_id' | 'job_id' | 'tool_call_id'> = {
      agent_run_id: null,
      job_id: null,
      tool_call_id: null,
    },
  ) =>
    ({
      schema_version: 1,
      event_id: [
        'EVT-7BSW7QFNPFN7FGSNW2WW07V82M',
        'EVT-4V9MRDSPQPS3YCZXZ34PBT306X',
        'EVT-2MVNBFRCR3VPGS5KQKF2F77FS7',
      ][sequence - 1]!,
      sequence,
      event_type: eventType,
      occurred_at: '2026-08-10T02:00:00Z',
      object_type: eventType.startsWith('experiment.') ? 'experiment' : 'tool_call',
      object_id: objectId,
      object_version: null,
      object_revision: sequence,
      request_id: null,
      ...references,
      payload,
    }) satisfies Schema<'SseEnvelope'>;
  const events = [
    envelope(1, 'experiment.updated', 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ', {
      research_id: 'RSCH-2X7WEJGQ3P414SWYH7HPF6ZVXK',
    }),
    envelope(2, 'experiment.created', 'EXP-1CSBAC5ADP9XC06NZ7J2JFDBWT', {
      research_id: 'RSCH-2X7WEJGQ3P414SWYH7HPF6ZVXK',
    }),
    envelope(
      3,
      'tool.call.updated',
      'TCALL-6FP37K9CABFDSDGXSGQ69S4F7V',
      {},
      {
        agent_run_id: null,
        job_id: null,
        tool_call_id: 'TCALL-6FP37K9CABFDSDGXSGQ69S4F7V',
      },
    ),
  ];
  await page.route('**/api/v1/events/stream', async (route) => {
    await streamGate;
    return route.fulfill({
      contentType: 'text/event-stream',
      body: events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(''),
    });
  });
  await page.route('**/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ', (route) => {
    experimentReads += 1;
    return route.fulfill({
      json: {
        ...source,
        objective: streamReleased
          ? 'REST server truth after SSE.'
          : 'Reproduce a canonical result.',
      } satisfies Schema<'ExperimentDetail'>,
    });
  });
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path === '/api/v1/experiments/EXP-1CSBAC5ADP9XC06NZ7J2JFDBWT') inactiveExperimentReads += 1;
    if (path === '/api/v1/research/RSCH-2X7WEJGQ3P414SWYH7HPF6ZVXK') researchReads += 1;
    if (path === '/api/v1/tool-calls/TCALL-6FP37K9CABFDSDGXSGQ69S4F7V') toolCallReads += 1;
  });
  await page.goto('/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ');
  await expect(page.getByText('Reproduce a canonical result.')).toBeVisible();
  streamReleased = true;
  releaseStream();
  await expect.poll(() => experimentReads).toBeGreaterThan(1);
  await expect(page.getByText('REST server truth after SSE.')).toBeVisible();
  expect({ inactiveExperimentReads, researchReads, toolCallReads }).toEqual({
    inactiveExperimentReads: 0,
    researchReads: 0,
    toolCallReads: 0,
  });
});

test('P05 uses only dedicated EXACT/CONTROLLED_OVERRIDE reproduce with Location and server job truth', async ({
  page,
}) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ contentType: 'text/event-stream', body: '' }),
  );
  const bodies: unknown[] = [];
  const keys: string[] = [];
  let createExperimentCalls = 0;
  let childReads = 0;
  await page.route('**/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ', (route) =>
    route.fulfill({ json: source, headers: { ETag: 'W/"experiment:1"' } }),
  );
  await page.route(
    '**/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ/reproduce',
    async (route) => {
      const body = await route.request().postDataJSON();
      bodies.push(body);
      keys.push(route.request().headers()['idempotency-key'] ?? '');
      const mode =
        (body as { mode?: string }).mode === 'CONTROLLED_OVERRIDE'
          ? 'CONTROLLED_OVERRIDE'
          : 'EXACT';
      const response = accepted(mode, bodies.length);
      return route.fulfill({
        status: 202,
        json: response,
        headers: { Location: `/api/v1/experiments/${response.resource_ref.id}` },
      });
    },
  );
  await page.route('**/api/v1/jobs/*', (route) =>
    route.fulfill({
      json: {
        job_id: route.request().url().split('/').at(-1) ?? '',
        job_type: 'EXPERIMENT_REPRODUCE',
        status: 'COMPLETED',
        progress: {
          mode: 'UNITS',
          completed_units: 1,
          total_units: 2,
          unit: 'steps',
          percent: 50,
          current_step_key: 'execute',
          current_step_label: 'Execute',
        },
        error_code: null,
        result_ref: {
          object_type: 'experiment',
          object_id: 'EXP-41JM536P4NGX0WHHTHVFZGPFVB',
          object_version: null,
          object_revision: 1,
          artifact_id: null,
        },
        queued_at: '2026-08-10T02:00:00Z',
        started_at: '2026-08-10T02:00:01Z',
        finished_at: '2026-08-10T02:00:03Z',
        last_updated_at: '2026-08-10T02:00:02Z',
        revision: 1,
      } satisfies Schema<'JobDetail'>,
    }),
  );
  await page.route(
    /\/api\/v1\/experiments\/(?:EXP-71H3WFBVC6Q951EGTPH30V511H|EXP-5KRA9DBWKB97YSNVGPVZA2GP9X)$/,
    (route) => {
      childReads += 1;
      const childId = route.request().url().split('/').at(-1) ?? 'EXP-41JM536P4NGX0WHHTHVFZGPFVB';
      return route.fulfill({
        json: {
          ...source,
          experiment_id: childId,
          parent_experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
          source_experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
          job_id: null,
          provenance: {
            ...provenance,
            provenance_id: 'PROV-1MX2RQZ9EAP4CBTG7KH5W6DNVS',
            experiment_id: childId,
            source_experiment_id: 'EXP-4B0ZYVEPMH387DV8TG6244X6NZ',
          },
        } satisfies Schema<'ExperimentDetail'>,
      });
    },
  );
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/experiments')
      createExperimentCalls += 1;
  });

  await page.goto('/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ');
  await page.getByRole('button', { name: 'Reproduce' }).click();
  const exactDialog = page.getByRole('dialog', { name: 'Confirm experiment reproduction' });
  await expect(exactDialog).toContainText('DS-6MP2ZFH625DXBRY8T9E53FP9E0');
  await expect(exactDialog).toContainText('factor-engine');
  await exactDialog.getByRole('button', { name: 'Confirm reproduce' }).click();
  await expect(
    page.getByText(/Reproduce EXACT accepted as job JOB-56D0P46J719PSN3R3RPM9HZTAM · COMPLETED/),
  ).toBeVisible();
  expect(bodies[0]).toEqual({ mode: 'EXACT' });
  await expect.poll(() => childReads).toBeGreaterThan(0);

  await page.getByRole('button', { name: 'Reproduce' }).click();
  const overrideDialog = page.getByRole('dialog', { name: 'Confirm experiment reproduction' });
  await overrideDialog.getByLabel('Reproduce mode').selectOption('CONTROLLED_OVERRIDE');
  await overrideDialog.getByLabel('Engine version').fill('1.1.0');
  await overrideDialog.getByLabel('Adapter version').fill('2.1.0');
  await overrideDialog.getByLabel('Code version').fill('def456');
  await overrideDialog.getByLabel('Required reason').fill('Verify the next engine patch.');
  await overrideDialog.getByRole('button', { name: 'Confirm reproduce' }).click();
  await expect(
    page.getByText(
      /Reproduce CONTROLLED_OVERRIDE accepted as job JOB-2S8JHC91CK3R0NKX15T6PYVMWE · COMPLETED/,
    ),
  ).toBeVisible();
  expect(bodies[1]).toEqual({
    mode: 'CONTROLLED_OVERRIDE',
    execution_overrides: {
      engine_version: '1.1.0',
      adapter_version: '2.1.0',
      code_version: 'def456',
    },
    reason: 'Verify the next engine patch.',
  });
  expect(keys.every(Boolean)).toBe(true);
  expect(new Set(keys).size).toBe(2);
  expect(createExperimentCalls).toBe(0);
  await expect(page.getByRole('button', { name: /Rerun/ })).toBeDisabled();
  await expect(page.getByText('View provenance').first()).toHaveAttribute(
    'href',
    /\/experiments\/EXP-4B0ZYVEPMH387DV8TG6244X6NZ\?tab=summary&focus=provenance&toolCallId=TCALL-3C56HJV662Q8B0CRDS9TMFWA1D/,
  );
  await page.getByRole('tab', { name: 'Inputs' }).click();
  await expect(page.getByText('original experiment')).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.map((violation) => violation.id)).toEqual([]);
});

test('P05 capability SHOW deny disables Reproduce and HIDE removes it without network calls', async ({
  page,
}) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ contentType: 'text/event-stream', body: '' }),
  );
  let reproduceCalls = 0;
  await page.route('**/api/v1/experiments/EXP-49GFTKSQ21XBWMXEEN8CY6KNX3', (route) =>
    route.fulfill({
      json: {
        ...source,
        experiment_id: 'EXP-49GFTKSQ21XBWMXEEN8CY6KNX3',
        action_capabilities: [
          {
            ...reproduceCapability,
            allowed: false,
            reason_code: 'NON_REPRODUCIBLE',
            reason_detail: 'Source lineage is incomplete.',
          },
        ],
      } satisfies Schema<'ExperimentDetail'>,
    }),
  );
  await page.route('**/api/v1/experiments/EXP-11Z9XP61Z9MY000VNS1MVES4T4', (route) =>
    route.fulfill({
      json: {
        ...source,
        experiment_id: 'EXP-11Z9XP61Z9MY000VNS1MVES4T4',
        action_capabilities: [{ ...reproduceCapability, visibility: 'HIDE' }],
      } satisfies Schema<'ExperimentDetail'>,
    }),
  );
  await page.route('**/api/v1/experiments/*/reproduce', (route) => {
    reproduceCalls += 1;
    return route.abort();
  });

  await page.goto('/experiments/EXP-49GFTKSQ21XBWMXEEN8CY6KNX3');
  const denied = page.getByRole('button', { name: /Reproduce/ });
  await expect(denied).toBeDisabled();
  await expect(denied).toHaveAttribute('title', 'Source lineage is incomplete.');
  await page.goto('/experiments/EXP-11Z9XP61Z9MY000VNS1MVES4T4');
  await expect(page.getByRole('button', { name: /^Reproduce/ })).toHaveCount(0);
  expect(reproduceCalls).toBe(0);
});

test('P05 preserves intent key through IDEMPOTENCY_IN_PROGRESS replay and shows conflict', async ({
  page,
}) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ contentType: 'text/event-stream', body: '' }),
  );
  const keys: string[] = [];
  let calls = 0;
  await page.route('**/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ', (route) =>
    route.fulfill({ json: source }),
  );
  await page.route('**/api/v1/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ/reproduce', (route) => {
    calls += 1;
    keys.push(route.request().headers()['idempotency-key'] ?? '');
    if (calls === 1)
      return route.fulfill({
        status: 409,
        json: {
          type: 'about:blank',
          title: 'In progress',
          status: 409,
          code: 'IDEMPOTENCY_IN_PROGRESS',
          detail: 'The original request is processing.',
          instance: null,
          request_id: 'REQ-PROCESSING',
          retryable: false,
          field_errors: [],
          context: {},
        } satisfies Schema<'ApiProblem'>,
      });
    return route.fulfill({
      status: 409,
      json: {
        type: 'about:blank',
        title: 'Conflict',
        status: 409,
        code: 'IDEMPOTENCY_CONFLICT',
        detail: 'The replay payload conflicts.',
        instance: null,
        request_id: 'REQ-CONFLICT',
        retryable: false,
        field_errors: [],
        context: {},
      } satisfies Schema<'ApiProblem'>,
    });
  });
  await page.goto('/experiments/EXP-4B0ZYVEPMH387DV8TG6244X6NZ');
  await page.getByRole('button', { name: 'Reproduce' }).click();
  const dialog = page.getByRole('dialog', { name: 'Confirm experiment reproduction' });
  await dialog.getByRole('button', { name: 'Confirm reproduce' }).click();
  await expect(dialog.getByText(/prior request is still being processed/i)).toBeVisible();
  await dialog.getByRole('button', { name: 'Confirm reproduce' }).click();
  await expect(dialog.getByText(/conflicts with an earlier submission/i)).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});
