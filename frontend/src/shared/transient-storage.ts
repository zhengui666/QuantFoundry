/* eslint-disable no-restricted-syntax -- this is the sole allowlisted transient storage adapter. */

const allowed = (key: string): boolean =>
  key === 'qf.auth.return_to' || key === 'qf.setup.started' || key.startsWith('qf.sse.cursor:');

const storage = (): Storage | undefined => {
  if (typeof window === 'undefined') return undefined;
  try {
    return window.sessionStorage;
  } catch {
    return undefined;
  }
};

export const transientStorage = {
  get(key: string): string | null {
    return allowed(key) ? (storage()?.getItem(key) ?? null) : null;
  },
  set(key: string, value: string): void {
    if (allowed(key)) storage()?.setItem(key, value);
  },
  remove(key: string): void {
    if (allowed(key)) storage()?.removeItem(key);
  },
  removeByPrefix(prefix: string): void {
    const target = storage();
    if (!target) return;
    for (let index = target.length - 1; index >= 0; index -= 1) {
      const key = target.key(index);
      if (key?.startsWith(prefix) && allowed(key)) target.removeItem(key);
    }
  },
};
