// The independent probe deliberately uses the same production decoder.  This prevents a
// test-only permissive parser from "proving" a causal SSE path the browser would reject.
export {
  decodeCanonicalSseFrame,
  splitCanonicalSseFrames,
  type DecodedSseFrame,
} from '../api/client';

import { splitCanonicalSseFrames } from '../api/client';
import type { DecodedSseFrame } from '../api/client';

export async function startCanonicalSseProbe(url: URL, sessionCookie: string) {
  const controller = new AbortController();
  const response = await fetch(url, {
    headers: { Accept: 'text/event-stream', Cookie: sessionCookie },
    signal: controller.signal,
  });
  const responseBody = response.body;
  if (response.status !== 200 || !responseBody) {
    controller.abort();
    throw new Error(`Authenticated SSE probe expected HTTP 200, received ${response.status}.`);
  }

  const frames: DecodedSseFrame[] = [];
  let failure: unknown;
  const waiters = new Set<{
    predicate: (frame: DecodedSseFrame) => boolean;
    resolve: (frame: DecodedSseFrame) => void;
    reject: (error: unknown) => void;
  }>();
  const publish = (frame: DecodedSseFrame) => {
    frames.push(frame);
    for (const waiter of waiters) {
      if (!waiter.predicate(frame)) continue;
      waiters.delete(waiter);
      waiter.resolve(frame);
    }
  };
  const reading = (async () => {
    const reader = responseBody.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = '';
    try {
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
        for (const waiter of waiters) waiter.reject(error);
        waiters.clear();
      }
    }
  })();

  return {
    snapshot: () => ({ frames: [...frames], failure }),
    waitForFrame(predicate: (frame: DecodedSseFrame) => boolean) {
      const current = frames.find(predicate);
      if (current) return Promise.resolve(current);
      if (failure) return Promise.reject(failure);
      return new Promise<DecodedSseFrame>((resolve, reject) => {
        waiters.add({ predicate, resolve, reject });
      });
    },
    async stop() {
      controller.abort();
      await reading;
    },
  };
}
