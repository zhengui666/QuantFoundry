import { expect, test } from 'playwright/test';
import type { Schema } from '../src/api/client';

const overview = () =>
  ({
    as_of: '2026-08-10T00:00:00Z',
    revision: 1,
    needs_attention: [],
    active_research: [],
    strategy_pipeline: { candidate: 0, frozen: 0, validating: 0, validated: 0, paper: 0 },
    paper_summary: {
      active_count: 0,
      total_nav: null,
      currency: 'USD',
      daily_return: null,
      mtd_return: null,
      since_start_return: null,
      benchmark_since_start_return: null,
      as_of_date: null,
      provenance: null,
    },
    paper_performance_chart: null,
    recent_findings: [],
    agent_activity: [],
    data_health: {
      state: 'HEALTHY',
      blocker_count: 0,
      warning_count: 0,
      checked_at: '2026-08-10T00:00:00Z',
      action_capabilities: [],
    },
    provenance: [],
    action_capabilities: [],
  }) satisfies Schema<'OverviewReadModel'>;

const problem = {
  type: 'about:blank',
  title: 'Unauthenticated',
  status: 401,
  code: 'UNAUTHENTICATED',
  detail: 'Token required.',
  instance: null,
  request_id: 'REQ-AUTH-SCOPE',
  retryable: false,
  field_errors: [],
  context: {},
} satisfies Schema<'ApiProblem'>;

test('WA reload WB isolates opaque cursor/dedupe scope for equal SSE sequence', async ({
  page,
}) => {
  const streamHeaders: Array<{
    authorization: string | undefined;
    lastEventId: string | undefined;
  }> = [];
  const overviewHeaders: string[] = [];
  const delivered = new Set<string>();
  let releaseWorkspaceA: () => void = () => undefined;
  let releaseWorkspaceB: () => void = () => undefined;
  const workspaceAGate = new Promise<void>((resolve) => {
    releaseWorkspaceA = resolve;
  });
  const workspaceBGate = new Promise<void>((resolve) => {
    releaseWorkspaceB = resolve;
  });
  await page.route('**/api/v1/events/stream', async (route) => {
    const headers = route.request().headers();
    streamHeaders.push({
      authorization: headers.authorization,
      lastEventId: headers['last-event-id'],
    });
    if (!headers.authorization || delivered.has(headers.authorization))
      return route.fulfill({ contentType: 'text/event-stream', body: '' });
    await (headers.authorization === 'Bearer workspace-a' ? workspaceAGate : workspaceBGate);
    delivered.add(headers.authorization);
    const workspace = headers.authorization === 'Bearer workspace-a' ? 'A' : 'B';
    const jobId =
      workspace === 'A' ? 'JOB-73MTX6YMDRFAZNRRNVCQDSQYH8' : 'JOB-0QAJSVRMV1KQSB49YFQHZJ72JK';
    const event = {
      schema_version: 1,
      event_id:
        workspace === 'A' ? 'EVT-7BSW7QFNPFN7FGSNW2WW07V82M' : 'EVT-4V9MRDSPQPS3YCZXZ34PBT306X',
      sequence: 7,
      event_type: 'job.updated',
      occurred_at: '2026-08-10T00:00:00Z',
      object_type: 'job',
      object_id: jobId,
      object_version: null,
      object_revision: 1,
      request_id: null,
      job_id: jobId,
      agent_run_id: null,
      tool_call_id: null,
      payload: {},
    } satisfies Schema<'SseEnvelope'>;
    return route.fulfill({
      contentType: 'text/event-stream',
      body: headers.authorization
        ? `id: ${event.sequence}\ndata: ${JSON.stringify(event)}\n\n`
        : '',
    });
  });
  await page.route('**/api/v1/overview', (route) => {
    const authorization = route.request().headers().authorization;
    overviewHeaders.push(authorization ?? 'none');
    if (!authorization)
      return route.fulfill({ status: 401, contentType: 'application/problem+json', json: problem });
    return route.fulfill({ json: overview() });
  });

  await page.goto('/overview');
  await page.getByLabel('Bearer token').fill('workspace-a');
  const workspaceAInitialRead = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/v1/overview' &&
      response.request().headers().authorization === 'Bearer workspace-a' &&
      response.status() === 200,
  );
  await page.getByRole('button', { name: 'Authenticate' }).click();
  await workspaceAInitialRead;
  const workspaceAEventRead = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/v1/overview' &&
      response.request().headers().authorization === 'Bearer workspace-a' &&
      response.status() === 200,
  );
  releaseWorkspaceA();
  await workspaceAEventRead;
  await expect
    .poll(() =>
      page.evaluate(() =>
        Object.keys(sessionStorage).filter((key) => key.startsWith('qf.sse.cursor:')),
      ),
    )
    .toHaveLength(1);
  const workspaceAReads = overviewHeaders.filter((value) => value === 'Bearer workspace-a').length;

  await page.reload();
  await expect
    .poll(() =>
      page.evaluate(() =>
        Object.keys(sessionStorage).filter((key) => key.startsWith('qf.sse.cursor:')),
      ),
    )
    .toHaveLength(0);
  await page.getByLabel('Bearer token').fill('workspace-b');
  const workspaceBInitialRead = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/v1/overview' &&
      response.request().headers().authorization === 'Bearer workspace-b' &&
      response.status() === 200,
  );
  await page.getByRole('button', { name: 'Authenticate' }).click();
  await workspaceBInitialRead;
  const workspaceBEventRead = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/v1/overview' &&
      response.request().headers().authorization === 'Bearer workspace-b' &&
      response.status() === 200,
  );
  releaseWorkspaceB();
  await workspaceBEventRead;

  const workspaceBStreams = streamHeaders.filter(
    ({ authorization }) => authorization === 'Bearer workspace-b',
  );
  expect(workspaceBStreams.length).toBeGreaterThan(0);
  expect(workspaceBStreams.every(({ lastEventId }) => lastEventId === undefined)).toBe(true);
  expect(overviewHeaders.filter((value) => value === 'Bearer workspace-a')).toHaveLength(
    workspaceAReads,
  );
});
