// The independent probe deliberately uses the same production decoder.  This prevents a
// test-only permissive parser from "proving" a causal SSE path the browser would reject.
export {
  decodeCanonicalSseFrame,
  splitCanonicalSseFrames,
  type DecodedSseFrame,
} from '../api/client';

import { splitCanonicalSseFrames } from '../api/client';
import type { DecodedSseFrame } from '../api/client';

export async function startCanonicalSseProbe(
  url: URL,
  sessionCookie: string,
  trustedOrigin: string,
  options: { signal?: AbortSignal; timeoutMs?: number } = {},
) {
  const trusted = new URL(trustedOrigin);
  const localInsecureOrigin =
    trusted.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(trusted.hostname);
  if (trusted.protocol !== 'https:' && !localInsecureOrigin)
    throw new Error('Authenticated SSE probe requires an HTTPS trusted origin outside localhost.');
  const origin = trusted.origin;
  if (
    url.origin !== origin ||
    url.pathname !== '/api/v1/events/stream' ||
    url.search ||
    url.hash ||
    url.username ||
    url.password
  )
    throw new Error('Authenticated SSE probe URL is outside the trusted stream origin.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 30_000);
  const abortExternal = () => controller.abort(options.signal?.reason);
  let cleanedUp = false;
  const cleanup = () => {
    if (cleanedUp) return;
    cleanedUp = true;
    clearTimeout(timeout);
    options.signal?.removeEventListener('abort', abortExternal);
  };
  if (options.signal) {
    if (options.signal.aborted) abortExternal();
    else options.signal.addEventListener('abort', abortExternal, { once: true });
  }
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: 'text/event-stream', Cookie: sessionCookie },
      redirect: 'error',
      signal: controller.signal,
    });
  } catch (error) {
    cleanup();
    throw error;
  }
  const responseBody = response.body;
  const mediaType = response.headers.get('content-type')?.split(';', 1)[0]?.trim().toLowerCase();
  if (response.status !== 200 || mediaType !== 'text/event-stream' || !responseBody) {
    cleanup();
    controller.abort();
    throw new Error(
      `Authenticated SSE probe expected HTTP 200 text/event-stream, received ${response.status} ${mediaType ?? 'missing content type'}.`,
    );
  }

  const frames: DecodedSseFrame[] = [];
  let failure: unknown;
  const waiters = new Set<{
    predicate: (frame: DecodedSseFrame) => boolean;
    resolve: (frame: DecodedSseFrame) => void;
    reject: (error: unknown) => void;
  }>();
  let closed = false;
  let terminalError: Error | undefined;
  const rejectWaiters = (error: Error) => {
    terminalError = error;
    closed = true;
    for (const waiter of waiters) waiter.reject(error);
    waiters.clear();
  };
  const publish = (frame: DecodedSseFrame) => {
    frames.push(frame);
    for (const waiter of [...waiters]) {
      try {
        if (!waiter.predicate(frame)) continue;
      } catch (error) {
        waiters.delete(waiter);
        waiter.reject(error);
        continue;
      }
      waiters.delete(waiter);
      waiter.resolve(frame);
    }
  };
  const reading = (async () => {
    let buffer = '';
    try {
      const reader = responseBody.pipeThrough(new TextDecoderStream()).getReader();
      while (!controller.signal.aborted) {
        const part = await reader.read();
        if (part.done) break;
        buffer += part.value;
        const split = splitCanonicalSseFrames(buffer);
        buffer = split.remainder;
        split.decoded.forEach(publish);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        failure = error;
        rejectWaiters(error instanceof Error ? error : new Error(String(error)));
      }
    } finally {
      if (!closed)
        rejectWaiters(
          failure instanceof Error
            ? failure
            : new Error('Authenticated SSE probe stream closed before the expected frame.'),
        );
      cleanup();
    }
  })();

  return {
    snapshot: () => ({ frames: [...frames], failure }),
    waitForFrame(predicate: (frame: DecodedSseFrame) => boolean) {
      let current: DecodedSseFrame | undefined;
      try {
        current = frames.find(predicate);
      } catch (error) {
        return Promise.reject(error);
      }
      if (current) return Promise.resolve(current);
      if (terminalError) return Promise.reject(terminalError);
      return new Promise<DecodedSseFrame>((resolve, reject) => {
        waiters.add({ predicate, resolve, reject });
      });
    },
    async stop() {
      controller.abort();
      await reading;
      cleanup();
    },
  };
}
