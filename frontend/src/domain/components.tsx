import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import type { Schema } from '../api/client';
import { ServerTime } from '../format';
import { Badge, Capability, Panel, Provenance, State } from '../ui';

export type DomainViewState =
  'default' | 'long' | 'loading' | 'empty' | 'error' | 'locked' | 'disabled' | 'focus' | 'narrow';

function DomainBoundary({
  state = 'default',
  name,
  children,
}: {
  state?: DomainViewState | undefined;
  name: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  if (state === 'loading') return <State kind="loading">{t('domain.loading', { name })}</State>;
  if (state === 'empty') return <State kind="empty">{t('domain.empty', { name })}</State>;
  if (state === 'error') return <State kind="error">{t('domain.error', { name })}</State>;
  if (state === 'locked') return <State kind="permission">{t('domain.locked', { name })}</State>;
  if (state === 'disabled')
    return (
      <fieldset className="domain-boundary" disabled aria-describedby={`${name}-disabled-reason`}>
        {children}
        <p id={`${name}-disabled-reason`} role="status">
          {t('domain.disabled')}
        </p>
      </fieldset>
    );
  return (
    <div
      className={`domain-boundary domain-${state}`}
      tabIndex={state === 'focus' ? 0 : undefined}
      data-domain-state={state}
    >
      {children}
    </div>
  );
}

type Stateful = { viewState?: DomainViewState | undefined };

export function StatusBadge({ status, viewState }: { status: string } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="status-badge">
      <Badge>{t(`status.${status}`, { defaultValue: status })}</Badge>
    </DomainBoundary>
  );
}

export function EvidenceBadge({
  stance,
  strength,
  viewState,
}: {
  stance: Schema<'ResearchEvidenceItem'>['stance'];
  strength: Schema<'ResearchEvidenceItem'>['strength'];
} & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="evidence-badge">
      <Badge>
        {t(`evidence.stance.${stance}`)} · {t(`evidence.strength.${strength}`)}
      </Badge>
    </DomainBoundary>
  );
}

export function EvidenceItem({
  item,
  viewState,
}: { item: Schema<'ResearchEvidenceItem'> } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="evidence-item">
      <article className="domain-card">
        <EvidenceBadge stance={item.stance} strength={item.strength} />
        <h3>{item.claim}</h3>
        {item.limitations && (
          <p>
            <strong>{t('evidence.limitations')}</strong> {item.limitations}
          </p>
        )}
        <ServerTime value={item.created_at} />
        <Provenance value={item.provenance} />
      </article>
    </DomainBoundary>
  );
}

export function AIInterpretationPanel({
  interpretation,
  provenance,
  viewState,
}: {
  interpretation: string;
  provenance: Schema<'ProvenanceRef'> | null;
} & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="ai-interpretation">
      <Panel title={t('domainComponent.aiInterpretation')}>
        <p>{interpretation}</p>
        <Provenance source="AI" value={provenance} />
      </Panel>
    </DomainBoundary>
  );
}

export function CalculatedBadge({ viewState }: Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="calculated-badge">
      <Badge>{t('domainComponent.calculated')}</Badge>
    </DomainBoundary>
  );
}

export function ProvenancePopover({
  value,
  viewState,
}: { value: Schema<'ProvenanceRef'> } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="provenance-popover">
      <details>
        <summary>{t('domainComponent.provenance')}</summary>
        <dl className="definition">
          <dt>{t('domainComponent.provenanceId')}</dt>
          <dd>{value.provenance_id}</dd>
        </dl>
      </details>
    </DomainBoundary>
  );
}

export function VersionBadge({
  version,
  frozen,
  viewState,
}: { version: number; frozen: boolean } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="version-badge">
      <Badge>
        {t('domainComponent.version', { version })} ·{' '}
        {t(frozen ? 'status.FROZEN' : 'status.CANDIDATE')}
      </Badge>
    </DomainBoundary>
  );
}

export function VersionSwitcher({
  versions,
  value,
  onChange,
  viewState,
}: {
  versions: readonly number[];
  value: number;
  onChange?: (version: number) => void;
} & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="version-switcher">
      <label>
        {t('domainComponent.versionSwitcher')}
        <select value={value} onChange={(event) => onChange?.(Number(event.target.value))}>
          {versions.map((version) => (
            <option key={version} value={version}>
              {t('domainComponent.version', { version })}
            </option>
          ))}
        </select>
      </label>
    </DomainBoundary>
  );
}

export function JobProgress({
  progress,
  status,
  viewState,
}: {
  progress: Schema<'JobProgress'>;
  status: string;
} & Stateful) {
  const { t } = useTranslation();
  const value = progress.percent ?? 0;
  return (
    <DomainBoundary state={viewState} name="job-progress">
      <div className="domain-card">
        <StatusBadge status={status} />
        <label htmlFor="job-progress-value">{progress.current_step_label ?? t('domain.job')}</label>
        <progress id="job-progress-value" max={100} value={value}>
          {value}%
        </progress>
        <output>
          {progress.mode === 'UNITS'
            ? `${progress.completed_units ?? 0}/${progress.total_units ?? 0} ${progress.unit ?? ''}`
            : `${value}%`}
        </output>
      </div>
    </DomainBoundary>
  );
}

export function ValidationTestRow({
  test,
  viewState,
}: { test: Schema<'ValidationTestResult'> } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="validation-test-row">
      <article className={test.state === 'FAIL' ? 'domain-row failed-row' : 'domain-row'}>
        <StatusBadge status={test.state} />
        <div>
          <strong>{test.test_key}</strong>
          <p>{test.purpose}</p>
          {test.calculated_result && (
            <p>
              <Badge>{t('domainComponent.calculated')}</Badge> {test.calculated_result}
            </p>
          )}
          {test.interpretation && <p>{test.interpretation}</p>}
          {test.failure_detail && <p role="alert">{test.failure_detail}</p>}
          <small>{t('domainComponent.noOverride')}</small>
        </div>
      </article>
    </DomainBoundary>
  );
}

export function ValidationMatrix({
  tests,
  viewState,
}: { tests: readonly Schema<'ValidationTestResult'>[] } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="validation-matrix">
      <section aria-label={t('domainComponent.validationMatrix')}>
        {tests.length === 0 ? (
          <State kind="empty">
            {t('domain.empty', { name: t('domainComponent.validationMatrix') })}
          </State>
        ) : (
          tests.map((test) => (
            <ValidationTestRow key={`${test.test_key}:${test.attempt_no}`} test={test} />
          ))
        )}
      </section>
    </DomainBoundary>
  );
}

export function HoldoutGate({ gate, viewState }: { gate: Schema<'HoldoutGate'> } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="holdout-gate">
      <Panel title={t('domainComponent.holdoutGate')}>
        <StatusBadge status={gate.state} />
        <p>{t('domainComponent.exposureCount', { count: gate.exposure_count })}</p>
        {gate.action_capabilities.map((capability) => (
          <Capability key={capability.action} item={capability} />
        ))}
      </Panel>
    </DomainBoundary>
  );
}

export function ApprovalCard({
  approval,
  viewState,
}: { approval: Schema<'ApprovalDetail'> } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="approval-card">
      <article className="domain-card">
        <header className="summary">
          <strong>{approval.approval_id}</strong>
          <StatusBadge status={approval.status} />
        </header>
        <p>{approval.reason}</p>
        <p>{t('domainComponent.prerequisiteCount', { count: approval.prerequisites.length })}</p>
        {approval.action_capabilities.map((capability) => (
          <Capability key={capability.action} item={capability} />
        ))}
      </article>
    </DomainBoundary>
  );
}

export function DataCapabilityMatrix({
  capabilities,
  viewState,
}: { capabilities: readonly Schema<'DataCapability'>[] } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="data-capability-matrix">
      <table>
        <caption>{t('domainComponent.dataCapabilityMatrix')}</caption>
        <thead>
          <tr>
            <th scope="col">{t('domainComponent.capability')}</th>
            <th scope="col">{t('domainComponent.provider')}</th>
            <th scope="col">{t('domainComponent.state')}</th>
            <th scope="col">{t('domainComponent.checkedAt')}</th>
          </tr>
        </thead>
        <tbody>
          {capabilities.map((capability) => (
            <tr key={capability.capability_id}>
              <td>{capability.capability_key}</td>
              <td>{capability.provider_id}</td>
              <td>
                <StatusBadge status={capability.state} />
              </td>
              <td>
                <ServerTime value={capability.checked_at} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </DomainBoundary>
  );
}

export function PaperBadge({ status, viewState }: { status: string } & Stateful) {
  return <StatusBadge status={status} viewState={viewState} />;
}

export function DeviationRow({
  label,
  expected,
  actual,
  severity,
  viewState,
}: {
  label: string;
  expected: string;
  actual: string;
  severity: 'INFO' | 'WARN' | 'FAIL';
} & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="deviation-row">
      <div className={severity === 'FAIL' ? 'domain-row failed-row' : 'domain-row'}>
        <StatusBadge status={severity} />
        <strong>{label}</strong>
        <span>{t('domainComponent.expected', { value: expected })}</span>
        <span>{t('domainComponent.actual', { value: actual })}</span>
      </div>
    </DomainBoundary>
  );
}

export function AuditEventRow({
  event,
  viewState,
}: { event: Schema<'ResearchAuditItem'> } & Stateful) {
  const { t } = useTranslation();
  return (
    <DomainBoundary state={viewState} name="audit-event-row">
      <article className="domain-row">
        <StatusBadge status={event.action} />
        <div>
          <strong>{event.actor.id}</strong>
          <p>{event.object.id}</p>
          <ServerTime value={event.occurred_at} />
          <a href={`/activity?requestId=${encodeURIComponent(event.request_id)}`}>
            {t('domainComponent.auditRequest', { requestId: event.request_id })}
          </a>
        </div>
      </article>
    </DomainBoundary>
  );
}
