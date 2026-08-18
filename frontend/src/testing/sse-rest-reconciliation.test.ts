import { describe, expect, it } from 'vitest';
import type { Schema } from '../api/client';
import { PublicIdExamples } from '../api/generated/runtime-schemas';
import type { DecodedSseFrame } from './fullstack-sse-probe';
import { SseRestReconciliationWitness } from './sse-rest-reconciliation';

const event = {
  schema_version: 1,
  event_id: PublicIdExamples.domain_event.ulid,
  sequence: '4',
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
} satisfies Schema<'SseEnvelope'>;
const frame = { cursor: event.sequence, event } satisfies DecodedSseFrame;
const path = `/api/v1/research/${event.object_id}`;

describe('SSE→REST causal reconciliation witness mutation-test seam', () => {
  it('passes only after the generated mapping event and a new exact REST read', () => {
    const witness = new SseRestReconciliationWitness('research', event.object_id, path, 2);
    witness.observeEvent(frame);
    witness.observeRest(path, 3);
    expect(() => witness.assertReconciled()).not.toThrow();
    expect(witness.snapshot().restReadsAfterBaseline).toBe(1);
  });

  it('negative control fails if queryKeysForEvent is replaced with no invalidation', () => {
    const witness = new SseRestReconciliationWitness('research', event.object_id, path, 2);
    witness.observeEvent(frame, () => []);
    witness.observeRest(path, 3);
    expect(() => witness.assertReconciled()).toThrow('No generated event-to-query mapping');
    expect(witness.snapshot().restReadsAfterBaseline).toBe(0);
  });

  it('negative control keeps the frozen baseline when no event is delivered', () => {
    const witness = new SseRestReconciliationWitness('research', event.object_id, path, 2);
    witness.observeRest(path, 3);
    expect(() => witness.assertReconciled()).toThrow('No generated event-to-query mapping');
    expect(witness.snapshot()).toMatchObject({ baseline: 2, restReadsAfterBaseline: 0 });
  });

  it('arms a related resource when the generated query mapping owns the target', () => {
    const witness = new SseRestReconciliationWitness('research', event.object_id, path, 2);
    const relatedFrame = {
      ...frame,
      event: { ...event, object_id: 'EXP-1M49GS2TJYQ2JPYV54YDGY7R59' },
    };
    witness.observeEvent(relatedFrame, () => [['workspace', 'research', event.object_id]]);
    witness.observeRest(path, 3);
    expect(() => witness.assertReconciled()).not.toThrow();
  });

  it('does not count a REST read that was already present when the event arrived', () => {
    const witness = new SseRestReconciliationWitness('research', event.object_id, path, 2);
    witness.observeEvent(frame, undefined, 3);
    witness.observeRest(path, 3);
    expect(() => witness.assertReconciled()).toThrow('No exact REST refetch');
  });
});
