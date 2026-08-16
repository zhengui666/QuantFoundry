export type StreamTrackerSnapshot = {
  authenticatedAccepted: boolean;
  authenticatedTerminated: boolean;
  ignoredRejectedTerminations: number;
};

export function createAuthenticatedStreamTracker<RequestIdentity extends object>(
  expectedSessionCookie: string | (() => string),
) {
  let authenticatedRequest: RequestIdentity | undefined;
  let authenticatedTerminated = false;
  let ignoredRejectedTerminations = 0;
  const rejectedRequests = new WeakSet<RequestIdentity>();

  return {
    observeResponse({
      authorization,
      path,
      request,
      status,
      cookie,
    }: {
      authorization: string | undefined;
      cookie?: string;
      path: string;
      request: RequestIdentity;
      status: number;
    }) {
      if (path !== '/api/v1/events/stream') return;
      const expected =
        typeof expectedSessionCookie === 'function'
          ? expectedSessionCookie()
          : expectedSessionCookie;
      if (
        status === 200 &&
        (cookie?.includes(expected) || authorization === `Bearer ${expected}`)
      ) {
        authenticatedRequest ??= request;
        return;
      }
      if (status === 401 || status === 403) rejectedRequests.add(request);
    },
    observeTermination(request: RequestIdentity) {
      if (request === authenticatedRequest) authenticatedTerminated = true;
      else if (rejectedRequests.has(request)) ignoredRejectedTerminations += 1;
    },
    snapshot(): StreamTrackerSnapshot {
      return {
        authenticatedAccepted: authenticatedRequest !== undefined,
        authenticatedTerminated,
        ignoredRejectedTerminations,
      };
    },
  };
}
