import { useState, type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';
import { ApiError, ContractError, type CanonicalErrorCode, type Schema } from './api/client';
import './i18n';

export function State({
  kind,
  children,
}: {
  kind: 'loading' | 'empty' | 'error' | 'permission';
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <section className={`state ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <strong>{t(`state.${kind}`)}</strong>
      <p>{children ?? t('state.default')}</p>
    </section>
  );
}
export function Badge({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <span className="badge">
      {typeof children === 'string'
        ? t(`status.${children}`, { defaultValue: children })
        : children}
    </span>
  );
}
export function Provenance({
  value,
  source = 'Calculated',
}: {
  value?: Schema<'ProvenanceRef'> | Schema<'Provenance'> | null;
  source?: 'AI' | 'Calculated' | 'Policy';
}) {
  const { t } = useTranslation();
  const sourceLabel = t(`provenance.source.${source}`);
  const experimentId = value && 'experiment_id' in value ? value.experiment_id : null;
  const toolCallId = value && 'tool_call_id' in value ? value.tool_call_id : null;
  const href = value
    ? experimentId
      ? `/experiments/${encodeURIComponent(experimentId)}?tab=summary&focus=provenance${toolCallId ? `&toolCallId=${encodeURIComponent(toolCallId)}` : ''}`
      : `/activity?provenanceId=${encodeURIComponent(value.provenance_id)}`
    : undefined;
  return (
    <span
      className="provenance"
      title={
        value
          ? t('provenance.identity', { id: value.provenance_id })
          : t('provenance.content', { source: sourceLabel })
      }
    >
      <Badge>{sourceLabel}</Badge>
      {href && <a href={href}>{t('domainComponent.provenance')}</a>}
    </span>
  );
}
export function Capability({
  item,
  onClick,
  busy = false,
  label,
  confirmationHandled = false,
}: {
  item: Schema<'ActionCapability'>;
  onClick?: (() => void | Promise<void>) | undefined;
  busy?: boolean;
  label?: string;
  confirmationHandled?: boolean;
}) {
  const { t } = useTranslation();
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [confirmationPending, setConfirmationPending] = useState(false);
  const [confirmationError, setConfirmationError] = useState<string>();
  if (item.visibility === 'HIDE') return null;
  const executable = item.allowed && onClick !== undefined;
  const actionLabel = label ?? t(`action.${item.action}`, { defaultValue: item.action });
  const run = async () => {
    setConfirmationError(undefined);
    try {
      await onClick?.();
    } catch (error) {
      setConfirmationError(error instanceof Error ? error.message : t('error.connection'));
    }
  };
  const runSafely = () => {
    void run();
  };
  const button = (
    <button
      type="button"
      data-testid={`capability-action-${item.action}`}
      data-requires-confirmation={String(item.requires_confirmation)}
      onClick={item.requires_confirmation && !confirmationHandled ? undefined : runSafely}
      disabled={!executable || busy}
      title={
        item.allowed
          ? onClick
            ? undefined
            : t('capability.noHandler')
          : (item.reason_detail ?? item.reason_code ?? t('capability.unavailable'))
      }
    >
      {busy ? t('common.saving') : actionLabel}
      {!item.allowed && ` · ${t('capability.unavailable')}`}
    </button>
  );
  if (!executable || !item.requires_confirmation || confirmationHandled)
    return (
      <>
        {button}
        {confirmationError && <State kind="error">{confirmationError}</State>}
      </>
    );
  const confirm = async () => {
    if (!onClick) return;
    setConfirmationPending(true);
    setConfirmationError(undefined);
    try {
      await onClick();
      setConfirmationOpen(false);
    } catch (error) {
      setConfirmationError(error instanceof Error ? error.message : t('error.connection'));
    } finally {
      setConfirmationPending(false);
    }
  };
  return (
    <Dialog.Root open={confirmationOpen} onOpenChange={setConfirmationOpen}>
      <Dialog.Trigger asChild>{button}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="decision-dialog" aria-describedby={undefined}>
          <Dialog.Title>{t('capability.confirm', { action: actionLabel })}</Dialog.Title>
          <p>
            {item.danger_level} · {item.result_mode}
            {item.if_match_required ? ` · ${t('capability.revisionProtected')}` : ''}
            {item.idempotency_required ? ` · ${t('capability.idempotentRequest')}` : ''}
          </p>
          {confirmationError && <State kind="error">{confirmationError}</State>}
          <button
            type="button"
            data-testid={`capability-confirm-${item.action}`}
            onClick={() => void confirm()}
            disabled={confirmationPending || busy}
          >
            {t('capability.confirmAction')}
          </button>
          <Dialog.Close asChild>
            <button type="button" className="secondary">
              {t('common.cancel')}
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function CapabilityFieldset({
  item,
  legend,
  busy = false,
  children,
}: {
  item: Schema<'ActionCapability'> | undefined;
  legend: string;
  busy?: boolean;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  if (!item || item.visibility === 'HIDE') return null;
  const reasonId = `capability-input-reason-${item.action}`;
  return (
    <fieldset
      data-testid={`capability-inputs-${item.action}`}
      disabled={!item.allowed || busy}
      aria-describedby={!item.allowed ? reasonId : undefined}
    >
      <legend>{legend}</legend>
      {children}
      {!item.allowed && (
        <p id={reasonId} role="status">
          {item.reason_detail ?? item.reason_code ?? t('capability.unavailableReason')}
        </p>
      )}
    </fieldset>
  );
}

export function mergeActionCapabilities(
  base: readonly Schema<'ActionCapability'>[],
  authoritativeOverrides: readonly Schema<'ActionCapability'>[],
): Schema<'ActionCapability'>[] {
  const byAction = new Map(base.map((capability) => [capability.action, capability]));
  for (const capability of authoritativeOverrides) byAction.set(capability.action, capability);
  return [...byAction.values()];
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function Inspector({
  title,
  trigger,
  children,
}: {
  title: string;
  trigger: ReactNode;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="inspector" aria-describedby={undefined}>
          <Dialog.Title>{title}</Dialog.Title>
          {children}
          <Dialog.Close asChild>
            <button type="button" className="secondary">
              {t('common.close')}
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export const errorCopy: Record<CanonicalErrorCode, string> = {
  INVALID_REQUEST: 'Check the submitted fields.',
  RESOURCE_NOT_FOUND: 'The requested record no longer exists.',
  PRECONDITION_REQUIRED: 'Refresh and confirm the latest server state.',
  REVISION_MISMATCH: 'This record changed; refresh before acting again.',
  IDEMPOTENCY_CONFLICT: 'This request key conflicts with an earlier submission.',
  IDEMPOTENCY_IN_PROGRESS: 'The prior request is still being processed.',
  RESOURCE_CONFLICT: 'The server rejected this conflicting state.',
  SERVICE_DEGRADED: 'A required service is degraded.',
  INTERNAL_ERROR: 'The service could not complete this request.',
  UNAUTHENTICATED: 'Sign in with a current general access key.',
  PERMISSION_DENIED: 'Your role cannot perform this action.',
  HUMAN_APPROVAL_REQUIRED: 'A human approval is required.',
  RESEARCH_NOT_MUTABLE: 'This research record is no longer mutable.',
  RESEARCH_WAITING_USER: 'The workflow is waiting for a human decision.',
  EXPERIMENT_IMMUTABLE: 'Experiments are immutable after creation.',
  EXPERIMENT_INVALID: 'The experiment is invalid.',
  NON_REPRODUCIBLE: 'The result cannot be reproduced.',
  MULTIPLE_TESTING_LIMIT_REACHED: 'The multiple-testing limit was reached.',
  STRATEGY_VERSION_FROZEN: 'This strategy version is frozen.',
  STRATEGY_VERSION_MISMATCH: 'The strategy version changed.',
  STRATEGY_NOT_FROZEN: 'Freeze the strategy first.',
  STRATEGY_NOT_VALIDATED: 'Validation is required first.',
  VALIDATION_IN_PROGRESS: 'Validation is already in progress.',
  VALIDATION_FAILED: 'Validation failed.',
  VALIDATION_PREREQUISITES_INCOMPLETE: 'Validation prerequisites are incomplete.',
  VALIDATION_TEST_BLOCKED: 'A validation test is blocked.',
  HOLDOUT_LOCKED: 'Holdout is locked.',
  HOLDOUT_APPROVAL_REQUIRED: 'Holdout requires explicit approval.',
  HOLDOUT_PREREQUISITES_INCOMPLETE: 'Holdout prerequisites are incomplete.',
  HOLDOUT_ALREADY_EXPOSED: 'Holdout has already been exposed.',
  HOLDOUT_RESULT_FORBIDDEN: 'Holdout results are not authorized.',
  APPROVAL_STALE: 'The approval is stale; review the latest state.',
  APPROVAL_ALREADY_RESOLVED: 'This approval is already resolved.',
  APPROVAL_PREREQUISITES_CHANGED: 'Approval prerequisites changed.',
  APPROVAL_TYPE_MISMATCH: 'The approval type does not match this action.',
  DATA_CAPABILITY_MISSING: 'A required data capability is missing.',
  DATA_QUALITY_BLOCKED: 'Data quality blocks this action.',
  DATA_SNAPSHOT_MISSING: 'An immutable data snapshot is required.',
  PIT_GUARANTEE_UNAVAILABLE: 'Point-in-time guarantees are unavailable.',
  STALE_DATA: 'The data is stale.',
  PROVIDER_UNAVAILABLE: 'The provider is unavailable.',
  JOB_CONFLICT: 'A conflicting job is active.',
  JOB_NOT_CANCELLABLE: 'This job cannot be cancelled.',
  JOB_LEASE_LOST: 'The job lease was lost.',
  JOB_FAILED: 'The job failed.',
  PAPER_APPROVAL_REQUIRED: 'Paper approval is required.',
  PAPER_RISK_BLOCKED: 'Risk policy blocks paper execution.',
  PAPER_DATA_BLOCKED: 'Data policy blocks paper execution.',
  PAPER_DUPLICATE_RUN: 'A duplicate paper run is blocked.',
  PAPER_VERSION_MISMATCH: 'The paper version changed.',
  RISK_LIMIT_EXCEEDED: 'A risk limit was exceeded.',
  AGENT_DISABLED: 'This agent is disabled for future admission.',
  AGENT_TOOL_FORBIDDEN: 'This agent is not permitted to use that tool.',
  AGENT_BUDGET_EXCEEDED: 'The agent budget was exceeded.',
  AGENT_OUTPUT_INVALID: 'The agent output failed validation.',
  AGENT_MODEL_UNAVAILABLE: 'The agent model is unavailable.',
  AGENT_RESUME_CONFLICT: 'The agent cannot resume from this checkpoint.',
  AGENT_CONTEXT_STALE: 'The agent context is stale.',
  AGENT_RETRY_EXHAUSTED: 'The agent retry budget is exhausted.',
  TOOL_INPUT_INVALID: 'Tool input is invalid.',
  TOOL_EXECUTION_FAILED: 'Tool execution failed.',
  CREDENTIAL_INVALID: 'Credentials are invalid.',
  CREDENTIAL_NOT_CONFIGURED: 'Credentials are not configured.',
  CONNECTION_VALIDATION_EXPIRED: 'The validated connection expired; test it again.',
  CONNECTION_KIND_MISMATCH: 'The validated connection is the wrong provider kind.',
  LAST_ACTIVE_KEY_REQUIRED: 'Keep one active general access key before revoking this key.',
  CONFIGURATION_VALIDATION_FAILED: 'The configuration candidate failed validation.',
  CONFIGURATION_APPLY_FAILED: 'The configuration could not be applied.',
  CONFIGURATION_RESTART_REQUIRED: 'Restart is required before this configuration is active.',
  DATABASE_CONNECTION_FAILED: 'The domain database connection failed.',
  DATABASE_SCHEMA_INCOMPATIBLE: 'The domain database schema is incompatible.',
  DATABASE_SWITCH_FAILED: 'The domain database switch failed and was reverted.',
  BOOTSTRAP_LOCKED: 'Bootstrap control is locked until a valid key is configured.',
  DATABASE_DISCONNECTED: 'The domain database is disconnected.',
  CSRF_REQUIRED: 'Refresh the session before retrying this action.',
};

export function localizedErrorCopy(
  code: CanonicalErrorCode,
  t: TFunction,
  language: string,
): string {
  const key = `error.${code}`;
  const translated = t(key, { defaultValue: '' });
  if (translated) return translated;
  return language.startsWith('zh') ? t('error.fallback', { code }) : errorCopy[code];
}

export function Problem({ error }: { error: unknown }) {
  const { i18n, t } = useTranslation();
  if (error instanceof ContractError) return <State kind="error">{t('error.contract')}</State>;
  if (!(error instanceof ApiError)) return <State kind="error">{t('error.connection')}</State>;
  const problem = error.problem;
  return (
    <State kind={problem.status === 403 ? 'permission' : 'error'}>
      {localizedErrorCopy(problem.code, t, i18n.language)} {problem.detail}{' '}
      <a href={`/activity?requestId=${encodeURIComponent(problem.request_id)}`}>
        {t('error.auditRequest', { requestId: problem.request_id })}
      </a>
      {problem.field_errors.length > 0 && (
        <ul>
          {problem.field_errors.map((field) => (
            <li key={`${field.field}:${field.code}`}>
              {field.field}: {field.message}
            </li>
          ))}
        </ul>
      )}
    </State>
  );
}
