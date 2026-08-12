import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api, workspaceQueryKey } from '../../api/client';
import { DataCapabilityMatrix } from '../../design-system/domain-components';
import { Panel, Problem, State } from '../../ui';

export function DataCapabilitiesPage() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: workspaceQueryKey('data-capabilities'),
    queryFn: ({ signal }) => api.dataCapabilities(signal),
  });

  return (
    <>
      <h1>{t('page.data')}</h1>
      <Panel title={t('data.verified')}>
        {query.isLoading && <State kind="loading">{t('data.loading')}</State>}
        {query.error && <Problem error={query.error} />}
        {query.data?.body.length === 0 && <State kind="empty">{t('data.empty')}</State>}
        {query.data && query.data.body.length > 0 && (
          <DataCapabilityMatrix capabilities={query.data.body} />
        )}
      </Panel>
    </>
  );
}
