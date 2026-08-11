// @vitest-environment node
import { describe, expect, it } from 'vitest';

describe('Node-side API module safety', () => {
  it('imports without DOM storage and keeps cursor persistence browser-only', async () => {
    expect(typeof window).toBe('undefined');
    const client = await import('./client');
    expect(client.auth.scope()).toMatch(/^workspace:/);
    expect(() => client.auth.set('node-import-token')).not.toThrow();
    client.auth.clear();
  });
});
