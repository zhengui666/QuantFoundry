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

const withStorage = <T>(fallback: T, operation: (target: Storage) => T): T => {
  const target = storage();
  if (!target) return fallback;
  try {
    return operation(target);
  } catch {
    return fallback;
  }
};

export const transientStorage = {
  get(key: string): string | null {
    return allowed(key) ? withStorage(null, (target) => target.getItem(key)) : null;
  },
  set(key: string, value: string): void {
    if (allowed(key)) withStorage(undefined, (target) => target.setItem(key, value));
  },
  remove(key: string): void {
    if (allowed(key)) withStorage(undefined, (target) => target.removeItem(key));
  },
  removeByPrefix(prefix: string): void {
    withStorage(undefined, (target) => {
      for (let index = target.length - 1; index >= 0; index -= 1) {
        const key = target.key(index);
        if (key?.startsWith(prefix) && allowed(key)) target.removeItem(key);
      }
    });
  },
};
