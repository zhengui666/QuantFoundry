import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { setupServer } from 'msw/node';
import { ApiProblemSchema } from '../api/generated/runtime-schemas';
import {
  decodeStorybookDataCapabilities,
  sharedMswScenarios,
  storybookDataCapabilities,
} from './msw-handlers';

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const getCapabilities = () => fetch('http://localhost/api/v1/data/capabilities');

describe('shared Storybook/MSW canonical scenarios', () => {
  it('decodes happy, empty, delayed, and stale bodies with the generated runtime schema', async () => {
    for (const [handlers, expectedLength] of [
      [sharedMswScenarios.happy, 1],
      [sharedMswScenarios.empty, 0],
      [sharedMswScenarios.delayed, 1],
      [sharedMswScenarios.stale, 1],
    ] as const) {
      server.resetHandlers(...handlers);
      const response = await getCapabilities();
      expect(response.status).toBe(200);
      expect(decodeStorybookDataCapabilities(await response.json())).toHaveLength(expectedLength);
    }
  });

  it('uses canonical closed Problem payloads for permission and conflict', async () => {
    for (const [handlers, expectedStatus] of [
      [sharedMswScenarios.permission, 403],
      [sharedMswScenarios.conflict, 409],
    ] as const) {
      server.resetHandlers(...handlers);
      const response = await getCapabilities();
      expect(response.status).toBe(expectedStatus);
      expect(ApiProblemSchema.parse(await response.json()).status).toBe(expectedStatus);
    }
  });

  it('fails closed when a Storybook fixture drifts from the canonical response', () => {
    expect(() =>
      decodeStorybookDataCapabilities([
        { ...storybookDataCapabilities[0], checked_at: 'not-a-server-utc-timestamp', extra: true },
      ]),
    ).toThrow();
  });
});
