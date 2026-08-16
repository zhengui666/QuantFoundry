import { expect, test } from 'playwright/test';
import type { Schema } from '../src/api/client';

const overview = {
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
} satisfies Schema<'OverviewReadModel'>;

test('single-owner session exposes no bearer or workspace controls', async ({ page }) => {
  await page.route('**/api/v1/events/stream', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: '' }),
  );
  await page.route('**/api/v1/overview', (route) => route.fulfill({ json: overview }));
  await page.goto('/overview');
  await expect(page.getByRole('button', { name: /退出登录|Log out/ })).toBeVisible();
  await expect(page.getByLabel(/Bearer token|通用密钥/)).toHaveCount(0);
  await expect(page.getByText(/workspace|工作区/i)).toHaveCount(0);
});
