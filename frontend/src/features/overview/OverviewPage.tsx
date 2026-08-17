import { useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { api, workspaceQueryKey } from '../../api/client';
import CanonicalChart from '../../CanonicalChart';
import { formatCanonicalDecimal, formatCanonicalPercent, ServerTime } from '../../format';
import { Badge, Capability, localizedErrorCopy, Panel, Problem, Provenance, State } from '../../ui';

export function OverviewPage() {
  const { i18n, t } = useTranslation();
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: workspaceQueryKey('overview'),
    queryFn: ({ signal }) => api.overview(signal),
  });
  if (query.isLoading) return <State kind="loading">{t('overview.loading')}</State>;
  if (query.error) return <Problem error={query.error} />;
  const data = query.data?.body;
  if (!data) return <State kind="empty" />;
  const locale = i18n.resolvedLanguage === 'en' ? 'en' : 'zh-CN';
  const money = (value: string | null) =>
    value === null
      ? '—'
      : `${formatCanonicalDecimal(value, locale) ?? '—'} ${data.paper_summary.currency}`;
  const percent = (value: string | null) =>
    value === null ? '—' : `${formatCanonicalPercent(value, locale) ?? '—'}%`;
  return (
    <>
      <h1>{t('page.overview')}</h1>
      <div className="grid metrics">
        <Panel title={t('overview.needsAttention')}>
          <strong>{data.needs_attention.length}</strong>
        </Panel>
        <Panel title={t('overview.activeResearch')}>
          <strong>{data.active_research.length}</strong>
        </Panel>
        {Object.entries(data.strategy_pipeline).map(([state, count]) => (
          <Panel key={state} title={state}>
            <strong>{count}</strong>
          </Panel>
        ))}
        <Panel title={t('overview.dataHealth')}>
          <Badge>{data.data_health.state}</Badge>
        </Panel>
      </div>
      {data.paper_performance_chart && (
        <Panel title={t('overview.paperPerformance')}>
          <CanonicalChart chart={data.paper_performance_chart} />
        </Panel>
      )}
      <Panel title={t('overview.paperSummary')}>
        <dl className="definition">
          <dt>{t('overview.activePortfolios')}</dt>
          <dd>{data.paper_summary.active_count}</dd>
          <dt>{t('overview.totalNav')}</dt>
          <dd>{money(data.paper_summary.total_nav)}</dd>
          <dt>{t('overview.dailyMtd')}</dt>
          <dd>
            {percent(data.paper_summary.daily_return)} / {percent(data.paper_summary.mtd_return)}
          </dd>
          <dt>{t('overview.sinceBenchmark')}</dt>
          <dd>
            {percent(data.paper_summary.since_start_return)} /{' '}
            {percent(data.paper_summary.benchmark_since_start_return)}
          </dd>
          <dt>{t('overview.asOf')}</dt>
          <dd>{data.paper_summary.as_of_date ?? '—'}</dd>
        </dl>
        <Provenance value={data.paper_summary.provenance} />
      </Panel>
      <Panel title={t('overview.needsAttention')}>
        {data.needs_attention.map((item) => (
          <article key={item.attention_id} className="row-card">
            <Badge>{item.severity}</Badge>
            <strong>{item.summary}</strong>
            {item.reason_code && (
              <span>{localizedErrorCopy(item.reason_code, t, i18n.language)}</span>
            )}
            <div>
              {item.action_capabilities.map((capability) => (
                <Capability
                  key={capability.action}
                  item={capability}
                  onClick={
                    ['open', 'view', 'review', 'review_approval'].includes(capability.action) &&
                    ['approval', 'research', 'strategy'].includes(item.object.type)
                      ? () => {
                          const object = item.object;
                          if (object.type === 'approval')
                            void navigate({
                              to: '/approvals/$approvalId',
                              params: { approvalId: object.id },
                            });
                          else if (object.type === 'research')
                            void navigate({
                              to: '/research/$researchId',
                              params: { researchId: object.id },
                            });
                          else if (object.type === 'strategy')
                            void navigate({
                              to: '/strategies/$strategyId',
                              params: { strategyId: object.id },
                              search: { version: object.version ?? undefined },
                            });
                        }
                      : undefined
                  }
                />
              ))}
            </div>
          </article>
        ))}
      </Panel>
      <Panel title={t('overview.activeResearch')}>
        {data.active_research.map((item) => (
          <article className="row-card" key={item.research_id}>
            <Badge>{item.status}</Badge>
            <strong>{item.title}</strong>
            <span>
              {item.progress.mode === 'UNITS'
                ? `${item.progress.completed_units ?? 0}/${item.progress.total_units ?? '—'} ${item.progress.unit ?? t('overview.units')}`
                : (item.progress.current_step_label ?? t('overview.awaitingProgress'))}
            </span>
            <span>{item.current_agent?.role ?? t('overview.noActiveAgent')}</span>
            <div>
              {item.action_capabilities.map((capability) => (
                <Capability
                  key={capability.action}
                  item={capability}
                  onClick={
                    capability.action === 'open_research'
                      ? () =>
                          void navigate({
                            to: '/research/$researchId',
                            params: { researchId: item.research_id },
                          })
                      : undefined
                  }
                />
              ))}
            </div>
          </article>
        ))}
      </Panel>
      <div className="grid">
        <Panel title={t('overview.recentFindings')}>
          {data.recent_findings.map((finding) => (
            <article key={finding.finding_id} className="stack-card">
              <Badge>{finding.evidence_status}</Badge>
              <p>{finding.finding}</p>
              <small>
                <ServerTime value={finding.updated_at} />
              </small>
              <Provenance value={finding.provenance} />
            </article>
          ))}
        </Panel>
        <Panel title={t('overview.agentActivity')}>
          {data.agent_activity.map((activity) => (
            <article key={activity.agent_run_id} className="stack-card">
              <Badge>{activity.status}</Badge>
              <strong>{activity.role}</strong>
              <p>{activity.objective}</p>
              <p>{activity.decision_summary ?? activity.next_action ?? t('overview.noDecision')}</p>
            </article>
          ))}
        </Panel>
      </div>
      <Panel title={t('overview.dataHealthActions')}>
        <Badge>{data.data_health.state}</Badge>
        <p>
          {t('overview.healthCounts', {
            blockers: data.data_health.blocker_count,
            warnings: data.data_health.warning_count,
          })}{' '}
          <ServerTime value={data.data_health.checked_at} />
        </p>
        {data.data_health.action_capabilities.map((capability) => (
          <Capability
            key={capability.action}
            item={capability}
            onClick={
              capability.action === 'inspect_data_health'
                ? () => void navigate({ to: '/data' })
                : undefined
            }
          />
        ))}
        {data.action_capabilities.map((capability) => (
          <Capability
            key={capability.action}
            item={capability}
            onClick={
              capability.action === 'refresh_overview'
                ? () => void query.refetch()
                : capability.action === 'create_research'
                  ? () => void navigate({ to: '/research' })
                  : capability.action === 'review_approvals'
                    ? () => void navigate({ to: '/approvals' })
                    : undefined
            }
          />
        ))}
      </Panel>
      <Panel title={t('overview.provenanceIndex')}>
        {data.provenance.map((provenance) => (
          <Provenance key={provenance.provenance_id} value={provenance} />
        ))}
      </Panel>
      <p className="as-of">
        {t('overview.serverRevision', { revision: data.revision })} · {t('overview.asOf')}{' '}
        <ServerTime value={data.as_of} />
      </p>
    </>
  );
}
