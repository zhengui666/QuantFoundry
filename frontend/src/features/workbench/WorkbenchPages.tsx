import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Link,
  Outlet,
  useNavigate,
  useParams,
  useLocation,
  useRouterState,
  useSearch,
} from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import {
  ApiError,
  api,
  auth,
  ContractError,
  idempotency,
  isPublicId,
  isMutableEventQueryKey,
  queryKeysForEvent,
  streamEvents,
  workspaceQueryKey,
  type ExperimentReproduceBody,
  type Schema,
} from '../../api/client';
import {
  Badge,
  Capability,
  CapabilityFieldset,
  Inspector,
  localizedErrorCopy,
  mergeActionCapabilities,
  Panel,
  Problem,
  Provenance,
  State,
} from '../../ui';
import i18n, { applyServerSettingsLocale, configurationLocale } from '../../i18n';
import { transientStorage } from '../../shared/transient-storage';
import { ServerTime } from '../../format';

function assertNever(value: never): never {
  throw new Error(`Unhandled canonical variant: ${String(value)}`);
}

const CanonicalChart = lazy(() => import('../../CanonicalChart'));

const detailRouteTypes = {
  research: 'research',
  experiments: 'experiment',
  strategies: 'strategy',
  validation: 'validation',
  approvals: 'approval',
  memos: 'memo',
} as const;

const invalidRouteMessages = {
  research: 'route.invalidResearch',
  experiment: 'route.invalidExperiment',
  strategy: 'route.invalidStrategy',
  validation: 'route.invalidValidation',
  approval: 'route.invalidApproval',
  memo: 'route.invalidMemo',
} as const;

function invalidDetailRoute(pathname: string): keyof typeof invalidRouteMessages | undefined {
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length !== 2) return undefined;
  const type = detailRouteTypes[parts[0] as keyof typeof detailRouteTypes];
  if (!type) return undefined;
  try {
    return isPublicId(type, decodeURIComponent(parts[1] ?? '')) ? undefined : type;
  } catch {
    return type;
  }
}

function setupRecoveryStep(status: Schema<'SetupStatus'>): number {
  switch (status.fallback_step) {
    case 'AI_PROVIDER':
      return 2;
    case 'RESEARCH_DEFAULTS':
      return 4;
    case 'RESEARCH_CONSTITUTION':
      return 5;
    case null:
      if (!status.owner_session_ready) return 1;
      return status.data_provider_configured ? 5 : 3;
    default:
      return assertNever(status.fallback_step);
  }
}

export function Shell() {
  const { t } = useTranslation();
  const translationRef = useRef(t);
  translationRef.current = t;
  const navigate = useNavigate();
  const location = useLocation();
  const client = useQueryClient();
  const [streamState, setStreamState] = useState('connecting');
  const [streamProblem, setStreamProblem] = useState<ApiError>();
  const [keyDraft, setKeyDraft] = useState('');
  const [reauthRequired, setReauthRequired] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [authScopeKey, setAuthScopeKey] = useState(auth.scope());
  const [sessionReady, setSessionReady] = useState(() => Boolean(auth.get()));
  const [localeReady, setLocaleReady] = useState(() => !auth.get());
  const isSetup = useRouterState({ select: (state) => state.location.pathname === '/setup' });
  const isLogin = useRouterState({ select: (state) => state.location.pathname === '/login' });
  const invalidRoute = invalidDetailRoute(location.pathname);
  useEffect(() => {
    if (auth.get()) return;
    void api
      .session()
      .catch(() => undefined)
      .finally(() => setSessionReady(true));
  }, []);
  useEffect(() => {
    if (!auth.get()) {
      setLocaleReady(true);
      return;
    }
    setLocaleReady(false);
    void api
      .configurationActive()
      .then(({ body }) => {
        const locale = configurationLocale(
          body.values.find((entry) => entry.key === 'appearance.locale')?.value,
        );
        if (locale)
          return applyServerSettingsLocale(locale).then(() => {
            if (i18n.language !== locale.language) return i18n.changeLanguage(locale.language);
          });
      })
      .finally(() => setLocaleReady(true))
      .catch(() => undefined);
  }, [authScopeKey]);
  useEffect(() => {
    if (sessionReady && !auth.get() && !isLogin) {
      const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (returnTo !== '/login') transientStorage.set('qf.auth.return_to', returnTo);
      void navigate({ to: '/login', replace: true });
    }
  }, [isLogin, navigate, sessionReady]);
  useEffect(() => {
    if (!auth.get()) return;
    return streamEvents(
      (event) => {
        setStreamState(translationRef.current('stream.updated', { object: event.object_type }));
        for (const queryKey of queryKeysForEvent(event))
          void client.invalidateQueries({ queryKey, exact: true, type: 'active' });
      },
      () => {
        setStreamState(translationRef.current('stream.resynchronizing'));
        void (async () => {
          const predicate = (query: { queryKey: readonly unknown[] }) =>
            isMutableEventQueryKey(query.queryKey);
          await client.invalidateQueries({ type: 'active', refetchType: 'none', predicate });
          await client.refetchQueries({ type: 'active', predicate });
        })();
      },
      (state) => {
        setStreamState(
          state === 'client-update-required'
            ? translationRef.current('stream.clientUpdateRequired')
            : state === 'resynchronizing'
              ? translationRef.current('stream.resynchronizing')
              : translationRef.current(`stream.${state}`),
        );
        if (state === 'connected') setStreamProblem(undefined);
      },
      setStreamProblem,
    );
  }, [authScopeKey, client]);
  useEffect(
    () =>
      auth.subscribe(() => {
        const authenticated = auth.get().length > 0;
        void client.cancelQueries();
        client.clear();
        setAuthScopeKey(auth.scope());
        setReauthRequired(!authenticated);
      }),
    [client],
  );
  useEffect(() => setMobileNavOpen(false), [location.pathname]);
  if (invalidRoute) return <State kind="error">{t(invalidRouteMessages[invalidRoute])}</State>;
  if ((!sessionReady || !localeReady) && !isLogin) return <State kind="loading" />;
  const navigation = [
    ['/overview', 'nav.overview'],
    ['/research', 'nav.research'],
    ['/strategies', 'nav.strategies'],
    ['/validation', 'nav.validation'],
    ['/approvals', 'nav.approvals'],
    ['/memos', 'nav.memo'],
    ['/data', 'nav.data'],
    ['/agents', 'nav.agents'],
    ['/activity', 'nav.activity'],
    ['/settings', 'nav.settings'],
  ] as const;
  return (
    <>
      <div className={`app${isSetup ? ' setup-shell' : ''}`}>
        {!isSetup && (
          <>
            {mobileNavOpen && (
              <button
                className="mobile-nav-backdrop"
                aria-label={t('nav.primary')}
                onClick={() => setMobileNavOpen(false)}
              />
            )}
            <nav
              id="primary-navigation"
              className={`sidebar${mobileNavOpen ? ' mobile-sheet-open' : ''}`}
              aria-label={t('nav.primary')}
            >
              <div className="brand">
                <span className="nav-label">{t('brand')}</span>
                <span className="nav-short" aria-hidden="true">
                  QF
                </span>
              </div>
              {navigation.map(([to, key]) => (
                <Link
                  key={to}
                  to={to}
                  aria-label={t(key)}
                  onClick={() => setMobileNavOpen(false)}
                  activeProps={{ className: 'active', 'aria-current': 'page' }}
                >
                  <span className="nav-label">{t(key)}</span>
                  <span className="nav-short" aria-hidden="true">
                    {key.split('.').at(-1)?.slice(0, 2).toUpperCase()}
                  </span>
                </Link>
              ))}
            </nav>
          </>
        )}
        <main key={authScopeKey}>
          <header className="topbar">
            {!isSetup && !isLogin && (
              <button
                className="mobile-nav-trigger secondary"
                aria-expanded={mobileNavOpen}
                aria-controls="primary-navigation"
                onClick={() => setMobileNavOpen((open) => !open)}
              >
                {t('nav.primary')}
              </button>
            )}
            <span aria-live="polite">
              <Badge>
                {t('realtime')} ·{' '}
                {streamState === 'connecting' ? t('stream.connecting') : streamState}
              </Badge>
            </span>
            {isLogin ? null : auth.get() ? (
              <button className="secondary" onClick={() => void api.logout()}>
                {t('auth.logout')}
              </button>
            ) : (
              <form
                className="auth-form"
                onSubmit={async (event) => {
                  event.preventDefault();
                  try {
                    await api.login(keyDraft.trim());
                    setKeyDraft('');
                    setReauthRequired(false);
                  } catch (error) {
                    if (error instanceof ApiError) setStreamProblem(error);
                    setReauthRequired(true);
                  }
                }}
              >
                <label>
                  {t('auth.generalAccessKey')}
                  <input
                    type="password"
                    value={keyDraft}
                    aria-label={t('auth.generalAccessKey')}
                    onChange={(event) => setKeyDraft(event.target.value)}
                    placeholder={t('auth.memoryOnly')}
                  />
                </label>
                <button disabled={!keyDraft.trim()}>{t('auth.authenticate')}</button>
              </form>
            )}
          </header>
          {reauthRequired && <State kind="error">{t('auth.expired')}</State>}
          {streamProblem && <Problem error={streamProblem} />}
          <Outlet />
        </main>
      </div>
    </>
  );
}

export function SetupPage() {
  const { i18n, t } = useTranslation();
  const navigate = useNavigate();
  const status = useQuery({
    queryKey: workspaceQueryKey('setup-status'),
    queryFn: ({ signal }) => api.setupStatus(signal),
  });
  const capabilities = useQuery({
    queryKey: workspaceQueryKey('setup-capabilities'),
    queryFn: ({ signal }) => api.setupCapabilities(signal),
  });
  const [step, setStep] = useState(1);
  const [providerId, setProviderId] = useState('');
  const [dataProviderId, setDataProviderId] = useState('');
  const [modelName, setModelName] = useState('');
  const [aiCredential, setAiCredential] = useState('');
  const [dataCredential, setDataCredential] = useState('');
  const [dataSkipped, setDataSkipped] = useState(false);
  const setupRestored = useRef(false);
  const resumeSetup = useRef(transientStorage.get('qf.setup.started') === 'true');
  const completeIntent = useRef<{ payload: string; key: string } | undefined>(undefined);
  const completeSubmitting = useRef(false);
  const [aiConnection, setAiConnection] =
    useState<Schema<'SetupProviderConnectionValidationResult'>>();
  const [dataConnection, setDataConnection] =
    useState<Schema<'SetupProviderConnectionValidationResult'>>();
  const [form, setForm] = useState({
    language: 'zh-CN' as 'en' | 'zh-CN',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    base_currency: 'USD',
    number_format_locale: 'zh-CN',
    default_benchmark: 'SPY',
    default_research_start: '',
    initial_paper_capital: '100000',
  });
  const validateAi = useMutation({
    mutationFn: () =>
      api.validateSetupConnection({
        provider_id: providerId,
        kind: 'AI',
        model_name: modelName || null,
        credential: aiCredential,
      }),
    onSuccess: async ({ body }) => {
      setAiCredential('');
      if (body.state === 'FAILED') {
        setAiConnection(body);
        return;
      }
      const refreshed = await status.refetch();
      setAiConnection(
        refreshed.data?.body.ai_connection_id === body.connection_id ? body : undefined,
      );
    },
  });
  const validateData = useMutation({
    mutationFn: () =>
      api.validateSetupConnection({
        provider_id: dataProviderId,
        kind: 'DATA',
        model_name: null,
        credential: dataCredential,
      }),
    onSuccess: ({ body }) => {
      setDataConnection(body);
      setDataCredential('');
      void status.refetch();
    },
  });
  const complete = useMutation({
    mutationFn: async () => {
      const refreshed = await status.refetch();
      const server = refreshed.data?.body;
      if (
        !server?.ai_connection_id ||
        !server.research_policy_id ||
        !server.risk_policy_id ||
        !server.cost_model_id ||
        server.fallback_step !== null
      )
        throw new ContractError('Fresh server setup refs are required before Finish.');
      const active = await api.configurationActive();
      if (!active.etag) throw new ContractError('Fresh configuration ETag is required.');
      const body = { configuration_revision: active.body.active_revision };
      const payload = JSON.stringify(body);
      if (!completeIntent.current || completeIntent.current.payload !== payload)
        completeIntent.current = { payload, key: idempotency() };
      return api.completeSetup(body, active.etag, completeIntent.current.key);
    },
    onSuccess: async ({ body }) => {
      const locale = configurationLocale(
        body.values.find((entry) => entry.key === 'appearance.locale')?.value,
      );
      if (locale) await applyServerSettingsLocale(locale);
      const refreshed = await status.refetch();
      if (refreshed.data?.body.completed) {
        completeIntent.current = undefined;
        transientStorage.remove('qf.setup.started');
        void navigate({ to: '/overview', replace: true });
      } else if (refreshed.data) setStep(setupRecoveryStep(refreshed.data.body));
    },
    onError: async () => {
      const refreshed = await status.refetch();
      if (refreshed.data?.body.completed) {
        completeIntent.current = undefined;
        transientStorage.remove('qf.setup.started');
        void navigate({ to: '/overview', replace: true });
      } else if (refreshed.data) setStep(setupRecoveryStep(refreshed.data.body));
    },
    onSettled: () => {
      completeSubmitting.current = false;
    },
  });
  const providers = capabilities.data?.body.providers.filter((item) => item.kind === 'AI') ?? [];
  const dataProviders =
    capabilities.data?.body.providers.filter((item) => item.kind === 'DATA') ?? [];
  const selectedProvider = providers.find((item) => item.provider_id === providerId);
  const selectedDataProvider = dataProviders.find((item) => item.provider_id === dataProviderId);
  const readiness = status.data?.body;
  const policyReady = Boolean(
    readiness?.research_policy_active &&
    readiness.research_policy_id &&
    readiness.risk_policy_active &&
    readiness.risk_policy_id &&
    readiness.cost_model_active &&
    readiness.cost_model_id,
  );
  const dataStepComplete = Boolean(readiness?.data_provider_configured || dataSkipped);
  const recoveryStep = readiness ? setupRecoveryStep(readiness) : 1;
  const canContinue =
    step === 1
      ? Boolean(readiness?.owner_session_ready)
      : step === 2
        ? Boolean(readiness?.ai_provider_configured && readiness.ai_connection_id)
        : step === 3
          ? dataStepComplete
          : step === 4
            ? Boolean(readiness?.cost_model_active && readiness.cost_model_id)
            : false;
  const serverEligible = Boolean(
    readiness?.owner_session_ready &&
    readiness.ai_provider_configured &&
    readiness.ai_connection_id &&
    policyReady &&
    readiness.fallback_step === null &&
    !readiness.completed,
  );
  const canFinish = Boolean(serverEligible && dataStepComplete);
  useEffect(() => {
    if (!readiness || setupRestored.current) return;
    setupRestored.current = true;
    transientStorage.set('qf.setup.started', 'true');
    if (readiness.completed) {
      transientStorage.remove('qf.setup.started');
      void navigate({ to: '/overview', replace: true });
    } else if (resumeSetup.current) setStep(recoveryStep);
  }, [navigate, readiness, recoveryStep]);
  useEffect(() => {
    if (readiness && step > recoveryStep && readiness.fallback_step !== null) setStep(recoveryStep);
  }, [readiness, recoveryStep, step]);
  if (status.isLoading || capabilities.isLoading)
    return <State kind="loading">{t('setup.loading')}</State>;
  if (status.error) return <Problem error={status.error} />;
  if (capabilities.error) return <Problem error={capabilities.error} />;
  return (
    <>
      <h1>{t('page.setup')}</h1>
      <p>{t('setup.progress', { step })}</p>
      <Panel title={t('setup.readiness')}>
        <Badge>{status.data?.body.completed ? 'COMPLETED' : 'REQUIRED'}</Badge>
        <p>
          {t('setup.providerChecked')}{' '}
          <ServerTime value={capabilities.data?.body.server_checked_at} />
        </p>
      </Panel>
      <form
        className="panel setup-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (completeSubmitting.current) return;
          completeSubmitting.current = true;
          complete.mutate();
        }}
      >
        {dataSkipped && <State kind="permission">{t('setup.dataSkippedReason')}</State>}
        {step === 3 && !readiness?.data_provider_configured && !dataSkipped && (
          <State kind="permission">{t('setup.dataMissingReason')}</State>
        )}
        {step === 1 && (
          <fieldset>
            <legend>{t('setup.basic')}</legend>
            <label>
              {t('setup.language')}
              <select
                value={form.language}
                onChange={(event) => {
                  const language = event.target.value as 'zh-CN' | 'en';
                  setForm((current) => ({
                    ...current,
                    language,
                    number_format_locale: language === 'zh-CN' ? 'zh-CN' : 'en-US',
                  }));
                  void i18n.changeLanguage(language);
                }}
              >
                <option value="zh-CN">简体中文</option>
                <option value="en">English</option>
              </select>
            </label>
            {(['timezone', 'base_currency', 'number_format_locale'] as const).map((key) => (
              <label key={key}>
                {t(`setup.field.${key}`)}
                <input
                  required
                  value={form[key]}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, [key]: event.target.value }))
                  }
                />
              </label>
            ))}
            <p>{t('setup.market')}</p>
          </fieldset>
        )}
        {step === 2 && (
          <fieldset>
            <legend>{t('setup.ai')}</legend>
            <label>
              {t('setup.aiProvider')}
              <select
                value={providerId}
                required
                onChange={(event) => {
                  setProviderId(event.target.value);
                  setModelName('');
                  setAiConnection(undefined);
                }}
              >
                <option value="">{t('setup.selectProvider')}</option>
                {providers.map((provider) => (
                  <option key={provider.provider_id} value={provider.provider_id}>
                    {provider.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('setup.model')}
              <select value={modelName} onChange={(event) => setModelName(event.target.value)}>
                <option value="">{t('setup.providerDefault')}</option>
                {selectedProvider?.models.map((model) => (
                  <option key={model.model_name}>{model.model_name}</option>
                ))}
              </select>
            </label>
            <label>
              {t('setup.credential')}
              <input
                type="password"
                value={aiCredential}
                onChange={(event) => setAiCredential(event.target.value)}
                autoComplete="off"
              />
            </label>
            <button
              type="button"
              disabled={!providerId || !aiCredential || validateAi.isPending}
              onClick={() => validateAi.mutate()}
            >
              {validateAi.isPending ? t('setup.testing') : t('setup.testAi')}
            </button>
            {validateAi.error && <Problem error={validateAi.error} />}
            {readiness?.ai_connection_id && (
              <State kind="empty">
                {t('setup.verifiedAi', { id: readiness.ai_connection_id })}
              </State>
            )}
            {aiConnection?.state === 'FAILED' && (
              <State kind="error">
                {localizedErrorCopy(aiConnection.error_code, t, i18n.language)}{' '}
                {aiConnection.detail}
              </State>
            )}
            {!readiness?.ai_connection_id && aiConnection?.state !== 'FAILED' && (
              <State kind="permission">{t('setup.aiNotVerified')}</State>
            )}
          </fieldset>
        )}
        {step === 3 && (
          <fieldset>
            <legend>{t('setup.data')}</legend>
            <label>
              {t('setup.defaultDataProvider')}
              <select
                value={dataProviderId}
                onChange={(event) => {
                  setDataProviderId(event.target.value);
                  setDataConnection(undefined);
                  setDataSkipped(false);
                }}
              >
                <option value="">{t('setup.selectProvider')}</option>
                {dataProviders.map((provider) => (
                  <option key={provider.provider_id} value={provider.provider_id}>
                    {provider.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('setup.dataCredential')}
              <input
                type="password"
                value={dataCredential}
                onChange={(event) => setDataCredential(event.target.value)}
                autoComplete="off"
              />
            </label>
            <button
              type="button"
              disabled={!dataProviderId || !dataCredential || validateData.isPending}
              onClick={() => validateData.mutate()}
            >
              {validateData.isPending ? t('setup.testing') : t('setup.testData')}
            </button>
            {validateData.error && <Problem error={validateData.error} />}
            {dataConnection?.state === 'SUCCESS' && (
              <State kind="empty">
                {t('setup.verifiedData', { id: dataConnection.connection_id })}
              </State>
            )}
            {dataConnection?.state === 'FAILED' && (
              <State kind="error">
                {localizedErrorCopy(dataConnection.error_code, t, i18n.language)}{' '}
                {dataConnection.detail}
              </State>
            )}
            {selectedDataProvider?.data_capabilities.map((capability) => (
              <article className="row-card" key={capability.capability_id}>
                <Badge>{capability.state}</Badge>
                <strong>{capability.capability_key}</strong>
                <span>{capability.frequencies.join(', ')}</span>
              </article>
            ))}
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setDataSkipped(true);
                setDataProviderId('');
                setDataCredential('');
                setDataConnection(undefined);
                setStep(4);
              }}
            >
              {t('setup.skipData')}
            </button>
          </fieldset>
        )}
        {step === 4 && (
          <fieldset>
            <legend>{t('setup.defaults')}</legend>
            <dl className="definition">
              <dt>{t('setup.researchPolicy')}</dt>
              <dd>{readiness?.research_policy_id ?? t('setup.requiresReconfirmation')}</dd>
              <dt>{t('setup.riskPolicy')}</dt>
              <dd>{readiness?.risk_policy_id ?? t('setup.requiresReconfirmation')}</dd>
              <dt>{t('setup.costModel')}</dt>
              <dd>{readiness?.cost_model_id ?? t('setup.requiresReconfirmation')}</dd>
            </dl>
            {readiness?.fallback_step === 'RESEARCH_DEFAULTS' && (
              <State kind="permission">{t('setup.costReconfirmation')}</State>
            )}
            {readiness?.fallback_step === 'RESEARCH_CONSTITUTION' && (
              <State kind="permission">{t('setup.policyReconfirmation')}</State>
            )}
            {(
              ['default_benchmark', 'default_research_start', 'initial_paper_capital'] as const
            ).map((key) => (
              <label key={key}>
                {t(`setup.field.${key}`)}
                <input
                  required={key !== 'default_research_start'}
                  type={key === 'default_research_start' ? 'date' : 'text'}
                  value={form[key]}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, [key]: event.target.value }))
                  }
                />
              </label>
            ))}
          </fieldset>
        )}
        {step === 5 && (
          <fieldset>
            <legend>{t('setup.constitution')}</legend>
            <p>
              {t('setup.serverBindings')} {readiness?.research_policy_id ?? t('status.UNAVAILABLE')}{' '}
              · {readiness?.risk_policy_id ?? t('status.UNAVAILABLE')} ·{' '}
              {readiness?.cost_model_id ?? t('status.UNAVAILABLE')}
            </p>
            <ul className="constitution" aria-label={t('setup.requiredConstitution')}>
              {[
                'noLookAhead',
                'survivorship',
                'transactionCosts',
                'validateCandidate',
                'holdoutAfterFreeze',
                'paperApproval',
              ].map((ruleKey) => (
                <li key={ruleKey}>
                  ✓ {t(`setup.rule.${ruleKey}`)} · {t('setup.required')}
                </li>
              ))}
            </ul>
            <button disabled={!canFinish || complete.isPending}>
              {complete.isPending ? t('common.saving') : t('setup.finish')}
            </button>
          </fieldset>
        )}
        <div className="setup-navigation">
          <button
            className="secondary"
            type="button"
            disabled={step === 1}
            onClick={() => setStep((current) => current - 1)}
          >
            {t('common.back')}
          </button>
          {step < 5 && (
            <button
              type="button"
              disabled={!canContinue}
              onClick={() => setStep((current) => current + 1)}
            >
              {t('common.continue')}
            </button>
          )}
          {!canContinue && step < 5 && (
            <span className="disabled-reason" role="status">
              {t('setup.ineligible')}
            </span>
          )}
        </div>
        {complete.error && <Problem error={complete.error} />}
        {step === 5 && !serverEligible && (
          <span className="disabled-reason" role="status">
            {t('setup.freshBindingsRequired')}
          </span>
        )}
        {complete.isSuccess && <State kind="empty">{t('setup.complete')}</State>}
      </form>
    </>
  );
}

export function NewResearchPage() {
  const { t } = useTranslation();
  const list = useQuery({
    queryKey: workspaceQueryKey('research'),
    queryFn: ({ signal }) => api.research(signal),
  });
  const [created, setCreated] = useState<string>();
  const mutation = useMutation({
    mutationFn: (body: Schema<'ResearchCreateRequest'>) => api.createResearch(body),
    onSuccess: ({ body }) => setCreated(body.research_id),
  });
  return (
    <>
      <h1>{t('page.research')}</h1>
      <Panel title={t('research.cases')}>
        {list.isLoading && <State kind="loading" />}
        {list.error && <Problem error={list.error} />}
        {list.data?.body.items.map((item) => (
          <article className="row-card" key={item.research_id}>
            <Badge>{item.status}</Badge>
            <Link to="/research/$researchId" params={{ researchId: item.research_id }}>
              {item.title}
            </Link>
            <span>{item.evidence_status}</span>
          </article>
        ))}
      </Panel>
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          mutation.mutate({
            title: String(data.get('title')),
            original_user_prompt: String(data.get('prompt')),
            research_policy_id: null,
          });
        }}
      >
        <label>
          {t('research.title')}
          <input name="title" required />
        </label>
        <label>
          {t('research.brief')}
          <textarea name="prompt" required />
        </label>
        <button disabled={mutation.isPending}>{t('action.create_research')}</button>
      </form>
      {mutation.error && <Problem error={mutation.error} />}
      {created && (
        <State kind="empty">
          {t('research.created')}{' '}
          <Link to="/research/$researchId" params={{ researchId: created }}>
            {created}
          </Link>
        </State>
      )}
    </>
  );
}

export function ResearchWorkspacePage() {
  const { t } = useTranslation();
  const { researchId } = useParams({ strict: false }) as { researchId: string };
  const validResearchId = isPublicId('research', researchId);
  const client = useQueryClient();
  const navigate = useNavigate();
  const search = useSearch({ strict: false }) as {
    tab?: 'overview' | 'plan' | 'timeline' | 'experiments' | 'evidence' | 'artifacts' | 'audit';
  };
  const activeTab = search.tab ?? 'overview';
  const tabs = [
    ['overview', 'research.tab.overview'],
    ['plan', 'research.tab.plan'],
    ['timeline', 'research.tab.timeline'],
    ['experiments', 'research.tab.experiments'],
    ['evidence', 'research.tab.evidence'],
    ['artifacts', 'research.tab.artifacts'],
    ['audit', 'research.tab.audit'],
  ] as const;
  const tabNavigation = (
    <div className="workspace-tabs" role="tablist" aria-label={t('research.workspace')}>
      {tabs.map(([tab, labelKey]) => (
        <button
          key={tab}
          role="tab"
          aria-selected={activeTab === tab}
          aria-controls="research-workspace-panel"
          className={activeTab === tab ? undefined : 'secondary'}
          onClick={() =>
            void navigate({
              to: '/research/$researchId',
              params: { researchId },
              search: { tab },
            })
          }
        >
          {t(labelKey)}
        </button>
      ))}
    </div>
  );
  const stateShell = (content: ReactNode) => (
    <>
      <h1>{t('research.workspace')}</h1>
      {tabNavigation}
      <div id="research-workspace-panel" role="tabpanel" className="research-workspace-panel">
        {content}
      </div>
    </>
  );
  const query = useQuery({
    queryKey: validResearchId
      ? workspaceQueryKey('research', researchId)
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.researchDetail(researchId, signal),
    enabled: validResearchId,
  });
  const start = useMutation({
    mutationFn: () => {
      if (!query.data?.etag) throw new Error('Server ETag required');
      return api.startResearch(researchId, query.data.etag, {
        research_revision_no: query.data.body.current_revision_no,
        capability_evaluation_confirmed: true,
      });
    },
    onSettled: () =>
      void client.invalidateQueries({ queryKey: workspaceQueryKey('research', researchId) }),
  });
  if (!validResearchId) return <State kind="error">{t('route.invalidResearch')}</State>;
  if (query.isLoading)
    return stateShell(<State kind="loading">{t('research.loadingWorkspace')}</State>);
  if (query.error) return stateShell(<Problem error={query.error} />);
  const data = query.data?.body;
  if (!data) return stateShell(<State kind="empty" />);
  const emptyPage = (label: string) => (
    <State kind="empty">{t('research.emptyServerTruth', { label })}</State>
  );
  const tabContent = (() => {
    switch (activeTab) {
      case 'overview': {
        const { brief, current_conclusion, current_agent_work, latest_evidence, progress } =
          data.overview;
        return (
          <div className="grid">
            <Panel title={t('research.brief')}>
              <h3>{brief.question}</h3>
              <p>{brief.hypothesis ?? t('research.noHypothesis')}</p>
              <p>{brief.economic_rationale ?? t('research.noEconomicRationale')}</p>
              <dl className="definition">
                <dt>{t('research.supportDefinition')}</dt>
                <dd>{brief.supporting_evidence_definition ?? t('research.notDefined')}</dd>
                <dt>{t('research.disconfirmingDefinition')}</dt>
                <dd>{brief.disconfirming_evidence_definition ?? t('research.notDefined')}</dd>
                <dt>{t('research.universeBenchmark')}</dt>
                <dd>
                  {brief.universe.symbols.join(', ') ||
                    brief.universe.universe_id ||
                    t('research.emptyUniverse')}{' '}
                  / {brief.benchmark}
                </dd>
                <dt>{t('research.periodFrequency')}</dt>
                <dd>
                  {brief.period.start} – {brief.period.end} / {brief.frequency}
                </dd>
                <dt>{t('research.contentHash')}</dt>
                <dd>
                  <code>{brief.content_sha256}</code>
                </dd>
              </dl>
            </Panel>
            <Panel title={t('research.currentConclusion')}>
              {current_conclusion ? (
                <>
                  <Badge>{current_conclusion.evidence_status}</Badge>
                  <p>{current_conclusion.summary}</p>
                  <p>
                    {current_conclusion.uncertainties.join(', ') || t('research.noUncertainties')}
                  </p>
                  <p>{current_conclusion.recommendation ?? t('research.noRecommendation')}</p>
                  <Provenance value={current_conclusion.provenance} source="AI" />
                </>
              ) : (
                emptyPage(t('research.emptyLabel.currentConclusion'))
              )}
            </Panel>
            <Panel title={t('research.progress')}>
              {progress.length === 0
                ? emptyPage(t('research.emptyLabel.progress'))
                : progress.map((node) => (
                    <article className="row-card" key={node.node_key}>
                      <Badge>{node.status}</Badge>
                      <strong>{node.title}</strong>
                      <span>{node.owner_agent_role ?? t('research.unassigned')}</span>
                    </article>
                  ))}
            </Panel>
            <Panel title={t('research.latestEvidence')}>
              {latest_evidence.length === 0
                ? emptyPage(t('research.emptyLabel.evidence'))
                : latest_evidence.map((item) => (
                    <article key={item.evidence.id}>
                      <Badge>{item.stance}</Badge> <strong>{item.claim}</strong>
                      <p>
                        {item.strength} · {item.limitations ?? t('research.noLimitation')}
                      </p>
                      <Provenance value={item.provenance} />
                    </article>
                  ))}
            </Panel>
            <Panel title={t('research.currentAgentWork')}>
              {current_agent_work ? (
                <>
                  <Badge>{current_agent_work.status}</Badge>
                  <p>{current_agent_work.agent_role}</p>
                  <p>{current_agent_work.objective ?? t('research.noObjective')}</p>
                  <p>{current_agent_work.current_action ?? t('research.noActiveAction')}</p>
                  <p>{current_agent_work.next_action ?? t('research.noNextAction')}</p>
                  <Provenance value={current_agent_work.provenance} source="AI" />
                </>
              ) : (
                emptyPage(t('research.emptyLabel.currentAgentWork'))
              )}
            </Panel>
          </div>
        );
      }
      case 'plan':
        return data.plan ? (
          <Panel title={t('research.serverPlanTitle', { version: data.plan.plan_version })}>
            <Badge>{data.plan.status}</Badge>
            <p>{data.plan.rationale_summary ?? t('research.noRationale')}</p>
            {data.plan.nodes.length === 0
              ? emptyPage(t('research.emptyLabel.planNodes'))
              : data.plan.nodes.map((node) => (
                  <article className="row-card" key={node.node_key}>
                    <Badge>{node.status}</Badge>
                    <strong>{node.title}</strong>
                    <span>
                      {t('research.experimentDependency', {
                        count: node.experiment_count,
                        dependencies: node.depends_on.join(', ') || t('research.root'),
                      })}
                    </span>
                  </article>
                ))}
            <Provenance value={data.plan.provenance} source="AI" />
          </Panel>
        ) : (
          emptyPage(t('research.emptyLabel.plan'))
        );
      case 'timeline':
        return data.timeline.items.length === 0 ? (
          emptyPage(t('research.emptyLabel.timeline'))
        ) : (
          <Panel title={t('research.serverTimeline')}>
            {data.timeline.items.map((item) => (
              <article key={item.event_id} className="panel nested-panel">
                <Badge>{item.agent_role ?? 'SYSTEM'}</Badge>
                <p>{item.objective ?? t('research.noObjective')}</p>
                <p>{item.result_summary ?? t('research.noResultSummary')}</p>
                <p>{item.decision_summary ?? t('research.noDecisionSummary')}</p>
                <p>{item.next_action ?? t('research.noNextAction')}</p>
                <p>
                  {t('research.tool', {
                    value: item.tool ? `${item.tool.name}@${item.tool.version}` : t('common.none'),
                  })}{' '}
                  <ServerTime value={item.occurred_at} />
                </p>
                <Provenance value={item.provenance} />
              </article>
            ))}
          </Panel>
        );
      case 'experiments':
        return (
          <Panel title={t('research.immutableExperiments')}>
            {data.experiments.items.length === 0
              ? emptyPage(t('research.emptyLabel.experiments'))
              : data.experiments.items.map((item) => (
                  <article className="row-card" key={item.experiment.id}>
                    <Badge>{item.status}</Badge>
                    <Link
                      to="/experiments/$experimentId"
                      params={{ experimentId: item.experiment.id }}
                    >
                      {item.experiment.id}
                    </Link>
                    <span>{item.objective}</span>
                    <Provenance value={item.provenance} />
                  </article>
                ))}
            <Link to="/experiments">{t('research.openExperimentWorkflow')}</Link>
          </Panel>
        );
      case 'evidence':
        return data.evidence.items.length === 0 ? (
          emptyPage(t('research.emptyLabel.evidence'))
        ) : (
          <Panel title={t('research.evidenceLedger')}>
            {data.evidence.items.map((item) => (
              <article className="panel nested-panel" key={item.evidence.id}>
                <Badge>{item.stance}</Badge> <strong>{item.claim}</strong>
                <p>
                  {item.strength} · {item.limitations ?? t('research.noLimitation')}
                </p>
                <p>
                  {t('research.resultLocator', {
                    hash: item.result_locator.result_sha256,
                    metric: item.result_locator.metric_key ?? t('research.noMetric'),
                  })}
                </p>
                <Provenance value={item.provenance} />
              </article>
            ))}
          </Panel>
        );
      case 'artifacts':
        return data.artifacts.items.length === 0 ? (
          emptyPage(t('research.emptyLabel.artifacts'))
        ) : (
          <Panel title={t('research.authorizedArtifacts')}>
            {data.artifacts.items.map((item) => (
              <article className="row-card" key={item.artifact.id}>
                <Badge>{item.kind}</Badge>
                <strong>{item.artifact.id}</strong>
                <span>
                  {item.media_type} · {t('common.bytes', { count: item.size_bytes })} ·{' '}
                  {item.sha256}
                </span>
                <Provenance value={item.provenance} />
              </article>
            ))}
          </Panel>
        );
      case 'audit':
        return data.audit.items.length === 0 ? (
          emptyPage(t('research.emptyLabel.audit'))
        ) : (
          <Panel title={t('research.auditEvents')}>
            {data.audit.items.map((item) => (
              <article className="row-card" key={item.event_id}>
                <Badge>{item.actor.type}</Badge>
                <strong>{item.action}</strong>
                <Link to="/activity" search={{ eventId: item.event_id }}>
                  {item.event_id}
                </Link>
                <Link to="/activity" search={{ requestId: item.request_id }}>
                  {t('research.request', { id: item.request_id })}
                </Link>
                <Provenance value={item.provenance} />
              </article>
            ))}
          </Panel>
        );
      default:
        return assertNever(activeTab);
    }
  })();
  return (
    <>
      <h1>{data.title}</h1>
      <div className="summary">
        <Badge>{data.status}</Badge>
        <span>{data.research_id}</span>
        <span>{t('research.evidenceStatus', { status: data.evidence_status })}</span>
      </div>
      <details>
        <summary>{t('research.serverIdentity')}</summary>
        <dl className="definition">
          <dt>{t('research.originalPrompt')}</dt>
          <dd>{data.original_user_prompt}</dd>
          <dt>{t('research.normalizedQuestion')}</dt>
          <dd>{data.normalized_question ?? t('research.notNormalized')}</dd>
          <dt>{t('research.researchRevision')}</dt>
          <dd>{data.current_revision_no}</dd>
          <dt>{t('research.activePlan')}</dt>
          <dd>{data.active_plan_version ?? t('research.noActivePlan')}</dd>
          <dt>{t('setup.researchPolicy')}</dt>
          <dd>{data.research_policy_id}</dd>
          <dt>{t('research.directorVersion')}</dt>
          <dd>{data.director_agent_version ?? t('research.notAssigned')}</dd>
          <dt>{t('research.recordRevision')}</dt>
          <dd>{data.revision}</dd>
          <dt>{t('research.createdUpdated')}</dt>
          <dd>
            <ServerTime value={data.created_at} /> / <ServerTime value={data.updated_at} />
          </dd>
          <dt>{t('research.completed')}</dt>
          <dd>
            {data.completed_at ? (
              <ServerTime value={data.completed_at} />
            ) : (
              t('research.notCompleted')
            )}
          </dd>
        </dl>
      </details>
      {query.isFetching && <State kind="loading">{t('research.revalidating')}</State>}
      {tabNavigation}
      <div id="research-workspace-panel" role="tabpanel" className="research-workspace-panel">
        {tabContent}
      </div>
      <Panel title={t('research.currentAgentWork')}>
        <p>{t('research.agentRun', { id: data.current_agent_run_id ?? t('common.none') })}</p>
        <p>{t('research.job', { id: data.current_job_id ?? t('common.none') })}</p>
        {data.action_capabilities.map((capability) => (
          <Capability
            key={capability.action}
            item={capability}
            busy={start.isPending}
            onClick={
              capability.action === 'start_research' || capability.action === 'start'
                ? () => start.mutate()
                : undefined
            }
          />
        ))}
        {start.error && <Problem error={start.error} />}
        {start.data && (
          <State kind="empty">
            {t('research.startAccepted', {
              jobId: start.data.body.job_id,
              status: start.data.body.status,
            })}
          </State>
        )}
      </Panel>
    </>
  );
}

export function ExperimentLanding() {
  const { t } = useTranslation();
  const [accepted, setAccepted] = useState<Schema<'JobAccepted'>>();
  const mutation = useMutation({
    mutationFn: (body: Schema<'ExperimentCreateRequest'>) => api.createExperiment(body),
    onSuccess: ({ body }) => setAccepted(body),
  });
  return (
    <>
      <h1>{t('page.experiment')}</h1>
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const optionalText = (key: string) => String(data.get(key) ?? '').trim() || null;
          const optionalNumber = (key: string) => {
            const value = optionalText(key);
            return value === null ? null : Number(value);
          };
          mutation.mutate({
            research_id: String(data.get('research_id')),
            research_revision_no: Number(data.get('research_revision_no')),
            objective: String(data.get('objective')),
            hypothesis: String(data.get('hypothesis')),
            experiment_type: String(
              data.get('experiment_type'),
            ) as Schema<'ExperimentCreateRequest'>['experiment_type'],
            data_snapshot_id: String(data.get('data_snapshot_id')),
            factor_id: optionalText('factor_id'),
            factor_version: optionalNumber('factor_version'),
            strategy_id: optionalText('strategy_id'),
            strategy_version: optionalNumber('strategy_version'),
            cost_model_id: String(data.get('cost_model_id')),
            parameters: [
              {
                key: String(data.get('parameter_key')),
                value: String(data.get('parameter_value')),
              },
            ],
            engine_key: String(data.get('engine_key')),
            engine_version: String(data.get('engine_version')),
          });
        }}
      >
        <div className="grid">
          <label>
            {t('field.researchId')}
            <input name="research_id" required />
          </label>
          <label>
            {t('research.researchRevision')}
            <input name="research_revision_no" type="number" min="1" required />
          </label>
          <label>
            {t('experiment.objective')}
            <input name="objective" required />
          </label>
          <label>
            {t('experiment.hypothesis')}
            <input name="hypothesis" required />
          </label>
          <label>
            {t('field.experimentType')}
            <select name="experiment_type" required>
              {[
                'FACTOR_ANALYSIS',
                'FAST_BACKTEST',
                'PARAMETER_SENSITIVITY',
                'DATA_VALIDATION',
                'STRICT_VALIDATION',
              ].map((type) => (
                <option key={type}>{type}</option>
              ))}
            </select>
          </label>
          <label>
            {t('field.datasetSnapshotId')}
            <input name="data_snapshot_id" required />
          </label>
          <label>
            {t('field.factorIdOptional')}
            <input name="factor_id" />
          </label>
          <label>
            {t('field.factorVersionOptional')}
            <input name="factor_version" type="number" min="1" />
          </label>
          <label>
            {t('field.strategyIdOptional')}
            <input name="strategy_id" />
          </label>
          <label>
            {t('field.strategyVersionOptional')}
            <input name="strategy_version" type="number" min="1" />
          </label>
          <label>
            {t('field.costModelId')}
            <input name="cost_model_id" required />
          </label>
          <label>
            {t('field.parameterKey')}
            <input name="parameter_key" required />
          </label>
          <label>
            {t('field.parameterValue')}
            <input name="parameter_value" required />
          </label>
          <label>
            {t('field.engineKey')}
            <input name="engine_key" required />
          </label>
          <label>
            {t('field.engineVersion')}
            <input name="engine_version" required />
          </label>
        </div>
        <button disabled={mutation.isPending}>
          {mutation.isPending ? t('common.creating') : t('experiment.createImmutable')}
        </button>
      </form>
      {mutation.error && <Problem error={mutation.error} />}
      {accepted && (
        <State kind="empty">
          {t('experiment.executionAccepted', { jobId: accepted.job_id })}
          {accepted.resource_ref?.type.toLowerCase().includes('experiment') && (
            <>
              {' '}
              <Link
                to="/experiments/$experimentId"
                params={{ experimentId: accepted.resource_ref.id }}
              >
                {accepted.resource_ref.id}
              </Link>
            </>
          )}
        </State>
      )}
    </>
  );
}

export function ExperimentPage() {
  const { i18n, t } = useTranslation();
  const { experimentId } = useParams({ strict: false }) as { experimentId: string };
  const validExperimentId = isPublicId('experiment', experimentId);
  const client = useQueryClient();
  const navigate = useNavigate();
  const search = useSearch({ from: '/experiments/$experimentId' });
  const activeTab = search.tab ?? 'summary';
  const [dialogOpen, setDialogOpen] = useState(false);
  const [mode, setMode] = useState<'EXACT' | 'CONTROLLED_OVERRIDE'>('EXACT');
  const [engineVersion, setEngineVersion] = useState('');
  const [adapterVersion, setAdapterVersion] = useState('');
  const [codeVersion, setCodeVersion] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [accepted, setAccepted] = useState<Schema<'ExperimentReproduceAccepted'>>();
  const reproduceInFlight = useRef(false);
  const intent = useRef<{ payload: string; key: string } | undefined>(undefined);
  const query = useQuery({
    queryKey: validExperimentId
      ? workspaceQueryKey('experiment', experimentId)
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.experiment(experimentId, signal),
    enabled: validExperimentId,
  });
  const reproduce = useMutation({
    mutationFn: (body: ExperimentReproduceBody) => {
      const payload = JSON.stringify(body);
      if (!intent.current || intent.current.payload !== payload)
        intent.current = { payload, key: idempotency() };
      return api.reproduceExperiment(experimentId, body, intent.current.key);
    },
    onSuccess: ({ body }) => {
      setAccepted(body);
      setDialogOpen(false);
      intent.current = undefined;
    },
    onSettled: () => {
      reproduceInFlight.current = false;
      void client.invalidateQueries({ queryKey: workspaceQueryKey('experiment', experimentId) });
    },
  });
  const job = useQuery({
    queryKey: workspaceQueryKey('job', accepted?.job_id),
    queryFn: ({ signal }) => api.job(accepted?.job_id ?? '', signal),
    enabled: accepted !== undefined,
    refetchInterval: (current) => {
      const state = current.state.data?.body.status;
      return state && ['COMPLETED', 'FAILED', 'CANCELLED'].includes(state) ? false : 1_000;
    },
  });
  useEffect(() => {
    if (!accepted || job.data?.body.status !== 'COMPLETED') return;
    void client.invalidateQueries({ queryKey: workspaceQueryKey('experiment', experimentId) });
    void client.prefetchQuery({
      queryKey: workspaceQueryKey('experiment', accepted.resource_ref.id),
      queryFn: ({ signal }) => api.experiment(accepted.resource_ref.id, signal),
    });
  }, [accepted, client, experimentId, job.data?.body.status]);
  if (!validExperimentId) return <State kind="error">{t('route.invalidExperiment')}</State>;
  if (query.isLoading) return <State kind="loading" />;
  if (query.error) return <Problem error={query.error} />;
  const data = query.data?.body;
  if (!data) return <State kind="empty" />;
  const reproduceCapability = data.action_capabilities.find(
    (capability) => capability.action === 'reproduce',
  );
  const executionOverrides: Schema<'ExperimentReproduceExecutionOverrides'> = {
    ...(engineVersion.trim() ? { engine_version: engineVersion.trim() } : {}),
    ...(adapterVersion.trim() ? { adapter_version: adapterVersion.trim() } : {}),
    ...(codeVersion.trim() ? { code_version: codeVersion.trim() } : {}),
  };
  const controlledReady =
    Object.keys(executionOverrides).length > 0 && overrideReason.trim().length > 0;
  const submitReproduce = () => {
    if (reproduceInFlight.current) return;
    const body: ExperimentReproduceBody =
      mode === 'EXACT'
        ? { mode: 'EXACT' }
        : {
            mode: 'CONTROLLED_OVERRIDE',
            execution_overrides: executionOverrides,
            reason: overrideReason.trim(),
          };
    reproduceInFlight.current = true;
    reproduce.mutate(body);
  };
  const searchResult = (() => {
    switch (data.search_result.state) {
      case 'NOT_APPLICABLE':
        return <State kind="empty">{t('experiment.searchNotApplicable')}</State>;
      case 'PENDING':
        return <State kind="loading">{t('experiment.searchPending')}</State>;
      case 'RUNNING':
        return (
          <State kind="loading">
            {t('experiment.searchRunning', { count: data.search_result.evaluated_count })}
          </State>
        );
      case 'COMPLETED':
        return (
          <>
            <Badge>COMPLETED</Badge>
            <p>{t('experiment.evaluations', { count: data.search_result.evaluated_count })}</p>
            {data.search_result.selected_parameters.map((parameter) => (
              <p key={parameter.key}>
                <strong>{parameter.key}</strong> {parameter.value}
              </p>
            ))}
            <p>
              {t('experiment.selectedMetric', {
                key: data.search_result.selected_metric.key,
                value: data.search_result.selected_metric.value,
                unit: data.search_result.selected_metric.unit ?? '',
              })}
            </p>
            <p>
              {t('experiment.resultRef', {
                type: data.search_result.result_ref.type,
                id: data.search_result.result_ref.id,
              })}
            </p>
          </>
        );
      case 'FAILED':
        return (
          <State kind="error">
            {localizedErrorCopy(data.search_result.failure_code, t, i18n.language)} ·{' '}
            {t('experiment.evaluations', { count: data.search_result.evaluated_count })}
          </State>
        );
      default:
        return assertNever(data.search_result);
    }
  })();
  return (
    <>
      <h1>{t('experiment.heading', { id: data.experiment_id })}</h1>
      <div className="workspace-tabs" role="tablist" aria-label={t('experiment.detail')}>
        {(
          [
            ['summary', 'experiment.tab.summary'],
            ['results', 'experiment.tab.results'],
            ['inputs', 'experiment.tab.inputs'],
            ['artifacts', 'experiment.tab.artifacts'],
            ['logs', 'experiment.tab.logs'],
          ] as const
        ).map(([tab, labelKey]) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            aria-controls="experiment-tab-panel"
            className={activeTab === tab ? undefined : 'secondary'}
            onClick={() =>
              void navigate({
                to: '/experiments/$experimentId',
                params: { experimentId },
                search: { tab },
              })
            }
          >
            {t(labelKey)}
          </button>
        ))}
      </div>
      <div id="experiment-tab-panel" role="tabpanel">
        {activeTab === 'summary' && (
          <div className="grid">
            <Panel title={t('experiment.summary')}>
              <Badge>{data.status}</Badge>
              <h3>{t('experiment.objective')}</h3>
              <p>{data.objective}</p>
              <h3>{t('experiment.hypothesis')}</h3>
              <p>{data.hypothesis}</p>
              <h3>{t('experiment.validity')}</h3>
              <p>{data.validity_state}</p>
              <dl className="definition">
                <dt>{t('field.research')}</dt>
                <dd>
                  <Link to="/research/$researchId" params={{ researchId: data.research_id }}>
                    {data.research_id}
                  </Link>{' '}
                  {t('field.revision')} {data.research_revision_no}
                </dd>
                <dt>{t('field.experimentType')}</dt>
                <dd>{data.experiment_type}</dd>
                <dt>{t('field.parent')}</dt>
                <dd>{data.parent_experiment_id ?? t('experiment.noParent')}</dd>
                <dt>{t('field.source')}</dt>
                <dd>{data.source_experiment_id ?? t('experiment.originalSource')}</dd>
                <dt>{t('field.factor')}</dt>
                <dd>
                  {data.factor_ref
                    ? `${data.factor_ref.id} v${data.factor_ref.version}`
                    : t('common.none')}
                </dd>
                <dt>{t('field.strategy')}</dt>
                <dd>
                  {data.strategy_ref
                    ? `${data.strategy_ref.id} v${data.strategy_ref.version}`
                    : t('common.none')}
                </dd>
              </dl>
              {data.invalid_reason_code && (
                <State kind="error">
                  {localizedErrorCopy(data.invalid_reason_code, t, i18n.language)}{' '}
                  {data.invalid_reason_detail}
                </State>
              )}
            </Panel>
            <Panel title={t('experiment.reproducibility')}>
              <dl className="definition">
                <dt>{t('field.datasetSnapshot')}</dt>
                <dd>{data.data_snapshot_id}</dd>
                <dt>{t('field.parametersHash')}</dt>
                <dd>
                  <code>{data.parameters_sha256}</code>
                </dd>
                <dt>{t('field.engineAdapter')}</dt>
                <dd>
                  {data.engine.name}@{data.engine.version} /{' '}
                  {data.adapter ? `${data.adapter.name}@${data.adapter.version}` : t('common.none')}
                </dd>
                <dt>{t('field.policyCostModel')}</dt>
                <dd>{data.cost_model_id}</dd>
                <dt>{t('field.codeVersion')}</dt>
                <dd>{data.code_version}</dd>
              </dl>
              {data.provenance ? (
                <Provenance value={data.provenance} />
              ) : (
                <State kind="error">
                  {localizedErrorCopy('NON_REPRODUCIBLE', t, i18n.language)}
                </State>
              )}
              {reproduceCapability &&
                reproduceCapability.visibility !== 'HIDE' &&
                data.provenance && (
                  <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
                    <Dialog.Trigger asChild>
                      <Capability
                        item={reproduceCapability}
                        label={t('action.reproduce')}
                        busy={reproduce.isPending}
                        confirmationHandled
                        onClick={() => undefined}
                      />
                    </Dialog.Trigger>
                    <Dialog.Portal>
                      <Dialog.Overlay className="dialog-overlay" />
                      <Dialog.Content className="decision-dialog" aria-describedby={undefined}>
                        <Dialog.Title>{t('experiment.confirmReproduce')}</Dialog.Title>
                        <label>
                          {t('experiment.reproduceMode')}
                          <select
                            value={mode}
                            onChange={(event) =>
                              setMode(event.target.value as 'EXACT' | 'CONTROLLED_OVERRIDE')
                            }
                          >
                            <option value="EXACT">EXACT</option>
                            <option value="CONTROLLED_OVERRIDE">CONTROLLED_OVERRIDE</option>
                          </select>
                        </label>
                        <dl className="definition">
                          <dt>{t('field.sourceExperiment')}</dt>
                          <dd>{data.experiment_id}</dd>
                          <dt>{t('field.datasetSnapshot')}</dt>
                          <dd>{data.data_snapshot_id}</dd>
                          <dt>{t('field.parametersHash')}</dt>
                          <dd>
                            <code>{data.parameters_sha256}</code>
                          </dd>
                          <dt>{t('field.engineAdapter')}</dt>
                          <dd>
                            {data.engine.name}@{data.engine.version} /{' '}
                            {data.adapter
                              ? `${data.adapter.name}@${data.adapter.version}`
                              : t('common.none')}
                          </dd>
                          <dt>{t('field.policyCostModel')}</dt>
                          <dd>
                            {data.provenance.policies.map((policy) => policy.id).join(', ') ||
                              t('common.none')}{' '}
                            / {data.cost_model_id}
                          </dd>
                          <dt>{t('field.codeVersion')}</dt>
                          <dd>{data.code_version}</dd>
                        </dl>
                        {mode === 'CONTROLLED_OVERRIDE' && (
                          <fieldset>
                            <legend>{t('experiment.controlledOverrides')}</legend>
                            <label>
                              {t('field.engineVersion')}
                              <input
                                value={engineVersion}
                                onChange={(event) => setEngineVersion(event.target.value)}
                              />
                            </label>
                            <label>
                              {t('field.adapterVersion')}
                              <input
                                value={adapterVersion}
                                onChange={(event) => setAdapterVersion(event.target.value)}
                              />
                            </label>
                            <label>
                              {t('field.codeVersion')}
                              <input
                                value={codeVersion}
                                onChange={(event) => setCodeVersion(event.target.value)}
                              />
                            </label>
                            <label>
                              {t('experiment.requiredReason')}
                              <textarea
                                value={overrideReason}
                                maxLength={4000}
                                onChange={(event) => setOverrideReason(event.target.value)}
                              />
                            </label>
                          </fieldset>
                        )}
                        {reproduce.error && <Problem error={reproduce.error} />}
                        <button
                          disabled={
                            reproduce.isPending ||
                            (mode === 'CONTROLLED_OVERRIDE' && !controlledReady)
                          }
                          onClick={submitReproduce}
                        >
                          {reproduce.isPending
                            ? t('experiment.submitting')
                            : t('experiment.confirm')}
                        </button>
                        <Dialog.Close asChild>
                          <button className="secondary">{t('common.cancel')}</button>
                        </Dialog.Close>
                      </Dialog.Content>
                    </Dialog.Portal>
                  </Dialog.Root>
                )}
              <button disabled title={t('experiment.rerunReason')}>
                {t('experiment.rerunUnavailable')}
              </button>
              {accepted && (
                <State kind="empty">
                  {t('experiment.reproduceAccepted', {
                    mode: accepted.reproduce_mode,
                    jobId: accepted.job_id,
                    status: job.data?.body.status ?? accepted.status,
                    sourceId: accepted.source_experiment_id,
                  })}{' '}
                  <Link
                    to="/experiments/$experimentId"
                    params={{ experimentId: accepted.resource_ref.id }}
                  >
                    {t('experiment.newExperiment', { id: accepted.resource_ref.id })}
                  </Link>{' '}
                  <Provenance value={accepted.source_provenance} />
                </State>
              )}
              {job.error && <Problem error={job.error} />}
            </Panel>
          </div>
        )}
        {activeTab === 'inputs' && (
          <Panel title={t('experiment.inputsSearch')}>
            {data.parameters.map((parameter) => (
              <p key={parameter.key}>
                <strong>{parameter.key}</strong> {parameter.value}
              </p>
            ))}
            <h3>{t('experiment.searchConfiguration')}</h3>
            {data.search_configuration ? (
              <p>
                {data.search_configuration.method} ·{' '}
                {data.search_configuration.objective_metric_key} ·{' '}
                {data.search_configuration.objective_direction} ·{' '}
                {t('experiment.maxEvaluations', {
                  count: data.search_configuration.max_evaluations,
                })}{' '}
                ·{' '}
                {t('experiment.seed', {
                  value: data.search_configuration.seed ?? t('agent.serverDefault'),
                })}
              </p>
            ) : (
              <State kind="empty">{t('experiment.noSearchConfiguration')}</State>
            )}
            <h3>{t('experiment.searchDimensions')}</h3>
            {data.search_space.length === 0 ? (
              <State kind="empty">{t('experiment.noSearchDimensions')}</State>
            ) : (
              data.search_space.map((dimension) => {
                switch (dimension.kind) {
                  case 'SET':
                    return (
                      <p key={dimension.parameter_key}>
                        <strong>{dimension.parameter_key}</strong> SET {dimension.value_type}:{' '}
                        {dimension.values.join(', ')}
                      </p>
                    );
                  case 'RANGE':
                    return (
                      <p key={dimension.parameter_key}>
                        <strong>{dimension.parameter_key}</strong> RANGE {dimension.value_type}:{' '}
                        {dimension.minimum}…{dimension.maximum} {t('experiment.step')}{' '}
                        {dimension.step}
                      </p>
                    );
                  default:
                    return assertNever(dimension);
                }
              })
            )}
            <p>
              {t('experiment.lineage')}{' '}
              {data.source_experiment_id ? (
                <Link
                  to="/experiments/$experimentId"
                  params={{ experimentId: data.source_experiment_id }}
                >
                  {data.source_experiment_id}
                </Link>
              ) : (
                t('experiment.originalSource')
              )}
            </p>
          </Panel>
        )}
        {activeTab === 'results' && (
          <div className="grid">
            <Panel title={t('experiment.searchResult')}>{searchResult}</Panel>
            <Panel title={t('experiment.calculatedMetrics')}>
              {data.metrics.length === 0 ? (
                <State kind="empty">{t('experiment.noMetrics')}</State>
              ) : (
                data.metrics.map((metric) => (
                  <p key={metric.key}>
                    <strong>{metric.key}</strong> {metric.value} {metric.unit ?? ''}
                  </p>
                ))
              )}
            </Panel>
          </div>
        )}
        {activeTab === 'artifacts' && (
          <Panel title={t('research.authorizedArtifacts')}>
            {data.artifacts.length === 0 ? (
              <State kind="empty">{t('experiment.noArtifacts')}</State>
            ) : (
              data.artifacts.map((artifact) => (
                <article className="row-card" key={artifact.artifact.id}>
                  <Badge>{artifact.kind}</Badge>
                  <strong>{artifact.artifact.id}</strong>
                  <span>
                    {artifact.media_type} · {t('common.bytes', { count: artifact.size_bytes })} ·{' '}
                    {artifact.sha256}
                  </span>
                  <Provenance value={artifact.provenance} />
                </article>
              ))
            )}
          </Panel>
        )}
        {activeTab === 'logs' && (
          <Panel title={t('experiment.executionIdentity')}>
            <p>{t('research.job', { id: data.job_id ?? t('common.none') })}</p>
            <p>
              {t('experiment.toolCall', { id: data.provenance?.tool_call_id ?? t('common.none') })}
            </p>
            <p>
              {t('field.started')}{' '}
              {data.started_at ? (
                <ServerTime value={data.started_at} />
              ) : (
                t('experiment.notStarted')
              )}
            </p>
            <p>
              {t('field.finished')}{' '}
              {data.finished_at ? (
                <ServerTime value={data.finished_at} />
              ) : (
                t('experiment.notFinished')
              )}
            </p>
            <p>
              {t('field.created')} <ServerTime value={data.created_at} />
            </p>
            <p>
              {t('experiment.invalidated')}{' '}
              {data.invalidated_at ? (
                <ServerTime value={data.invalidated_at} />
              ) : (
                t('experiment.notInvalidated')
              )}
            </p>
            <p>
              {t('experiment.invalidReason', {
                reason: data.invalid_reason_detail ?? t('common.none'),
              })}
            </p>
            <Provenance value={data.provenance} />
          </Panel>
        )}
      </div>
    </>
  );
}

export function StrategyLanding() {
  const { t } = useTranslation();
  const [created, setCreated] = useState<Schema<'StrategyVersionDetail'>>();
  const mutation = useMutation({
    mutationFn: (body: Schema<'StrategyCreateRequest'>) => api.createStrategy(body),
    onSuccess: ({ body }) => setCreated(body),
  });
  return (
    <>
      <h1>{t('page.strategy')}</h1>
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          mutation.mutate({
            research_id: String(data.get('research_id')),
            name: String(data.get('name')),
            thesis: String(data.get('thesis')),
            universe: {
              asset_class: 'EQUITY',
              symbols: String(data.get('symbols'))
                .split(',')
                .map((symbol) => symbol.trim())
                .filter(Boolean),
              universe_id: null,
            },
            signals: [
              {
                factor_id: String(data.get('factor_id')),
                factor_version: Number(data.get('factor_version')),
                direction: 'LONG',
                weight: '1',
              },
            ],
            rules: {
              selection_count: Number(data.get('selection_count')),
              weighting: 'EQUAL',
              rebalance_frequency: 'MONTHLY',
              long_short: false,
              leverage_limit: '1',
              position_limit: '0.1',
            },
            cost_model_id: String(data.get('cost_model_id')),
            benchmark: String(data.get('benchmark')),
            research_period: {
              start: String(data.get('research_start')),
              end: String(data.get('research_end')),
            },
            validation_period: {
              start: String(data.get('validation_start')),
              end: String(data.get('validation_end')),
            },
            holdout_period: {
              start: String(data.get('holdout_start')),
              end: String(data.get('holdout_end')),
            },
            known_failure_modes: [String(data.get('failure_mode'))],
          });
        }}
      >
        <div className="grid">
          <label>
            {t('field.researchId')}
            <input name="research_id" required />
          </label>
          <label>
            {t('strategy.name')}
            <input name="name" required />
          </label>
          <label>
            {t('field.thesis')}
            <input name="thesis" required />
          </label>
          <label>
            {t('strategy.symbols')}
            <input name="symbols" required />
          </label>
          <label>
            {t('field.factorId')}
            <input name="factor_id" required />
          </label>
          <label>
            {t('field.factorVersion')}
            <input name="factor_version" type="number" min="1" required />
          </label>
          <label>
            {t('field.selectionCount')}
            <input name="selection_count" type="number" min="1" required />
          </label>
          <label>
            {t('field.costModelId')}
            <input name="cost_model_id" required />
          </label>
          <label>
            {t('field.benchmark')}
            <input name="benchmark" required />
          </label>
          <label>
            {t('field.researchStart')}
            <input name="research_start" type="date" required />
          </label>
          <label>
            {t('field.researchEnd')}
            <input name="research_end" type="date" required />
          </label>
          <label>
            {t('field.validationStart')}
            <input name="validation_start" type="date" required />
          </label>
          <label>
            {t('field.validationEnd')}
            <input name="validation_end" type="date" required />
          </label>
          <label>
            {t('field.holdoutStart')}
            <input name="holdout_start" type="date" required />
          </label>
          <label>
            {t('field.holdoutEnd')}
            <input name="holdout_end" type="date" required />
          </label>
          <label>
            {t('strategy.knownFailureMode')}
            <input name="failure_mode" required />
          </label>
        </div>
        <button disabled={mutation.isPending}>
          {mutation.isPending ? t('common.creating') : t('strategy.createCandidate')}
        </button>
      </form>
      {mutation.error && <Problem error={mutation.error} />}
      {created && (
        <State kind="empty">
          {t('strategy.candidateCreated')}{' '}
          <Link
            to="/strategies/$strategyId"
            params={{ strategyId: created.strategy_id }}
            search={{ version: created.version }}
          >
            {created.strategy_id} v{created.version}
          </Link>
        </State>
      )}
    </>
  );
}
export function StrategyPage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false }) as { strategyId: string };
  const search = useSearch({ strict: false }) as {
    version?: number;
    tab?:
      | 'overview'
      | 'specification'
      | 'backtests'
      | 'trades'
      | 'risk'
      | 'sensitivity'
      | 'validation'
      | 'history';
  };
  const navigate = useNavigate();
  const client = useQueryClient();
  const freezeInFlight = useRef(false);
  const [snapshotId, setSnapshotId] = useState('');
  const [backtestEngine, setBacktestEngine] = useState('');
  const [backtestEngineVersion, setBacktestEngineVersion] = useState('');
  const [backtestParameterKey, setBacktestParameterKey] = useState('');
  const [backtestParameterValue, setBacktestParameterValue] = useState('');
  const [validationPolicy, setValidationPolicy] = useState('');
  const [strictEngine, setStrictEngine] = useState('');
  const [strictEngineVersion, setStrictEngineVersion] = useState('');
  const [testSuiteVersion, setTestSuiteVersion] = useState('');
  const [actionJob, setActionJob] = useState<Schema<'JobAccepted'>>();
  const strategyId = params.strategyId;
  const validStrategyId = isPublicId('strategy', strategyId);
  const version = search.version;
  const query = useQuery({
    queryKey: validStrategyId
      ? workspaceQueryKey('strategy', strategyId, version ?? 'current')
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) =>
      version === undefined
        ? api.currentStrategyVersion(strategyId, signal)
        : api.strategyVersion(strategyId, version, signal),
    enabled: validStrategyId,
  });
  useEffect(() => {
    if (version !== undefined || !query.data) return;
    const expectedLocation = `/strategies/${encodeURIComponent(strategyId)}/versions/${query.data.body.version}`;
    if (!query.data.contentLocation?.endsWith(expectedLocation)) return;
    void navigate({
      to: '/strategies/$strategyId',
      params: { strategyId },
      search: search.tab
        ? { version: query.data.body.version, tab: search.tab }
        : { version: query.data.body.version },
      replace: true,
    });
  }, [navigate, query.data, search.tab, strategyId, version]);
  const freeze = useMutation({
    mutationFn: () => {
      if (!query.data?.etag) throw new Error('Server ETag required');
      return api.freezeStrategy(strategyId, query.data.body.version, query.data.etag, {
        expected_spec_sha256: query.data.body.spec_sha256,
      });
    },
    onSettled: () => {
      freezeInFlight.current = false;
      void client.invalidateQueries({ queryKey: workspaceQueryKey('strategy', strategyId) });
    },
  });
  const backtest = useMutation({
    mutationFn: () => {
      if (version === undefined) throw new Error('Explicit strategy version required');
      return api.runFastBacktest(strategyId, version, {
        snapshot_id: snapshotId,
        cost_model_id: query.data?.body.cost_model_id ?? '',
        engine_key: backtestEngine,
        engine_version: backtestEngineVersion,
        parameters: [{ key: backtestParameterKey, value: backtestParameterValue }],
      });
    },
    onSuccess: ({ body }) => setActionJob(body),
  });
  const startValidation = useMutation({
    mutationFn: () => {
      if (version === undefined) throw new Error('Explicit strategy version required');
      return api.createValidation({
        strategy_id: strategyId,
        strategy_version: version,
        policy_id: validationPolicy,
        strict_engine_key: strictEngine,
        strict_engine_version: strictEngineVersion,
        test_suite_version: testSuiteVersion,
      });
    },
    onSuccess: ({ body }) => setActionJob(body),
  });
  if (!validStrategyId) return <State kind="error">{t('route.invalidStrategy')}</State>;
  if (query.isLoading)
    return (
      <>
        <h1>{t('page.strategy')}</h1>
        <State kind="loading">{t('strategy.loading')}</State>
      </>
    );
  if (query.error)
    return (
      <>
        <h1>{t('page.strategy')}</h1>
        <Problem error={query.error} />
      </>
    );
  if (
    version === undefined &&
    query.data &&
    !query.data.contentLocation?.endsWith(
      `/strategies/${encodeURIComponent(strategyId)}/versions/${query.data.body.version}`,
    )
  )
    return <State kind="error">{t('strategy.contentLocationMismatch')}</State>;
  if (version === undefined)
    return (
      <State kind="loading">
        {t('strategy.resolvingVersion', {
          location: query.data?.contentLocation ?? 'server Content-Location',
        })}
      </State>
    );
  const data = query.data?.body;
  if (!data) return <State kind="empty" />;
  const activeTab = search.tab ?? 'overview';
  const tabs = [
    ['overview', 'strategy.tab.overview'],
    ['specification', 'strategy.tab.specification'],
    ['backtests', 'strategy.tab.backtests'],
    ['trades', 'strategy.tab.trades'],
    ['risk', 'strategy.tab.risk'],
    ['sensitivity', 'strategy.tab.sensitivity'],
    ['validation', 'strategy.tab.validation'],
    ['history', 'strategy.tab.history'],
  ] as const;
  const latestBacktest = (() => {
    switch (data.latest_backtest.state) {
      case 'AVAILABLE':
        return (
          <>
            <dl className="definition">
              <dt>{t('field.experiment')}</dt>
              <dd>
                <Link
                  to="/experiments/$experimentId"
                  params={{ experimentId: data.latest_backtest.result.experiment.id }}
                  search={{ tab: 'results' }}
                >
                  {data.latest_backtest.result.experiment.id}
                </Link>
              </dd>
              <dt>{t('field.status')}</dt>
              <dd>{data.latest_backtest.result.status}</dd>
              <dt>{t('field.validity')}</dt>
              <dd>{data.latest_backtest.result.validity_state}</dd>
              <dt>{t('field.resultHash')}</dt>
              <dd>
                <code>{data.latest_backtest.result.result_sha256}</code>
              </dd>
              <dt>{t('field.job')}</dt>
              <dd>{data.latest_backtest.result.job_id ?? t('strategy.noAsynchronousJob')}</dd>
              <dt>{t('field.started')}</dt>
              <dd>
                <ServerTime value={data.latest_backtest.result.started_at} />
              </dd>
              <dt>{t('field.finished')}</dt>
              <dd>
                <ServerTime value={data.latest_backtest.result.finished_at} />
              </dd>
            </dl>
            <ul>
              {data.latest_backtest.metrics.map((metric) => (
                <li key={metric.key}>
                  {metric.key}: {metric.value} {metric.unit ?? ''}
                </li>
              ))}
            </ul>
            <Suspense fallback={<State kind="loading">{t('strategy.loadingChart')}</State>}>
              <CanonicalChart chart={data.latest_backtest.chart} />
            </Suspense>
            <Provenance value={data.latest_backtest.result.provenance} />
          </>
        );
      case 'EMPTY':
        return <State kind="empty">{t('strategy.noBacktest')}</State>;
      case 'LOCKED':
        return <State kind="permission">{t('strategy.backtestLocked')}</State>;
      default:
        return assertNever(data.latest_backtest);
    }
  })();
  const validationSummary = data.validation_summary;
  const backtestCapability = data.action_capabilities.find(
    (capability) => capability.action === 'run_fast_backtest',
  );
  const validationCapability = data.action_capabilities.find(
    (capability) => capability.action === 'start_validation',
  );
  return (
    <>
      <h1>
        {data.name} · v{data.version}
      </h1>
      <nav className="workspace-tabs" aria-label={t('strategy.details')}>
        {tabs.map(([tab, labelKey]) => (
          <Link
            key={tab}
            to="/strategies/$strategyId"
            params={{ strategyId }}
            search={{ version: data.version, tab }}
            aria-current={activeTab === tab ? 'page' : undefined}
          >
            {t(labelKey)}
          </Link>
        ))}
      </nav>
      {query.isFetching && <State kind="loading">{t('strategy.refreshing')}</State>}
      {activeTab === 'overview' && (
        <Panel title={t('strategy.overview')}>
          <Badge>{data.lifecycle_state}</Badge>
          {data.is_frozen && <State kind="permission">{t('strategy.frozen')}</State>}
          <dl className="definition">
            <dt>{t('field.thesis')}</dt>
            <dd>{data.thesis}</dd>
            <dt>{t('field.benchmark')}</dt>
            <dd>{data.benchmark}</dd>
            <dt>{t('field.specHash')}</dt>
            <dd>
              <code>{data.spec_sha256}</code>
            </dd>
            <dt>{t('field.universe')}</dt>
            <dd>{data.universe.symbols.join(', ')}</dd>
          </dl>
          <CapabilityFieldset
            item={backtestCapability}
            legend={t('strategy.fastBacktestInputs')}
            busy={backtest.isPending}
          >
            <label>
              {t('field.datasetSnapshotId')}
              <input value={snapshotId} onChange={(event) => setSnapshotId(event.target.value)} />
            </label>
            <label>
              {t('field.engineKey')}
              <input
                value={backtestEngine}
                onChange={(event) => setBacktestEngine(event.target.value)}
              />
            </label>
            <label>
              {t('field.engineVersion')}
              <input
                value={backtestEngineVersion}
                onChange={(event) => setBacktestEngineVersion(event.target.value)}
              />
            </label>
            <label>
              {t('field.parameterKey')}
              <input
                value={backtestParameterKey}
                onChange={(event) => setBacktestParameterKey(event.target.value)}
              />
            </label>
            <label>
              {t('field.parameterValue')}
              <input
                value={backtestParameterValue}
                onChange={(event) => setBacktestParameterValue(event.target.value)}
              />
            </label>
          </CapabilityFieldset>
          <CapabilityFieldset
            item={validationCapability}
            legend={t('strategy.strictValidationInputs')}
            busy={startValidation.isPending}
          >
            <label>
              {t('strategy.validationPolicyId')}
              <input
                value={validationPolicy}
                onChange={(event) => setValidationPolicy(event.target.value)}
              />
            </label>
            <label>
              {t('strategy.strictEngineKey')}
              <input
                value={strictEngine}
                onChange={(event) => setStrictEngine(event.target.value)}
              />
            </label>
            <label>
              {t('strategy.strictEngineVersion')}
              <input
                value={strictEngineVersion}
                onChange={(event) => setStrictEngineVersion(event.target.value)}
              />
            </label>
            <label>
              {t('strategy.testSuiteVersion')}
              <input
                value={testSuiteVersion}
                onChange={(event) => setTestSuiteVersion(event.target.value)}
              />
            </label>
          </CapabilityFieldset>
          <div>
            {data.action_capabilities.map((capability) => (
              <Capability
                key={capability.action}
                item={capability}
                busy={freeze.isPending || backtest.isPending || startValidation.isPending}
                onClick={
                  capability.action === 'freeze'
                    ? () => {
                        if (freezeInFlight.current) return;
                        freezeInFlight.current = true;
                        freeze.mutate();
                      }
                    : capability.action === 'start_validation' &&
                        validationPolicy.trim() &&
                        strictEngine.trim() &&
                        strictEngineVersion.trim() &&
                        testSuiteVersion.trim()
                      ? () => startValidation.mutate()
                      : capability.action === 'run_fast_backtest' &&
                          snapshotId.trim() &&
                          backtestEngine.trim() &&
                          backtestEngineVersion.trim() &&
                          backtestParameterKey.trim() &&
                          backtestParameterValue.trim()
                        ? () => backtest.mutate()
                        : undefined
                }
              />
            ))}
          </div>
          {freeze.error && <Problem error={freeze.error} />}
          {backtest.error && <Problem error={backtest.error} />}
          {startValidation.error && <Problem error={startValidation.error} />}
          {actionJob && (
            <State kind="empty">
              {t('strategy.serverJob', { jobId: actionJob.job_id, status: actionJob.status })}
              {actionJob.resource_ref?.type === 'validation' && (
                <Link
                  to="/validation/$validationId"
                  params={{ validationId: actionJob.resource_ref.id }}
                >
                  {t('approval.openValidation', { id: actionJob.resource_ref.id })}
                </Link>
              )}
            </State>
          )}
        </Panel>
      )}
      {activeTab === 'specification' && (
        <Panel title={t('strategy.specification')}>
          <p>{data.specification.thesis}</p>
          <dl className="definition">
            <dt>{t('field.universe')}</dt>
            <dd>{data.specification.universe.symbols.join(', ')}</dd>
            <dt>{t('field.selectionCount')}</dt>
            <dd>{data.specification.rules.selection_count}</dd>
            <dt>{t('field.weighting')}</dt>
            <dd>{data.specification.rules.weighting}</dd>
            <dt>{t('field.rebalance')}</dt>
            <dd>{data.specification.rules.rebalance_frequency}</dd>
            <dt>{t('field.longShort')}</dt>
            <dd>
              {data.specification.rules.long_short ? t('strategy.enabled') : t('strategy.disabled')}
            </dd>
            <dt>{t('field.leverageLimit')}</dt>
            <dd>{data.specification.rules.leverage_limit}</dd>
            <dt>{t('field.positionLimit')}</dt>
            <dd>{data.specification.rules.position_limit}</dd>
            <dt>{t('field.costModel')}</dt>
            <dd>{data.specification.cost_model_id}</dd>
            <dt>{t('field.benchmark')}</dt>
            <dd>{data.specification.benchmark}</dd>
            <dt>{t('field.researchPeriod')}</dt>
            <dd>
              {data.specification.research_period.start} – {data.specification.research_period.end}
            </dd>
            <dt>{t('field.validationPeriod')}</dt>
            <dd>
              {data.specification.validation_period.start} –{' '}
              {data.specification.validation_period.end}
            </dd>
            <dt>{t('field.holdoutPeriod')}</dt>
            <dd>
              {data.specification.holdout_period.start} – {data.specification.holdout_period.end}
            </dd>
            <dt>{t('field.specificationHash')}</dt>
            <dd>
              <code>{data.specification.spec_sha256}</code>
            </dd>
          </dl>
          <h3>{t('field.signals')}</h3>
          {data.specification.signals.length === 0 ? (
            <State kind="empty">{t('strategy.noSignals')}</State>
          ) : (
            <ul>
              {data.specification.signals.map((signal) => (
                <li key={`${signal.factor_id}:${signal.factor_version}`}>
                  {signal.factor_id} v{signal.factor_version} · {signal.direction} · {signal.weight}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
      {activeTab === 'backtests' && (
        <Panel title={t('strategy.latestBacktest')}>{latestBacktest}</Panel>
      )}
      {activeTab === 'trades' && (
        <Panel title={t('strategy.trades')}>
          <State kind="empty">{t('strategy.noTrades')}</State>
        </Panel>
      )}
      {activeTab === 'risk' && (
        <Panel title={t('strategy.riskControls')}>
          <dl className="definition">
            <dt>{t('field.leverageLimit')}</dt>
            <dd>{data.rules.leverage_limit}</dd>
            <dt>{t('field.positionLimit')}</dt>
            <dd>{data.rules.position_limit}</dd>
          </dl>
          <h3>{t('strategy.failureModes')}</h3>
          {data.known_failure_modes.length === 0 ? (
            <State kind="empty">{t('strategy.noFailureModes')}</State>
          ) : (
            <ul>
              {data.known_failure_modes.map((mode) => (
                <li key={mode}>{mode}</li>
              ))}
            </ul>
          )}
        </Panel>
      )}
      {activeTab === 'sensitivity' && (
        <Panel title={t('strategy.sensitivityEvidence')}>
          {data.artifacts.length === 0 ? (
            <State kind="empty">{t('strategy.noArtifacts')}</State>
          ) : (
            <ul>
              {data.artifacts.map((artifact) => (
                <li key={`${artifact.artifact.id}:${artifact.artifact.revision}`}>
                  <strong>{artifact.kind}</strong> · {artifact.media_type} ·{' '}
                  {t('common.bytes', { count: artifact.size_bytes })} ·{' '}
                  <code>{artifact.sha256}</code> <Provenance value={artifact.provenance} />
                </li>
              ))}
            </ul>
          )}
          {data.provenance.map((value) => (
            <Provenance key={value.provenance_id} value={value} />
          ))}
        </Panel>
      )}
      {activeTab === 'validation' && (
        <Panel title={t('validation.summary')}>
          {validationSummary === null ? (
            <State kind="empty">{t('strategy.noValidation')}</State>
          ) : (
            <>
              <Link
                to="/validation/$validationId"
                params={{ validationId: validationSummary.validation.id }}
              >
                {t('approval.openValidation', { id: validationSummary.validation.id })}
              </Link>
              <dl className="definition">
                <dt>{t('field.status')}</dt>
                <dd>{validationSummary.status}</dd>
                <dt>{t('field.result')}</dt>
                <dd>{validationSummary.result ?? t('strategy.pending')}</dd>
                <dt>{t('field.holdout')}</dt>
                <dd>{validationSummary.holdout_state}</dd>
                <dt>{t('field.revision')}</dt>
                <dd>{validationSummary.revision}</dd>
                {Object.entries(validationSummary.test_counts).map(([state, count]) => (
                  <div key={state} className="definition-pair">
                    <dt>{state}</dt>
                    <dd>{count}</dd>
                  </div>
                ))}
              </dl>
              <Provenance value={validationSummary.provenance} />
            </>
          )}
        </Panel>
      )}
      {activeTab === 'history' && (
        <Panel title={t('strategy.versionHistory')}>
          <dl className="definition">
            <dt>{t('field.version')}</dt>
            <dd>{data.version}</dd>
            <dt>{t('field.revision')}</dt>
            <dd>{data.revision}</dd>
            <dt>{t('field.lifecycle')}</dt>
            <dd>{data.lifecycle_state}</dd>
            <dt>{t('field.frozenAt')}</dt>
            <dd>
              {data.frozen_at ? <ServerTime value={data.frozen_at} /> : t('strategy.notFrozen')}
            </dd>
            <dt>{t('field.frozenBy')}</dt>
            <dd>{data.frozen_by ?? t('strategy.notFrozen')}</dd>
            <dt>{t('field.created')}</dt>
            <dd>
              <ServerTime value={data.created_at} />
            </dd>
          </dl>
          {data.provenance.map((value) => (
            <Provenance key={value.provenance_id} value={value} />
          ))}
        </Panel>
      )}
    </>
  );
}

export function ValidationLanding() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t('page.validation')}</h1>
      <State kind="empty">{t('validation.openId')}</State>
    </>
  );
}
export function ValidationPage() {
  const { i18n, t } = useTranslation();
  const { validationId } = useParams({ strict: false }) as { validationId: string };
  const validValidationId = isPublicId('validation', validationId);
  const navigate = useNavigate();
  const client = useQueryClient();
  const [selected, setSelected] = useState<string>();
  const [reason, setReason] = useState('');
  const [actionError, setActionError] = useState<unknown>();
  const actionInFlight = useRef(false);
  const validation = useQuery({
    queryKey: validValidationId
      ? workspaceQueryKey('validation', validationId)
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.validation(validationId, signal),
    enabled: validValidationId,
  });
  const gate = useQuery({
    queryKey: validValidationId
      ? workspaceQueryKey('holdout', validationId)
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.holdoutGate(validationId, signal),
    enabled: validValidationId,
  });
  const result = useQuery({
    queryKey: validValidationId
      ? workspaceQueryKey('holdout-result', validationId)
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.holdoutResult(validationId, signal),
    enabled: validValidationId && gate.data?.body.state === 'EXPOSED',
  });
  const action = useMutation({
    mutationFn: async (actionName: string) => {
      if (actionName === 'request_holdout_approval') {
        if (!validation.data?.etag) throw new Error('Validation ETag required');
        return api.requestHoldoutApproval(validationId, validation.data.etag, { reason });
      }
      if (!gate.data?.etag) throw new Error('Holdout gate ETag required');
      if (actionName === 'run_holdout' && gate.data.body.approval)
        return api.runHoldout(validationId, gate.data.etag, {
          approval_id: gate.data.body.approval.approval_id,
        });
      throw new Error('Unsupported action');
    },
    onError: setActionError,
    onSettled: () => {
      actionInFlight.current = false;
      void client.invalidateQueries({ queryKey: workspaceQueryKey('validation', validationId) });
      void client.invalidateQueries({ queryKey: workspaceQueryKey('holdout', validationId) });
    },
  });
  const runAction = (actionName: string) => {
    if (actionInFlight.current) return;
    actionInFlight.current = true;
    action.mutate(actionName);
  };
  if (!validValidationId) return <State kind="error">{t('route.invalidValidation')}</State>;
  if (validation.isLoading || gate.isLoading) return <State kind="loading" />;
  if (validation.error) return <Problem error={validation.error} />;
  if (gate.error) return <Problem error={gate.error} />;
  const detail = validation.data?.body;
  const holdout = gate.data?.body;
  if (!detail || !holdout) return <State kind="empty" />;
  const selectedTest = detail.tests.find((test) => test.test_key === selected) ?? detail.tests[0];
  const counts = detail.tests.reduce<Record<string, number>>(
    (total, test) => ({ ...total, [test.state]: (total[test.state] ?? 0) + 1 }),
    {},
  );
  const holdoutActions = new Set(['request_holdout_approval', 'run_holdout']);
  const validationCapabilities = detail.action_capabilities.filter(
    (capability) => !holdoutActions.has(capability.action),
  );
  const holdoutCapabilities = mergeActionCapabilities(
    detail.action_capabilities.filter((capability) => holdoutActions.has(capability.action)),
    holdout.action_capabilities,
  );
  const testInspector = selectedTest && (
    <>
      <Badge>{selectedTest.state}</Badge>
      <p>{selectedTest.purpose}</p>
      <p>{selectedTest.configuration_summary}</p>
      <p>{selectedTest.calculated_result}</p>
      <p>{selectedTest.interpretation}</p>
      {selectedTest.failure_code && (
        <State kind="error">
          {localizedErrorCopy(selectedTest.failure_code, t, i18n.language)}{' '}
          {selectedTest.failure_detail}
        </State>
      )}
      <p>
        {t('validation.artifacts', {
          ids: selectedTest.artifact_ids.join(', ') || t('common.none'),
        })}
      </p>
      <Provenance value={selectedTest.provenance} />
      <strong>{t('validation.noOverride')}</strong>
    </>
  );
  return (
    <>
      <h1>{t('validation.heading', { id: detail.validation_id })}</h1>
      <div className="summary" aria-label={t('validation.summary')}>
        <Badge>{detail.result ?? detail.status}</Badge>
        <span>PASS {counts.PASS ?? 0}</span>
        <span>WARN {counts.WARN ?? 0}</span>
        <span>FAIL {counts.FAIL ?? 0}</span>
      </div>
      {(counts.FAIL ?? 0) > 0 && (
        <State kind="error">
          {t('validation.mandatoryFailure')}
          <br />
          <Link to="/research">{t('validation.returnResearch')}</Link>
        </State>
      )}
      <div className="actions">
        {validationCapabilities.map((capability) => (
          <Capability
            key={capability.action}
            item={capability}
            onClick={
              capability.action === 'return_to_research'
                ? () => void navigate({ to: '/research' })
                : capability.action === 'view_strategy'
                  ? () =>
                      void navigate({
                        to: '/strategies/$strategyId',
                        params: { strategyId: detail.strategy.id },
                        search: { version: detail.strategy.version },
                      })
                  : undefined
            }
          />
        ))}
      </div>
      <div className="validation-layout">
        <Panel title={t('domainComponent.validationMatrix')}>
          <table>
            <thead>
              <tr>
                <th>{t('validation.test')}</th>
                <th>{t('validation.purpose')}</th>
                <th>{t('domainComponent.state')}</th>
                <th>{t('validation.result')}</th>
              </tr>
            </thead>
            <tbody>
              {detail.tests.map((test) => (
                <tr
                  key={`${test.test_key}:${test.attempt_no}`}
                  className={test.state === 'FAIL' ? 'failed-row' : ''}
                >
                  <td>
                    <button className="text-button" onClick={() => setSelected(test.test_key)}>
                      {test.test_key}
                    </button>
                  </td>
                  <td>{test.purpose}</td>
                  <td>
                    <Badge>{test.state}</Badge>
                  </td>
                  <td>{test.calculated_result ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Inspector
            title={t('validation.inspector')}
            trigger={
              <button className="mobile-inspector-trigger">{t('validation.openInspector')}</button>
            }
          >
            {testInspector}
          </Inspector>
        </Panel>
        <aside className="validation-inspector panel">
          <h2>{t('validation.inspector')}</h2>
          {testInspector}
        </aside>
      </div>
      <Panel title={t('domainComponent.holdoutGate')}>
        <Badge>{holdout.state}</Badge>
        <p>{t('validation.exposureCount', { count: holdout.exposure_count })}</p>
        <p>{t('validation.subjectRevision', { revision: holdout.revision })}</p>
        {holdout.state !== 'EXPOSED' && (
          <State kind="permission">{t('validation.protectedMetrics')}</State>
        )}
        {result.error && <Problem error={result.error} />}
        {result.data && (
          <>
            <Badge>{result.data.body.result}</Badge>
            <p>
              {t('validation.exposure', { id: result.data.body.exposure_id })} ·{' '}
              <ServerTime value={result.data.body.exposed_at} />
            </p>
            <dl className="definition">
              {result.data.body.metrics.map((metric) => (
                <div key={metric.key} className="definition-pair">
                  <dt>{metric.key}</dt>
                  <dd>
                    {metric.value} {metric.unit}
                  </dd>
                </div>
              ))}
            </dl>
            <Provenance value={result.data.body.provenance} />
          </>
        )}
        <label>
          {t('validation.approvalReason')}
          <input value={reason} onChange={(event) => setReason(event.target.value)} />
        </label>
        <div>
          {holdoutCapabilities.map((capability) => (
            <Capability
              key={capability.action}
              item={capability}
              busy={action.isPending}
              onClick={
                capability.action === 'request_holdout_approval' && reason.trim()
                  ? () => runAction(capability.action)
                  : capability.action === 'run_holdout' && holdout.approval
                    ? () => runAction(capability.action)
                    : undefined
              }
            />
          ))}
        </div>
        {actionError !== undefined && <Problem error={actionError} />}
        {action.data && 'approval_id' in action.data.body && (
          <State kind="empty">
            {t('validation.approvalRequested')}{' '}
            <Link to="/approvals/$approvalId" params={{ approvalId: action.data.body.approval_id }}>
              {action.data.body.approval_id}
            </Link>
          </State>
        )}
        {action.data && 'job_id' in action.data.body && (
          <State kind="empty">
            {t('validation.executionJob', {
              jobId: action.data.body.job_id,
              status: action.data.body.status,
            })}
          </State>
        )}
      </Panel>
    </>
  );
}

export function ApprovalListPage() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: workspaceQueryKey('approvals'),
    queryFn: ({ signal }) => api.approvals(signal),
  });
  if (query.isLoading) return <State kind="loading" />;
  if (query.error) return <Problem error={query.error} />;
  return (
    <>
      <h1>{t('page.approvals')}</h1>
      <Panel title={t('approval.queue')}>
        <table>
          <thead>
            <tr>
              <th>{t('approval.type')}</th>
              <th>{t('approval.subject')}</th>
              <th>{t('approval.status')}</th>
              <th>{t('approval.requested')}</th>
            </tr>
          </thead>
          <tbody>
            {query.data?.body.items.map((item) => (
              <tr key={item.approval_id}>
                <td>
                  <Link to="/approvals/$approvalId" params={{ approvalId: item.approval_id }}>
                    {item.type}
                  </Link>
                </td>
                <td>
                  {item.subject.id} · v{item.subject.version ?? '—'}
                </td>
                <td>
                  <Badge>{item.status}</Badge>
                </td>
                <td>
                  <ServerTime value={item.requested_at} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </>
  );
}
export function ApprovalPage() {
  const { t } = useTranslation();
  const { approvalId } = useParams({ strict: false }) as { approvalId: string };
  const validApprovalId = isPublicId('approval', approvalId);
  const client = useQueryClient();
  const [reason, setReason] = useState('');
  const [decisionError, setDecisionError] = useState<unknown>();
  const decisionInFlight = useRef(false);
  const query = useQuery({
    queryKey: validApprovalId
      ? workspaceQueryKey('approval', approvalId)
      : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.approval(approvalId, signal),
    enabled: validApprovalId,
  });
  const decide = useMutation({
    mutationFn: async (kind: 'approve' | 'reject') => {
      if (!query.data?.etag) throw new Error('Server ETag required');
      const hash = query.data.body.subject.sha256;
      return kind === 'approve'
        ? api.approveApproval(approvalId, query.data.etag, { acknowledged_subject_sha256: hash })
        : api.rejectApproval(approvalId, query.data.etag, {
            acknowledged_subject_sha256: hash,
            reason,
          });
    },
    onError: (error) => {
      setDecisionError(error);
      if (
        error instanceof ApiError &&
        (error.problem.code === 'APPROVAL_STALE' ||
          error.problem.code === 'REVISION_MISMATCH' ||
          error.problem.code === 'PRECONDITION_REQUIRED')
      )
        void query.refetch();
    },
    onSuccess: (result) => {
      setDecisionError(undefined);
      void client.invalidateQueries({
        queryKey: workspaceQueryKey('validation', result.body.subject_ref.id),
      });
      void client.invalidateQueries({
        queryKey: workspaceQueryKey('holdout', result.body.subject_ref.id),
      });
    },
    onSettled: () => {
      decisionInFlight.current = false;
      void client.invalidateQueries({ queryKey: workspaceQueryKey('approval', approvalId) });
      void client.invalidateQueries({ queryKey: workspaceQueryKey('approvals') });
    },
  });
  if (!validApprovalId) return <State kind="error">{t('route.invalidApproval')}</State>;
  if (query.isLoading) return <State kind="loading" />;
  if (query.error) return <Problem error={query.error} />;
  const data = query.data?.body;
  if (!data) return <State kind="empty" />;
  const approveCapability = data.action_capabilities.find((item) => item.action === 'approve');
  const rejectCapability = data.action_capabilities.find((item) => item.action === 'reject');
  const makeDecision = (kind: 'approve' | 'reject') => {
    if (decisionInFlight.current) return;
    decisionInFlight.current = true;
    decide.mutate(kind);
  };
  return (
    <>
      <h1>{t('approval.heading', { id: data.approval_id })}</h1>
      <Panel title={data.type}>
        <Badge>{data.status}</Badge>
        <p>{data.reason}</p>
        <p>
          {t('approval.subjectIdentity', {
            id: data.subject.id,
            version: data.subject.version ?? '—',
            revision: data.subject.revision,
          })}
        </p>
        <p>
          <code>{data.subject.sha256}</code>
        </p>
        {data.subject.type.toLowerCase().includes('validation') && (
          <Link to="/validation/$validationId" params={{ validationId: data.subject.id }}>
            {t('approval.openValidation', { id: data.subject.id })}
          </Link>
        )}
        {data.status === 'STALE' && <State kind="error">{t('approval.stale')}</State>}
        <h3>{t('approval.prerequisites')}</h3>
        {data.prerequisites.map((item) => (
          <p key={item.key}>
            <Badge>{item.state}</Badge> {item.detail}
          </p>
        ))}
        <div className="actions">
          {approveCapability && (
            <DecisionDialog
              item={approveCapability}
              title={t('approval.confirmApproval')}
              label={t('approval.reviewApprove')}
              busy={decide.isPending}
              detail={data}
              error={decisionError}
              successSignal={decide.isSuccess ? decide.submittedAt : 0}
              onBeforeOpen={async () => {
                setDecisionError(undefined);
                await query.refetch();
              }}
              onConfirm={() => makeDecision('approve')}
            >
              <p>{t('approval.exactHash')}</p>
            </DecisionDialog>
          )}
          {rejectCapability && (
            <DecisionDialog
              item={rejectCapability}
              title={t('approval.confirmRejection')}
              label={t('approval.reviewReject')}
              busy={decide.isPending}
              detail={data}
              error={decisionError}
              successSignal={decide.isSuccess ? decide.submittedAt : 0}
              onBeforeOpen={async () => {
                setDecisionError(undefined);
                await query.refetch();
              }}
              confirmDisabled={!reason.trim()}
              onConfirm={() => makeDecision('reject')}
            >
              <label>
                {t('approval.rejectionReason')}
                <input value={reason} onChange={(event) => setReason(event.target.value)} />
              </label>
            </DecisionDialog>
          )}
        </div>
        {decisionError !== undefined && <Problem error={decisionError} />}
      </Panel>
    </>
  );
}

function DecisionDialog({
  item,
  title,
  label,
  busy,
  confirmDisabled = false,
  detail,
  error,
  successSignal,
  onBeforeOpen,
  onConfirm,
  children,
}: {
  item: Schema<'ActionCapability'>;
  title: string;
  label: string;
  busy: boolean;
  confirmDisabled?: boolean;
  detail: Schema<'ApprovalDetail'>;
  error: unknown;
  successSignal: number;
  onBeforeOpen: () => Promise<void>;
  onConfirm: () => void;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  useEffect(() => {
    if (successSignal > 0) setOpen(false);
  }, [successSignal]);
  if (item.visibility === 'HIDE') return null;
  if (!item.requires_confirmation)
    return <Capability item={item} label={label} busy={busy} onClick={onConfirm} />;
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          setOpen(false);
          return;
        }
        setRefreshing(true);
        void onBeforeOpen().then(() => {
          setRefreshing(false);
          setOpen(true);
        });
      }}
    >
      <Dialog.Trigger asChild>
        <Capability
          item={item}
          label={label}
          busy={busy || refreshing}
          confirmationHandled
          onClick={() => undefined}
        />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="decision-dialog" aria-describedby={undefined}>
          <Dialog.Title>{title}</Dialog.Title>
          <dl className="definition">
            <dt>{t('approval.subjectId')}</dt>
            <dd>{detail.subject.id}</dd>
            <dt>{t('approval.versionRevision')}</dt>
            <dd>
              {detail.subject.version ?? '—'} / {detail.subject.revision}
            </dd>
            <dt>{t('approval.approvalRevision')}</dt>
            <dd>{detail.revision}</dd>
            <dt>{t('approval.subjectHash')}</dt>
            <dd>
              <code>{detail.subject.sha256}</code>
            </dd>
          </dl>
          <h3>{t('approval.effects')}</h3>
          {detail.effects.map((effect) => (
            <p key={effect.code}>
              <strong>{effect.code}</strong> {effect.detail}
            </p>
          ))}
          <h3>{t('approval.prerequisites')}</h3>
          {detail.prerequisites.map((prerequisite) => (
            <p key={prerequisite.key}>
              <Badge>{prerequisite.state}</Badge> <strong>{prerequisite.key}</strong>{' '}
              {prerequisite.detail}
            </p>
          ))}
          {children}
          {error !== undefined && <Problem error={error} />}
          <button
            data-testid={`capability-confirm-${item.action}`}
            onClick={onConfirm}
            disabled={busy || confirmDisabled || !item.allowed}
          >
            {busy ? t('common.saving') : t('approval.confirmVersioned')}
          </button>
          <Dialog.Close asChild>
            <button className="secondary">{t('common.cancel')}</button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function AgentsPage() {
  const { t } = useTranslation();
  const list = useQuery({
    queryKey: workspaceQueryKey('agents'),
    queryFn: ({ signal }) => api.agents(signal),
  });
  if (list.isLoading) return <State kind="loading" />;
  if (list.error) return <Problem error={list.error} />;
  return (
    <>
      <h1>{t('page.agents')}</h1>
      <State kind="permission">{t('agent.disableSemantics')}</State>
      <div className="grid">
        {list.data?.body.map((agent) => (
          <AgentCard key={agent.role_key} role={agent.role_key} />
        ))}
      </div>
    </>
  );
}

export function ActivityPage() {
  const { t } = useTranslation();
  const search = useSearch({ from: '/activity' });
  return (
    <>
      <h1>{t('page.activity')}</h1>
      <Panel title={t('activity.deepLink')}>
        {search.eventId && <p>{t('activity.event', { id: search.eventId })}</p>}
        {search.provenanceId && <p>{t('activity.provenance', { id: search.provenanceId })}</p>}
        {search.requestId && <p>{t('activity.request', { id: search.requestId })}</p>}
        {!search.eventId && !search.provenanceId && !search.requestId && (
          <State kind="empty">{t('activity.openLink')}</State>
        )}
        <p>{t('activity.serverOnly')}</p>
      </Panel>
    </>
  );
}
function AgentCard({ role }: { role: Schema<'AgentRoleKey'> }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [mutationError, setMutationError] = useState<unknown>();
  const updateInFlight = useRef(false);
  const query = useQuery({
    queryKey: workspaceQueryKey('agent', role),
    queryFn: ({ signal }) => api.agentConfig(role, signal),
  });
  const update = useMutation({
    mutationFn: async (enabled: boolean) => {
      if (!query.data?.etag) throw new Error('Server ETag required');
      return api.updateAgent(role, query.data.etag, { enabled });
    },
    onError: (error) => {
      setMutationError(error);
      if (
        error instanceof ApiError &&
        (error.problem.status === 412 || error.problem.status === 428)
      )
        void query.refetch();
    },
    onSuccess: () => {
      setMutationError(undefined);
      void client.invalidateQueries({ queryKey: workspaceQueryKey('agents') });
      void query.refetch();
    },
    onSettled: () => {
      updateInFlight.current = false;
    },
  });
  if (query.isLoading)
    return (
      <Panel title={role}>
        <State kind="loading" />
      </Panel>
    );
  if (query.error)
    return (
      <Panel title={role}>
        <Problem error={query.error} />
      </Panel>
    );
  const data = query.data?.body;
  if (!data) return null;
  const updateCapability = data.action_capabilities.find(
    (item) =>
      item.action === (data.enabled ? 'disable_agent' : 'enable_agent') ||
      item.action === 'update_agent_config',
  );
  return (
    <Panel title={role}>
      <Badge>{data.enabled ? 'ENABLED' : 'DISABLED'}</Badge>
      <p>
        {data.model_provider}/{data.model_name}
      </p>
      <dl className="definition">
        <dt>{t('agent.runtimeProfile')}</dt>
        <dd>{data.runtime_profile}</dd>
        <dt>{t('agent.toolTimeout')}</dt>
        <dd>{t('agent.seconds', { count: data.tool_timeout_seconds })}</dd>
        <dt>{t('agent.maxSteps')}</dt>
        <dd>{data.max_steps_override ?? t('agent.serverDefault')}</dd>
        <dt>{t('agent.maxToolCalls')}</dt>
        <dd>{data.max_tool_calls_override ?? t('agent.serverDefault')}</dd>
      </dl>
      <p>{t('agent.revision', { revision: data.revision })}</p>
      {updateCapability && (
        <Capability
          item={updateCapability}
          busy={update.isPending}
          label={data.enabled ? t('agent.disableFuture') : t('agent.enableFuture')}
          onClick={
            query.data?.etag
              ? () => {
                  if (updateInFlight.current) return;
                  updateInFlight.current = true;
                  update.mutate(!data.enabled);
                }
              : undefined
          }
        />
      )}
      {mutationError !== undefined && <Problem error={mutationError} />}
    </Panel>
  );
}
