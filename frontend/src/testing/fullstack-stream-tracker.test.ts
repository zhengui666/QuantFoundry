import { describe, expect, it } from 'vitest';
import { createAuthenticatedStreamTracker } from './fullstack-stream-tracker';

describe('full-stack authenticated SSE lifecycle tracker', () => {
  it('ignores a finished pre-auth 401 before accepting a still-open authenticated 200', () => {
    const tracker = createAuthenticatedStreamTracker<object>('current-token');
    const preAuth = {};
    const authenticated = {};
    const unrelated = {};

    tracker.observeResponse({
      request: preAuth,
      path: '/api/v1/events/stream',
      status: 401,
      authorization: undefined,
    });
    tracker.observeTermination(preAuth);
    tracker.observeResponse({
      request: authenticated,
      path: '/api/v1/events/stream',
      status: 200,
      authorization: 'Bearer current-token',
    });
    tracker.observeTermination(unrelated);

    expect(tracker.snapshot()).toEqual({
      authenticatedAccepted: true,
      authenticatedTerminated: false,
      ignoredRejectedTerminations: 1,
    });
  });

  it('marks only the accepted authenticated 200 request terminating as a disconnect', () => {
    const tracker = createAuthenticatedStreamTracker<object>('current-token');
    const authenticated = {};
    tracker.observeResponse({
      request: authenticated,
      path: '/api/v1/events/stream',
      status: 200,
      authorization: 'Bearer current-token',
    });
    tracker.observeTermination(authenticated);
    expect(tracker.snapshot()).toEqual({
      authenticatedAccepted: true,
      authenticatedTerminated: true,
      ignoredRejectedTerminations: 0,
    });
  });
});
