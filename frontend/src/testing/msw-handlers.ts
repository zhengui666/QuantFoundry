import { delay, http, HttpResponse } from 'msw';
import type { Schema } from '../api/client';
import { DataCapabilityListSchema } from '../api/generated/runtime-schemas';

export const storybookProblem = {
  type: 'about:blank',
  title: 'Storybook server state',
  status: 503,
  code: 'SERVICE_DEGRADED',
  detail: 'Actual page rendering of the canonical Problem state.',
  instance: null,
  request_id: 'REQ-STORYBOOK-PAGE',
  retryable: true,
  field_errors: [],
  context: {},
} satisfies Schema<'ApiProblem'>;

export const storybookProblemHandlers = [
  http.get('*/api/v1/research/:researchId', () =>
    HttpResponse.json(storybookProblem, { status: storybookProblem.status }),
  ),
  http.get('*/api/v1/strategies/:strategyId/versions/:version', () =>
    HttpResponse.json(storybookProblem, { status: storybookProblem.status }),
  ),
];

export const storybookDataCapabilities = DataCapabilityListSchema.parse([
  {
    capability_id: 'CAP-35MYBZ1TNZM144QVG46FBY3HWF',
    provider_id: 'polygon',
    capability_key: 'US_EQUITY_DAILY_BARS',
    state: 'SUPPORTED',
    asset_classes: ['EQUITY'],
    frequencies: ['DAILY'],
    coverage: { start: '2010-01-01', end: '2026-08-10' },
    point_in_time: { supported: true, available_from: '2010-01-01', semantics: 'AS_REPORTED' },
    fields: ['open', 'high', 'low', 'close', 'volume'],
    limitations: [],
    checked_at: '2026-08-10T02:00:00Z',
  },
]) satisfies Schema<'DataCapabilityList'>;

export const decodeStorybookDataCapabilities = (value: unknown): Schema<'DataCapabilityList'> =>
  DataCapabilityListSchema.parse(value);

const scenarioProblem = (
  status: 403 | 409,
  code: 'PERMISSION_DENIED' | 'RESOURCE_CONFLICT',
): Schema<'ApiProblem'> => ({
  ...storybookProblem,
  status,
  code,
  retryable: false,
  detail: status === 403 ? 'Server capability denies this view.' : 'Server state is stale.',
});

const dataCapabilities = (body: Schema<'DataCapabilityList'>, wait = 0) =>
  http.get('*/api/v1/data/capabilities', async () => {
    if (wait > 0) await delay(wait);
    return HttpResponse.json(decodeStorybookDataCapabilities(body));
  });

export const sharedMswScenarios = {
  happy: [dataCapabilities(storybookDataCapabilities)],
  loading: [
    http.get('*/api/v1/data/capabilities', async () => {
      await delay('infinite');
      return HttpResponse.json([]);
    }),
  ],
  empty: [dataCapabilities([])],
  delayed: [dataCapabilities(storybookDataCapabilities, 750)],
  stale: [
    dataCapabilities(
      storybookDataCapabilities.map((capability) => ({
        ...capability,
        state: 'UNKNOWN',
        limitations: [{ code: 'STALE_DATA', detail: 'Last server check is stale.' }],
      })),
    ),
  ],
  permission: [
    http.get('*/api/v1/data/capabilities', () =>
      HttpResponse.json(scenarioProblem(403, 'PERMISSION_DENIED'), { status: 403 }),
    ),
  ],
  conflict: [
    http.get('*/api/v1/data/capabilities', () =>
      HttpResponse.json(scenarioProblem(409, 'RESOURCE_CONFLICT'), { status: 409 }),
    ),
  ],
} as const;
