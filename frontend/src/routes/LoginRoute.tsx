import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { ApiError, api } from '../api/client';
import { transientStorage } from '../shared/transient-storage';
import { Panel, Problem, State } from '../ui';

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [key, setKey] = useState('');
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  return (
    <section className="auth-page">
      <h1>{t('auth.loginTitle')}</h1>
      <p>{t('auth.loginLede')}</p>
      <Panel title={t('auth.generalAccessKey')}>
        <form
          onSubmit={(event) => {
            void (async () => {
              event.preventDefault();
              setPending(true);
              setError(undefined);
              try {
                await api.login(key.trim());
                setKey('');
                const returnTo = transientStorage.get('qf.auth.return_to');
                transientStorage.remove('qf.auth.return_to');
                let safeReturnTo: string | undefined;
                if (returnTo) {
                  try {
                    const target = new URL(returnTo, window.location.origin);
                    if (target.origin === window.location.origin && target.pathname !== '/login')
                      safeReturnTo = `${target.pathname}${target.search}${target.hash}`;
                  } catch {
                    safeReturnTo = undefined;
                  }
                }
                if (safeReturnTo) window.location.replace(safeReturnTo);
                else void navigate({ to: '/overview', replace: true });
              } catch (value) {
                setError(value);
              } finally {
                setPending(false);
              }
            })();
          }}
        >
          <label>
            {t('auth.generalAccessKey')}
            <input
              required
              type="password"
              autoComplete="off"
              value={key}
              onChange={(event) => setKey(event.target.value)}
            />
          </label>
          <button disabled={pending || !key.trim()}>
            {pending ? t('common.saving') : t('auth.authenticate')}
          </button>
        </form>
        {error instanceof ApiError ? (
          <Problem error={error} />
        ) : error ? (
          <State kind="error">{t('error.connection')}</State>
        ) : null}
      </Panel>
    </section>
  );
}
