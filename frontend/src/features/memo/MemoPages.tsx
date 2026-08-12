import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useParams } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { api, isPublicId, type Schema, workspaceQueryKey } from '../../api/client';
import { Badge, Problem, State } from '../../ui';

export function MemoLanding() {
  const { t } = useTranslation();
  const [job, setJob] = useState<Schema<'JobAccepted'>>();
  const mutation = useMutation({
    mutationFn: (body: Schema<'MemoGenerateRequest'>) => api.generateMemo(body),
    onSuccess: ({ body }) => setJob(body),
  });
  return (
    <>
      <h1>{t('page.memo')}</h1>
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          mutation.mutate({
            strategy_id: String(data.get('strategy_id')),
            strategy_version: Number(data.get('strategy_version')),
          });
        }}
      >
        <label>
          {t('memo.strategyId')}
          <input name="strategy_id" required />
        </label>
        <label>
          {t('memo.strategyVersion')}
          <input name="strategy_version" type="number" min="1" required />
        </label>
        <button disabled={mutation.isPending}>{t('memo.generate')}</button>
      </form>
      {mutation.error && <Problem error={mutation.error} />}
      {job && (
        <State kind="empty">
          {t('memo.accepted', { jobId: job.job_id, status: job.status })}
          {job.resource_ref?.type === 'memo' && (
            <Link to="/memos/$memoId" params={{ memoId: job.resource_ref.id }}>
              {t('memo.open', { id: job.resource_ref.id })}
            </Link>
          )}
        </State>
      )}
    </>
  );
}

export function MemoPage() {
  const { t } = useTranslation();
  const { memoId } = useParams({ strict: false }) as { memoId: string };
  const validMemoId = isPublicId('memo', memoId);
  const query = useQuery({
    queryKey: validMemoId ? workspaceQueryKey('memo', memoId) : workspaceQueryKey('invalid-route'),
    queryFn: ({ signal }) => api.memo(memoId, signal),
    enabled: validMemoId,
  });
  const exportMutation = useMutation({
    mutationFn: () => api.exportMemo(memoId),
    onSuccess: ({ body }) => {
      const url = URL.createObjectURL(new Blob([body], { type: 'text/markdown' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${memoId}.md`;
      anchor.click();
      URL.revokeObjectURL(url);
    },
  });
  if (!validMemoId) return <State kind="error">{t('route.invalidMemo')}</State>;
  if (query.isLoading) return <State kind="loading" />;
  if (query.error) return <Problem error={query.error} />;
  const data = query.data?.body;
  if (!data) return <State kind="empty" />;
  return (
    <article className="memo">
      <h1>{t('page.memo')}</h1>
      <Badge>{data.status}</Badge>
      <p>{t('memo.strategyIdentity', { id: data.strategy.id, version: data.strategy.version })}</p>
      {data.sections.map((section) => (
        <section key={section.section_key}>
          <h2>{section.title}</h2>
          <p>{section.content}</p>
          {section.evidence_links.map((link) => (
            <Link
              key={link.experiment_id}
              to="/experiments/$experimentId"
              params={{ experimentId: link.experiment_id }}
              search={{ tab: 'summary', focus: 'provenance' }}
            >
              {t('memo.experiment', { id: link.experiment_id })}
            </Link>
          ))}
        </section>
      ))}
      <section>
        <h2>{t('memo.provenance')}</h2>
        {data.provenance.map((provenance) => (
          <Link
            key={provenance.provenance_id}
            to="/activity"
            search={{ provenanceId: provenance.provenance_id }}
          >
            {provenance.provenance_id}
          </Link>
        ))}
      </section>
      <button
        onClick={() => exportMutation.mutate()}
        disabled={exportMutation.isPending || data.status !== 'FINAL'}
      >
        {t('memo.exportMarkdown')}
      </button>
      <button disabled title={t('memo.paperDisabledReason')}>
        {t('memo.requestPaperDisabled')}
      </button>
      <button disabled title={t('memo.askDisabledReason')}>
        {t('memo.askDisabled')}
      </button>
      <button disabled title={t('memo.pdfDisabledReason')}>
        {t('memo.pdfDisabled')}
      </button>
      {exportMutation.error && <Problem error={exportMutation.error} />}
    </article>
  );
}
