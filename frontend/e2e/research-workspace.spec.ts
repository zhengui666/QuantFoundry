import { expect, test } from 'playwright/test';
import type { Schema } from '../src/api/client';
import { researchProjection } from './fixture-builders';

const researchId = 'RSCH-399GM4EKDQ6VFNPE5EQ50HTV2J';
const emptyResearch = {
  research_id: researchId,
  title: 'Four-state workspace',
  original_user_prompt: 'Test typed workspace states.',
  normalized_question: null,
  status: 'DRAFT',
  evidence_status: 'INSUFFICIENT',
  current_revision_no: 1,
  active_plan_version: null,
  research_policy_id: 'RP-756FFQA659A84RCEVR0M9X8DMN',
  director_agent_version: null,
  current_agent_run_id: null,
  current_job_id: null,
  ...researchProjection(false),
  revision: 1,
  action_capabilities: [],
  created_at: '2026-08-10T00:00:00Z',
  updated_at: '2026-08-10T00:00:00Z',
  completed_at: null,
} satisfies Schema<'ResearchDetail'>;

const problem = {
  type: 'about:blank',
  title: 'Workspace unavailable',
  status: 503,
  code: 'SERVICE_DEGRADED',
  detail: 'Canonical research projection is temporarily unavailable.',
  instance: null,
  request_id: 'REQ-P04-FOUR-STATE',
  retryable: true,
  field_errors: [],
  context: {},
} satisfies Schema<'ApiProblem'>;

const tabs = [
  ['overview', 'Overview', /No current conclusion in server truth/],
  ['plan', 'Plan', /No research plan in server truth/],
  ['timeline', 'Timeline', /No timeline events in server truth/],
  ['experiments', 'Experiments', /No experiments in server truth/],
  ['evidence', 'Evidence', /No evidence in server truth/],
  ['artifacts', 'Artifacts', /No artifacts in server truth/],
  ['audit', 'Audit', /No audit events in server truth/],
] as const;

for (const [tab, label, emptyCopy] of tabs) {
  test(`P04 ${label} preserves URL and stable container across loading/empty/revalidating/Problem`, async ({
    page,
  }) => {
    let releaseInitial: () => void = () => {};
    const initialGate = new Promise<void>((resolve) => {
      releaseInitial = resolve;
    });
    let releaseRefetch: () => void = () => {};
    const refetchGate = new Promise<void>((resolve) => {
      releaseRefetch = resolve;
    });
    let releaseStream: () => void = () => {};
    const streamGate = new Promise<void>((resolve) => {
      releaseStream = resolve;
    });
    let reads = 0;
    let initialReleased = false;
    let holdRefetch = false;
    let errorMode = false;
    await page.route(`**/api/v1/research/${researchId}`, async (route) => {
      reads += 1;
      if (errorMode)
        return route.fulfill({
          status: 503,
          contentType: 'application/problem+json',
          json: problem,
        });
      if (!initialReleased) await initialGate;
      if (holdRefetch) await refetchGate;
      return route.fulfill({ json: emptyResearch, headers: { ETag: 'W/"research:1"' } });
    });
    await page.route('**/api/v1/events/stream', async (route) => {
      await streamGate;
      const event = {
        schema_version: 1,
        event_id: 'EVT-7BSW7QFNPFN7FGSNW2WW07V82M',
        sequence: 1,
        event_type: 'research.updated',
        occurred_at: '2026-08-10T00:00:00Z',
        object_type: 'research',
        object_id: researchId,
        object_version: null,
        object_revision: 1,
        request_id: null,
        job_id: null,
        agent_run_id: null,
        tool_call_id: null,
        payload: {},
      } satisfies Schema<'SseEnvelope'>;
      return route.fulfill({
        contentType: 'text/event-stream',
        body: `data: ${JSON.stringify(event)}\n\n`,
      });
    });

    await page.goto(`/research/${researchId}?tab=${tab}`);
    const selectedTab = page.getByRole('tab', { name: label });
    await expect(selectedTab).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('tabpanel')).toContainText('Loading research workspace');
    initialReleased = true;
    releaseInitial();
    await expect(page.getByRole('tabpanel')).toContainText(emptyCopy);
    await expect(page).toHaveURL(new RegExp(`tab=${tab}$`));

    holdRefetch = true;
    releaseStream();
    await expect(page.getByText('Revalidating this research from server truth…')).toBeVisible();
    await expect(selectedTab).toHaveAttribute('aria-selected', 'true');
    releaseRefetch();
    await expect.poll(() => reads).toBeGreaterThanOrEqual(2);

    errorMode = true;
    await page.reload();
    await expect(page.getByRole('tabpanel')).toContainText(
      'Canonical research projection is temporarily unavailable.',
    );
    await expect(
      page.getByRole('link', { name: 'Audit request REQ-P04-FOUR-STATE' }),
    ).toBeVisible();
    await expect(page.getByRole('tab', { name: label })).toHaveAttribute('aria-selected', 'true');
  });
}
