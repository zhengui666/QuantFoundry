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
  let selectedCredential = '';

  const credentialParts = (raw: string) => {
    const value = raw.trim();
    const token = value.startsWith('qf_session=')
      ? (value.slice('qf_session='.length).split(';', 1)[0]?.trim() ?? '')
      : value;
    return { cookiePair: `qf_session=${token}`, token };
  };

  const reconcile = () => {
    const expected =
      typeof expectedSessionCookie === 'function' ? expectedSessionCookie() : expectedSessionCookie;
    const { cookiePair: expectedPair, token } = credentialParts(expected);
    if (selectedCredential !== token) {
      selectedCredential = token;
      authenticatedRequest = undefined;
      authenticatedTerminated = false;
    }
    if (!token || authenticatedRequest) return;
    for (const [request, response] of successfulResponses) {
      const cookieMatches = response.cookie
        ?.split(';')
        .map((part) => part.trim())
        .some((part) => part === expectedPair);
      if (
        response.status === 200 &&
        (cookieMatches || response.authorization === `Bearer ${token}`)
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
      const { cookiePair: expectedPair, token } = credentialParts(expected);
      if (status === 200) successfulResponses.set(request, { authorization, cookie, status });
      const cookieMatches = cookie
        ?.split(';')
        .map((part) => part.trim())
        .some((part) => part === expectedPair);
      if (
        token.length > 0 &&
        status === 200 &&
        (cookieMatches || authorization === `Bearer ${token}`)
      ) {
        if (selectedCredential !== token) {
          selectedCredential = token;
          authenticatedRequest = undefined;
          authenticatedTerminated = false;
        }
        if (authenticatedRequest === undefined) {
          authenticatedRequest = request;
          authenticatedTerminated = terminatedRequests.has(request);
        }
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
