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
  const terminatedRequests = new WeakSet<RequestIdentity>();
  const successfulResponses = new Map<
    RequestIdentity,
    { authorization: string | undefined; cookie: string | undefined; status: number }
  >();

  const reconcile = () => {
    const expected =
      typeof expectedSessionCookie === 'function' ? expectedSessionCookie() : expectedSessionCookie;
    if (!expected || authenticatedRequest) return;
    const expectedPair = expected.includes('=') ? expected.trim() : `qf_session=${expected}`;
    for (const [request, response] of successfulResponses) {
      const cookieMatches = response.cookie
        ?.split(';')
        .map((part) => part.trim())
        .some((part) => part === expectedPair);
      if (
        response.status === 200 &&
        (cookieMatches || response.authorization === `Bearer ${expected}`)
      ) {
        authenticatedRequest = request;
        authenticatedTerminated = terminatedRequests.has(request);
        return;
      }
    }
  };

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
      if (status === 200) successfulResponses.set(request, { authorization, cookie, status });
      const expectedPair = expected.includes('=') ? expected.trim() : `qf_session=${expected}`;
      const cookieMatches = cookie
        ?.split(';')
        .map((part) => part.trim())
        .some((part) => part === expectedPair);
      if (
        expected.length > 0 &&
        status === 200 &&
        (cookieMatches || authorization === `Bearer ${expected}`)
      ) {
        authenticatedRequest ??= request;
        return;
      }
      if (status === 401 || status === 403) rejectedRequests.add(request);
    },
    observeTermination(request: RequestIdentity) {
      terminatedRequests.add(request);
      reconcile();
      if (request === authenticatedRequest) authenticatedTerminated = true;
      else if (rejectedRequests.has(request)) ignoredRejectedTerminations += 1;
    },
    snapshot(): StreamTrackerSnapshot {
      reconcile();
      return {
        authenticatedAccepted: authenticatedRequest !== undefined,
        authenticatedTerminated,
        ignoredRejectedTerminations,
      };
    },
  };
}
