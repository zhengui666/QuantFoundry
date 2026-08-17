import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api, workspaceQueryKey, type Schema } from '../api/client';
import { Panel, Problem, State } from '../ui';

const initialSecret = { label: '' };

export function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const catalog = useQuery({
    queryKey: workspaceQueryKey('settings', 'catalog'),
    queryFn: ({ signal }) => api.configurationCatalog(signal),
  });
  const active = useQuery({
    queryKey: workspaceQueryKey('settings', 'active'),
    queryFn: ({ signal }) => api.configurationActive(signal),
  });
  const keys = useQuery({
    queryKey: workspaceQueryKey('settings', 'access-keys'),
    queryFn: ({ signal }) => api.accessKeys(signal),
  });
  const database = useQuery({
    queryKey: workspaceQueryKey('settings', 'database'),
    queryFn: ({ signal }) => api.databaseConnection(signal),
  });
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [draftIdentity, setDraftIdentity] = useState<string>();
  const [configurationMessage, setConfigurationMessage] = useState<string>();
  useEffect(() => {
    if (!active.data) return;
    const identity = `${active.data.etag}:${active.data.body.active_revision}`;
    if (draftIdentity === identity) return;
    const next: Record<string, string> = {};
    for (const value of active.data.body.values)
      if (value.sensitivity !== 'SECRET' && value.value !== null)
        next[value.key] = JSON.stringify(value.value, null, 2);
    setDraftValues(next);
    setDraftIdentity(identity);
  }, [active.data, draftIdentity]);
  const saveConfiguration = useMutation({
    mutationFn: async () => {
      const etag = active.data?.etag;
      const activeBody = active.data?.body;
      if (!etag || !activeBody) throw new Error('Active configuration ETag is unavailable.');
      const values: Schema<'ConfigurationCandidateRequest'>['values'] =
        catalog.data?.body.entries.flatMap<
          Schema<'ConfigurationCandidateRequest'>['values'][number]
        >((entry) => {
          const input = draftValues[entry.key] ?? '';
          const raw = input.trim();
          if (!raw) return [];
          if (entry.sensitivity === 'SECRET') return [{ key: entry.key, secret: input }];
          return [
            {
              key: entry.key,
              value: JSON.parse(raw) as Schema<'ConfigurationValueView'>['value'],
            },
          ];
        }) ?? [];
      const candidate = await api.putConfigurationCandidate(
        { base_revision: activeBody.active_revision, values },
        etag,
      );
      const validation = await api.validateConfigurationCandidate();
      if (validation.body.revision !== candidate.body.revision)
        throw new Error('Configuration candidate changed during validation; retry.');
      if (validation.body.status !== 'VALID') throw new Error(t('settings.validationFailed'));
      return api.activateConfiguration(candidate.body.revision, etag);
    },
    onSuccess: () => {
      setConfigurationMessage(t('settings.saved'));
      void queryClient.invalidateQueries({ queryKey: workspaceQueryKey('settings', 'active') });
    },
    onError: (error) =>
      setConfigurationMessage(error instanceof Error ? error.message : t('error.connection')),
  });
  const [dbForm, setDbForm] = useState({
    host: '',
    port: '5432',
    database: '',
    tls_mode: 'VERIFY_FULL' as 'DISABLED' | 'VERIFY_CA' | 'VERIFY_FULL',
    username: '',
    password: '',
  });
  const [dbDraftIdentity, setDbDraftIdentity] = useState<string>();
  const [dbSavedFingerprint, setDbSavedFingerprint] = useState<string>();
  const [dbCandidateRevision, setDbCandidateRevision] = useState<number>();
  const [dbValidatedRevision, setDbValidatedRevision] = useState<number>();
  const serverCandidateRevision = database.data?.body.candidate?.revision;
  const serverCandidateState = database.data?.body.candidate?.state;
  useEffect(() => {
    setDbCandidateRevision(serverCandidateRevision);
    setDbValidatedRevision(
      serverCandidateState === 'VALIDATED' ? serverCandidateRevision : undefined,
    );
  }, [serverCandidateRevision, serverCandidateState]);
  const persistedValidatedRevision =
    database.data?.body.candidate?.state === 'VALIDATED'
      ? database.data.body.candidate.revision
      : undefined;
  const validatedRevision =
    dbValidatedRevision ??
    (dbCandidateRevision === undefined ? persistedValidatedRevision : undefined);
  const dbFingerprint = (value: typeof dbForm) =>
    JSON.stringify({
      host: value.host.trim(),
      port: value.port,
      database: value.database.trim(),
      tls_mode: value.tls_mode,
      username: value.username.trim(),
      password: value.password,
    });
  const dbFormDirty =
    dbSavedFingerprint !== undefined && dbFingerprint(dbForm) !== dbSavedFingerprint;
  useEffect(() => {
    const current = database.data?.body.active;
    if (!current) return;
    const identity = `${database.data?.etag}:${current.revision}`;
    if (dbDraftIdentity === identity) return;
    const nextForm = {
      host: current.host,
      port: String(current.port),
      database: current.database,
      tls_mode: current.tls_mode,
      username: '',
      password: '',
    };
    setDbForm(nextForm);
    setDbSavedFingerprint(JSON.stringify(nextForm));
    setDbDraftIdentity(identity);
  }, [database.data, dbDraftIdentity]);
  const saveDatabase = useMutation({
    mutationFn: () => {
      const etag = database.data?.etag;
      if (!etag) throw new Error('Database connection ETag is unavailable.');
      const baseRevision = database.data?.body.active_revision;
      if (baseRevision == null) throw new Error('Active database revision is unavailable.');
      return api.putDatabaseConnectionCandidate(
        {
          base_revision: baseRevision,
          connection: {
            host: dbForm.host.trim(),
            port: Number(dbForm.port),
            database: dbForm.database.trim(),
            tls_mode: dbForm.tls_mode,
            ...(dbForm.username.trim() ? { username: dbForm.username.trim() } : {}),
            ...(dbForm.password ? { password: dbForm.password } : {}),
          },
        },
        etag,
      );
    },
    onSuccess: ({ body }) => {
      setDbCandidateRevision(body.revision);
      setDbValidatedRevision(undefined);
      setDbSavedFingerprint(dbFingerprint(dbForm));
      void queryClient.invalidateQueries({ queryKey: workspaceQueryKey('settings', 'database') });
    },
  });
  const validateDatabase = useMutation({
    mutationFn: async () => {
      const revision = dbCandidateRevision ?? database.data?.body.candidate?.revision;
      if (!revision) throw new Error('Database candidate revision is unavailable.');
      const result = await api.validateDatabaseConnectionCandidate(revision);
      if (result.body.status !== 'VALID') {
        throw new Error('Database connection validation failed.');
      }
      return result;
    },
    onSuccess: ({ body }) => {
      setDbValidatedRevision(body.revision);
      void queryClient.invalidateQueries({ queryKey: workspaceQueryKey('settings', 'database') });
    },
  });
  const activateDatabase = useMutation({
    mutationFn: () => {
      const etag = database.data?.etag;
      if (!etag) throw new Error('Database connection ETag is unavailable.');
      if (!validatedRevision) throw new Error('Validated database candidate is unavailable.');
      return api.activateDatabaseConnection(etag, validatedRevision);
    },
    onSuccess: () => {
      setDbCandidateRevision(undefined);
      setDbValidatedRevision(undefined);
      void queryClient.invalidateQueries({ queryKey: workspaceQueryKey('settings', 'database') });
    },
  });
  const [keyForm, setKeyForm] = useState(initialSecret);
  const [issuedSecret, setIssuedSecret] = useState<string>();
  const issue = useMutation({
    mutationFn: () => {
      setIssuedSecret(undefined);
      return api.createAccessKey({ label: keyForm.label.trim() });
    },
    onSuccess: ({ body }) => {
      setIssuedSecret(body.secret);
      setKeyForm(initialSecret);
      void queryClient.invalidateQueries({
        queryKey: workspaceQueryKey('settings', 'access-keys'),
      });
    },
  });
  const keyAction = useMutation({
    mutationFn: async ({
      action,
      key,
    }: {
      action: 'rotate' | 'revoke';
      key: Schema<'GeneralAccessKeyMetadata'>;
    }) => {
      setIssuedSecret(undefined);
      const etag = `W/"key:${key.revision}"`;
      if (action === 'rotate') return api.rotateAccessKey(key.key_id, etag);
      return api.revokeAccessKey(key.key_id, etag);
    },
    onSuccess: (result, variables) => {
      if (
        variables.action === 'rotate' &&
        'body' in result &&
        result.body &&
        'secret' in result.body
      )
        setIssuedSecret(result.body.secret);
      void queryClient.invalidateQueries({
        queryKey: workspaceQueryKey('settings', 'access-keys'),
      });
    },
    onError: () => setIssuedSecret(undefined),
  });
  if (catalog.isLoading || active.isLoading || keys.isLoading || database.isLoading)
    return <State kind="loading" />;
  if (catalog.error) return <Problem error={catalog.error} />;
  if (active.error) return <Problem error={active.error} />;
  if (keys.error) return <Problem error={keys.error} />;
  if (database.error) return <Problem error={database.error} />;
  const activeBody = active.data?.body;
  return (
    <>
      <h1>{t('settings.title')}</h1>
      <p className="lede">{t('settings.lede')}</p>
      <Panel title={t('settings.catalog')}>
        <p>
          {t('settings.catalogVersion')} {catalog.data?.body.catalog_version}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('settings.key')}</th>
                <th>{t('settings.group')}</th>
                <th>{t('settings.apply')}</th>
                <th>{t('settings.sensitivity')}</th>
              </tr>
            </thead>
            <tbody>
              {catalog.data?.body.entries.map((entry) => (
                <tr key={entry.key}>
                  <td>
                    <code>{entry.key}</code>
                  </td>
                  <td>{entry.group}</td>
                  <td>{entry.apply_mode}</td>
                  <td>{entry.sensitivity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title={t('settings.active')}>
        <p>
          {t('settings.revision')} {activeBody?.active_revision} · {activeBody?.snapshot_sha256}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('settings.key')}</th>
                <th>{t('settings.value')}</th>
                <th>{t('settings.state')}</th>
              </tr>
            </thead>
            <tbody>
              {activeBody?.values.map((value) => (
                <tr key={value.key}>
                  <td>
                    <code>{value.key}</code>
                  </td>
                  <td>
                    {value.sensitivity === 'SECRET'
                      ? (value.masked_hint ?? t('settings.configured'))
                      : JSON.stringify(value.value)}
                  </td>
                  <td>
                    {value.configured ? t('settings.configured') : t('settings.notConfigured')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title={t('settings.editor')}>
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            setConfigurationMessage(undefined);
            saveConfiguration.mutate();
          }}
        >
          {catalog.data?.body.entries.map((entry) => {
            const value = draftValues[entry.key] ?? '';
            return (
              <label key={entry.key}>
                <span>
                  <code>{entry.key}</code> · {entry.sensitivity}
                </span>
                {entry.sensitivity === 'SECRET' ? (
                  <input
                    type="password"
                    autoComplete="new-password"
                    placeholder={t('settings.secretJsonPlaceholder')}
                    value={value}
                    onChange={(event) =>
                      setDraftValues((current) => ({ ...current, [entry.key]: event.target.value }))
                    }
                  />
                ) : (
                  <textarea
                    rows={3}
                    value={value}
                    placeholder="{ }"
                    onChange={(event) =>
                      setDraftValues((current) => ({ ...current, [entry.key]: event.target.value }))
                    }
                  />
                )}
              </label>
            );
          })}
          <button disabled={saveConfiguration.isPending || !active.data?.etag}>
            {saveConfiguration.isPending ? t('common.saving') : t('settings.saveConfiguration')}
          </button>
          {configurationMessage && (
            <State kind={saveConfiguration.isError ? 'error' : 'permission'}>
              {configurationMessage}
            </State>
          )}
        </form>
      </Panel>
      <Panel title={t('settings.accessKeys')}>
        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            issue.mutate();
          }}
        >
          <label>
            {t('settings.label')}
            <input
              required
              maxLength={80}
              value={keyForm.label}
              onChange={(event) => setKeyForm({ label: event.target.value })}
            />
          </label>
          <button disabled={issue.isPending || !keyForm.label.trim()}>
            {t('settings.createKey')}
          </button>
        </form>
        {issue.error && <Problem error={issue.error} />}
        {issuedSecret && (
          <State kind="permission">
            {t('settings.oneTimeSecret')} <code>{issuedSecret}</code>
          </State>
        )}
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('settings.label')}</th>
                <th>{t('settings.hint')}</th>
                <th>{t('settings.status')}</th>
                <th>{t('settings.lastUsed')}</th>
                <th>{t('settings.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {keys.data?.body.items.map((key) => (
                <tr key={key.key_id}>
                  <td>{key.label}</td>
                  <td>{key.masked_hint}</td>
                  <td>{key.status}</td>
                  <td>{key.last_used_at ?? t('settings.never')}</td>
                  <td>
                    {key.status === 'ACTIVE' && (
                      <div className="inline-form">
                        <button
                          type="button"
                          className="secondary"
                          disabled={keyAction.isPending}
                          onClick={() => keyAction.mutate({ action: 'rotate', key })}
                        >
                          {t('settings.rotate')}
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          disabled={keyAction.isPending}
                          onClick={() => {
                            if (window.confirm(t('settings.revokeConfirm', { label: key.label })))
                              keyAction.mutate({ action: 'revoke', key });
                          }}
                        >
                          {t('settings.revoke')}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {keyAction.error && <Problem error={keyAction.error} />}
      </Panel>
      <Panel title={t('settings.database')}>
        <p>
          {database.data?.body.state} · {database.data?.body.domain_operations}
        </p>
        <form
          className="grid"
          onSubmit={(event) => {
            event.preventDefault();
            saveDatabase.mutate();
          }}
        >
          {(['host', 'port', 'database', 'username', 'password'] as const).map((field) => (
            <label key={field}>
              {t(`settings.${field === 'database' ? 'databaseName' : field}`)}
              <input
                required={
                  field !== 'password' && (field !== 'username' || !database.data?.body.active)
                }
                type={field === 'password' ? 'password' : field === 'port' ? 'number' : 'text'}
                value={dbForm[field]}
                onChange={(event) =>
                  setDbForm((current) => ({ ...current, [field]: event.target.value }))
                }
              />
            </label>
          ))}
          <button disabled={saveDatabase.isPending || !database.data?.etag}>
            {t('settings.saveCandidate')}
          </button>
        </form>
        {saveDatabase.error && <Problem error={saveDatabase.error} />}
        {(database.data?.body.candidate?.state === 'CANDIDATE' ||
          (dbCandidateRevision !== undefined && dbValidatedRevision === undefined)) && (
          <button
            disabled={validateDatabase.isPending || dbFormDirty}
            onClick={() => validateDatabase.mutate()}
          >
            {t('settings.validateDatabase')}
          </button>
        )}
        {validatedRevision !== undefined && !dbFormDirty && (
          <button disabled={activateDatabase.isPending} onClick={() => activateDatabase.mutate()}>
            {t('settings.activateDatabase')}
          </button>
        )}
        {validateDatabase.error && <Problem error={validateDatabase.error} />}
        {activateDatabase.error && <Problem error={activateDatabase.error} />}
      </Panel>
    </>
  );
}
