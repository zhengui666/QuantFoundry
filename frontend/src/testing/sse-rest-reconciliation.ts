import { queryKeysForEvent, type EventEnvelope, type EventQueryKey } from '../api/client';
import type { DecodedSseFrame } from './fullstack-sse-probe';

type QueryPlanner = (event: EventEnvelope) => readonly EventQueryKey[];

export class SseRestReconciliationWitness {
  readonly baseline: number;
  private matchingEvent: DecodedSseFrame | undefined;
  private matchingRestReads = 0;
  private eventReadBoundary: number;

  constructor(
    private readonly resourceType: string,
    private readonly resourceId: string,
    private readonly exactRestPath: string,
    initialRestReads: number,
  ) {
    this.baseline = initialRestReads;
    this.eventReadBoundary = initialRestReads;
  }

  observeEvent(
    frame: DecodedSseFrame,
    planner: QueryPlanner = queryKeysForEvent,
    restReadsAtEvent = this.baseline,
  ) {
    if (!Number.isInteger(restReadsAtEvent) || restReadsAtEvent < this.baseline)
      throw new Error('SSE reconciliation event boundary must follow the frozen REST baseline.');
    const mapped = planner(frame.event).some(
      (key) => key[1] === this.resourceType && key[2] === this.resourceId,
    );
    if (mapped) {
      this.matchingEvent = frame;
      this.eventReadBoundary = restReadsAtEvent;
      this.matchingRestReads = 0;
    } else {
      this.matchingEvent = undefined;
      this.matchingRestReads = 0;
    }
  }

  observeRest(path: string, requestOrdinal: number) {
    // Initial loader/StrictMode reads are part of the frozen baseline. Only a
    // generated event-to-query match can arm a later exact REST observation. The
    // ordinal comes from the browser request listener, so reads already in flight
    // when the SSE frame arrived cannot be misclassified as causal refetches.
    if (
      this.matchingEvent &&
      path === this.exactRestPath &&
      Number.isInteger(requestOrdinal) &&
      requestOrdinal > this.eventReadBoundary
    )
      this.matchingRestReads += 1;
  }

  snapshot() {
    return {
      baseline: this.baseline,
      event: this.matchingEvent,
      restReadsAfterBaseline: this.matchingRestReads,
    };
  }

  assertReconciled() {
    if (!this.matchingEvent)
      throw new Error('No generated event-to-query mapping armed REST reconciliation.');
    if (this.matchingRestReads < 1)
      throw new Error('No exact REST refetch followed the decoded SSE event.');
  }
}
