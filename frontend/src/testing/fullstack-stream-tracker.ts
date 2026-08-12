export type StreamTrackerSnapshot = {
  authenticatedAccepted: boolean;
  authenticatedTerminated: boolean;
  ignoredRejectedTerminations: number;
};

export function createAuthenticatedStreamTracker<RequestIdentity extends object>(
  expectedBearer: string,
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
    }: {
      authorization: string | undefined;
      path: string;
      request: RequestIdentity;
      status: number;
    }) {
      if (path !== '/api/v1/events/stream') return;
      if (status === 200 && authorization === `Bearer ${expectedBearer}`) {
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
