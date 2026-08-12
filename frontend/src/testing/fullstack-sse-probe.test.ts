import { describe, expect, it } from 'vitest';
import { PublicIdExamples } from '../api/generated/runtime-schemas';
import { decodeCanonicalSseFrame, splitCanonicalSseFrames } from './fullstack-sse-probe';

const event = {
  schema_version: 1,
  event_id: PublicIdExamples.domain_event.ulid,
  sequence: 12,
  event_type: 'research.updated',
  occurred_at: '2026-08-11T00:00:00Z',
  object_type: 'research',
  object_id: PublicIdExamples.research.ulid,
  object_version: null,
  object_revision: 2,
  request_id: null,
  job_id: null,
  agent_run_id: null,
  tool_call_id: null,
  payload: {},
} as const;

describe('real full-stack SSE frame decoder', () => {
  it('uses the generated closed envelope and binds frame cursor to event sequence', () => {
    expect(decodeCanonicalSseFrame(`id: 12\ndata: ${JSON.stringify(event)}`)).toEqual({
      cursor: 12,
      event,
    });
    expect(() => decodeCanonicalSseFrame(`id: 13\ndata: ${JSON.stringify(event)}`)).toThrow(
      'does not match',
    );
  });

  it('handles split network chunks while ignoring heartbeat-only frames', () => {
    const value = `: heartbeat\n\nid: 12\ndata: ${JSON.stringify(event)}\n\nid: 13`;
    const result = splitCanonicalSseFrames(value);
    expect(result.decoded).toEqual([{ cursor: 12, event }]);
    expect(result.remainder).toBe('id: 13');
  });

  it('fails closed on extra or structurally drifted actual payload data', () => {
    expect(() =>
      decodeCanonicalSseFrame(
        `id: 12\ndata: ${JSON.stringify({ ...event, unexpected_member: true })}`,
      ),
    ).toThrow('generated closed schema');
  });
});
