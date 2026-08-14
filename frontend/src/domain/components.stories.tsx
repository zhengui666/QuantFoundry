import type { Meta, StoryObj } from '@storybook/react-vite';
import type { Schema } from '../api/client';
import { applyServerSettingsLocale } from '../i18n';
import { storybookDataCapabilities, sharedMswScenarios } from '../testing/msw-handlers';
import {
  AIInterpretationPanel,
  ApprovalCard,
  AuditEventRow,
  CalculatedBadge,
  DataCapabilityMatrix,
  DeviationRow,
  EvidenceBadge,
  EvidenceItem,
  HoldoutGate,
  JobProgress,
  PaperBadge,
  ProvenancePopover,
  StatusBadge,
  ValidationMatrix,
  ValidationTestRow,
  VersionBadge,
  VersionSwitcher,
  type DomainViewState,
} from './components';

const capability = (action: string, allowed = true): Schema<'ActionCapability'> => ({
  action,
  visibility: 'SHOW',
  allowed,
  reason_code: allowed ? null : 'HOLDOUT_APPROVAL_REQUIRED',
  reason_detail: allowed ? null : 'Owner approval is required.',
  requires_confirmation: false,
  idempotency_required: true,
  if_match_required: true,
  result_mode: 'IMMEDIATE',
  danger_level: 'STATE_CHANGE',
});

const provenance = {
  provenance_id: 'PROV-4K66CSQZMSY08WK2ZGS0A05V8B',
} satisfies Schema<'ProvenanceRef'>;

const evidence = {
  evidence: {
    type: 'evidence',
    id: 'EVID-01J77KCWBMWESD3FBAY4R8GGQT',
    version: null,
    revision: 1,
  },
  stance: 'SUPPORTING',
  claim: 'Quality remains positive after measured costs.',
  source_experiment: {
    type: 'experiment',
    id: 'EXP-6NRYG2G3MDMMT74S8B4SMZTRCV',
    version: null,
    revision: 1,
  },
  result_locator: { result_sha256: 'd'.repeat(64), metric_key: 'sharpe', artifact: null },
  strength: 'MODERATE',
  limitations: 'The observation covers one market regime.',
  is_invalidated: false,
  provenance,
  created_at: '2026-08-10T00:30:00Z',
} satisfies Schema<'ResearchEvidenceItem'>;

const validationTest = {
  test_key: 'parameter_stability',
  attempt_no: 1,
  test_version: '1.0.0',
  state: 'FAIL',
  purpose: 'Measure stability around the selected parameter.',
  configuration_summary: 'Adjacent parameter grid.',
  calculated_result: 'Minimum threshold missed.',
  interpretation: 'The stable region is too narrow.',
  failure_code: 'VALIDATION_FAILED',
  failure_detail: 'Mandatory stability test failed.',
  warning_codes: [],
  artifact_ids: [],
  provenance,
  override_permitted: false,
} satisfies Schema<'ValidationTestResult'>;

const holdoutGate = {
  validation_id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
  state: 'LOCKED',
  exposure_count: 0,
  period: { start: '2019-01-01', end: '2024-12-31' },
  approval: null,
  action_capabilities: [capability('run_holdout', false)],
  revision: 3,
} satisfies Schema<'HoldoutGate'>;

const approval = {
  approval_id: 'APR-0T71YPB60APYFY39FY75RYTVZB',
  type: 'HOLDOUT_UNLOCK',
  subject: {
    type: 'VALIDATION',
    id: 'VAL-2GKYQRFB6BG5R4AVJSYCAJH56J',
    version: 4,
    revision: 3,
    sha256: 'b'.repeat(64),
  },
  requester: { type: 'OWNER', id: 'owner' },
  reason: 'Expose the final holdout exactly once.',
  prerequisites: [{ key: 'strict_validation', state: 'PASS', detail: 'Passed.' }],
  risk_summary: { risk_level: 'HIGH', warning_codes: [] },
  effects: [{ code: 'EXPOSE_HOLDOUT', detail: 'Exposure count increments.' }],
  status: 'PENDING',
  requested_at: '2026-08-10T00:00:00Z',
  decided_at: null,
  revision: 3,
  action_capabilities: [capability('approve'), capability('reject')],
} satisfies Schema<'ApprovalDetail'>;

const auditEvent = {
  event_id: 'AUD-3S55HPAVN1YRA6GMVCA87MMXG8',
  action: 'research.started',
  actor: { type: 'OWNER', id: 'owner' },
  object: {
    type: 'research',
    id: 'RSCH-10QAK5KS1BPEVRRDDZR68QTGCV',
    version: null,
    revision: 2,
  },
  request_id: 'request-storybook-audit',
  provenance,
  occurred_at: '2026-08-10T01:00:00Z',
} satisfies Schema<'ResearchAuditItem'>;

export function DomainComponentGallery({ state = 'default' }: { state?: DomainViewState }) {
  const longText =
    state === 'long'
      ? 'This intentionally long interpretation preserves evidence limitations, assumptions, and provenance without clipping or hiding decision-critical server truth. '.repeat(
          3,
        )
      : 'The result is consistent with the calculated evidence.';
  return (
    <main className={state === 'narrow' ? 'domain-story-narrow' : 'domain-story'}>
      <h1>QuantFoundry domain components</h1>
      <div className="domain-story-grid">
        <StatusBadge status="RUNNING" viewState={state} />
        <EvidenceBadge stance="SUPPORTING" strength="MODERATE" viewState={state} />
        <EvidenceItem
          item={{ ...evidence, claim: state === 'long' ? longText : evidence.claim }}
          viewState={state}
        />
        <AIInterpretationPanel
          interpretation={longText}
          provenance={provenance}
          viewState={state}
        />
        <CalculatedBadge viewState={state} />
        <ProvenancePopover value={provenance} viewState={state} />
        <VersionBadge version={4} frozen viewState={state} />
        <VersionSwitcher versions={[2, 3, 4]} value={4} viewState={state} />
        <JobProgress
          status="RUNNING"
          progress={{
            mode: 'UNITS',
            completed_units: 4,
            total_units: 10,
            unit: 'experiments',
            percent: 40,
            current_step_key: 'validate',
            current_step_label: 'Running mandatory validation',
          }}
          viewState={state}
        />
        <ValidationMatrix tests={[validationTest]} viewState={state} />
        <ValidationTestRow test={validationTest} viewState={state} />
        <HoldoutGate gate={holdoutGate} viewState={state} />
        <ApprovalCard
          approval={{ ...approval, reason: state === 'long' ? longText : approval.reason }}
          viewState={state}
        />
        <DataCapabilityMatrix capabilities={storybookDataCapabilities} viewState={state} />
        <PaperBadge status="APPROVAL_PENDING" viewState={state} />
        <DeviationRow
          label="Net return"
          expected="8.0%"
          actual="5.2%"
          severity="WARN"
          viewState={state}
        />
        <AuditEventRow event={auditEvent} viewState={state} />
      </div>
    </main>
  );
}

const meta = {
  title: 'Design System/Domain components',
  component: DomainComponentGallery,
  parameters: { msw: { handlers: sharedMswScenarios.happy } },
  args: { state: 'default' },
} satisfies Meta<typeof DomainComponentGallery>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const LongContent: Story = { args: { state: 'long' } };
export const Loading: Story = {
  args: { state: 'loading' },
  parameters: { msw: { handlers: sharedMswScenarios.loading } },
};
export const Empty: Story = {
  args: { state: 'empty' },
  parameters: { msw: { handlers: sharedMswScenarios.empty } },
};
export const Error: Story = { args: { state: 'error' } };
export const Locked: Story = {
  args: { state: 'locked' },
  parameters: { msw: { handlers: sharedMswScenarios.permission } },
};
export const DisabledReason: Story = { args: { state: 'disabled' } };
export const KeyboardFocus: Story = { args: { state: 'focus' } };
export const Narrow: Story = {
  args: { state: 'narrow' },
  globals: { viewport: { value: 'desktop1180', isRotated: false } },
};
export const EnglishNewYork: Story = {
  loaders: [
    async () => applyServerSettingsLocale({ language: 'en', timezone: 'America/New_York' }),
  ],
};
export const ChineseShanghai: Story = {
  loaders: [
    async () => applyServerSettingsLocale({ language: 'zh-CN', timezone: 'Asia/Shanghai' }),
  ],
};
