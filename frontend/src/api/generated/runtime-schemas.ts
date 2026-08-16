// Generated from canonical openapi-v1.yaml. Do not edit.
import { z } from 'zod';
export const ResearchPolicyIdSchema = z.union([
  z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(39)
    .max(39)
    .regex(new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const RiskPolicyIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const CostModelIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const CredentialIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^CRED-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^CRED-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const CapabilityIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const DatasetIdSchema = z.union([
  z.string().min(32).max(32).regex(new RegExp('^DSSET-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(42)
    .max(42)
    .regex(
      new RegExp('^DSSET-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const SnapshotIdSchema = z.union([
  z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(39)
    .max(39)
    .regex(new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const DataQualityRunIdSchema = z.union([
  z.string().min(29).max(29).regex(new RegExp('^DQ-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(39)
    .max(39)
    .regex(new RegExp('^DQ-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const DataQualityIssueIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^DQI-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^DQI-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const ResearchIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const EvidenceIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^EVID-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^EVID-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ConclusionIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ExperimentIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const FactorIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const StrategyIdSchema = z.union([
  z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(42)
    .max(42)
    .regex(
      new RegExp('^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ValidationIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const ExposureIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^HOLD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^HOLD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const RedTeamRunIdSchema = z.union([
  z.string().min(29).max(29).regex(new RegExp('^RT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(39)
    .max(39)
    .regex(new RegExp('^RT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const PortfolioIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^PORT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^PORT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const MemoIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ApprovalIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const PaperIdSchema = z.union([
  z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(42)
    .max(42)
    .regex(
      new RegExp('^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const PaperRunIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const PaperOrderIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^PORD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^PORD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const PaperFillIdSchema = z.union([
  z.string().min(32).max(32).regex(new RegExp('^PFILL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(42)
    .max(42)
    .regex(
      new RegExp('^PFILL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ReviewIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const AgentRunIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ToolCallIdSchema = z.union([
  z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(42)
    .max(42)
    .regex(
      new RegExp('^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const JobIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const DomainEventIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const AuditEventIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^AUD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^AUD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const ArtifactIdSchema = z.union([
  z.string().min(30).max(30).regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(40)
    .max(40)
    .regex(new RegExp('^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
]);
export const NotificationIdSchema = z.union([
  z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(42)
    .max(42)
    .regex(
      new RegExp('^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const ProvenanceIdSchema = z.union([
  z.string().min(31).max(31).regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
  z
    .string()
    .min(41)
    .max(41)
    .regex(
      new RegExp('^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    ),
]);
export const PublicIdSchemas = {
  research_policy: ResearchPolicyIdSchema,
  risk_policy: RiskPolicyIdSchema,
  cost_model: CostModelIdSchema,
  credential: CredentialIdSchema,
  capability: CapabilityIdSchema,
  dataset: DatasetIdSchema,
  snapshot: SnapshotIdSchema,
  data_quality_run: DataQualityRunIdSchema,
  data_quality_issue: DataQualityIssueIdSchema,
  research: ResearchIdSchema,
  evidence: EvidenceIdSchema,
  conclusion: ConclusionIdSchema,
  experiment: ExperimentIdSchema,
  factor: FactorIdSchema,
  strategy: StrategyIdSchema,
  validation: ValidationIdSchema,
  exposure: ExposureIdSchema,
  red_team_run: RedTeamRunIdSchema,
  portfolio: PortfolioIdSchema,
  memo: MemoIdSchema,
  approval: ApprovalIdSchema,
  paper: PaperIdSchema,
  paper_run: PaperRunIdSchema,
  paper_order: PaperOrderIdSchema,
  paper_fill: PaperFillIdSchema,
  review: ReviewIdSchema,
  agent_run: AgentRunIdSchema,
  tool_call: ToolCallIdSchema,
  job: JobIdSchema,
  domain_event: DomainEventIdSchema,
  audit_event: AuditEventIdSchema,
  artifact: ArtifactIdSchema,
  notification: NotificationIdSchema,
  provenance: ProvenanceIdSchema,
} as const;
export const PublicIdExamples = {
  research_policy: {
    ulid: 'RP-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'RP-550e8400-e29b-41d4-a716-446655440000',
  },
  risk_policy: {
    ulid: 'RISK-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'RISK-550e8400-e29b-41d4-a716-446655440000',
  },
  cost_model: {
    ulid: 'COST-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'COST-550e8400-e29b-41d4-a716-446655440000',
  },
  credential: {
    ulid: 'CRED-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'CRED-550e8400-e29b-41d4-a716-446655440000',
  },
  capability: {
    ulid: 'CAP-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'CAP-550e8400-e29b-41d4-a716-446655440000',
  },
  dataset: {
    ulid: 'DSSET-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'DSSET-550e8400-e29b-41d4-a716-446655440000',
  },
  snapshot: {
    ulid: 'DS-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'DS-550e8400-e29b-41d4-a716-446655440000',
  },
  data_quality_run: {
    ulid: 'DQ-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'DQ-550e8400-e29b-41d4-a716-446655440000',
  },
  data_quality_issue: {
    ulid: 'DQI-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'DQI-550e8400-e29b-41d4-a716-446655440000',
  },
  research: {
    ulid: 'RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'RSCH-550e8400-e29b-41d4-a716-446655440000',
  },
  evidence: {
    ulid: 'EVID-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'EVID-550e8400-e29b-41d4-a716-446655440000',
  },
  conclusion: {
    ulid: 'CONC-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'CONC-550e8400-e29b-41d4-a716-446655440000',
  },
  experiment: {
    ulid: 'EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'EXP-550e8400-e29b-41d4-a716-446655440000',
  },
  factor: {
    ulid: 'FAC-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'FAC-550e8400-e29b-41d4-a716-446655440000',
  },
  strategy: {
    ulid: 'STRAT-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'STRAT-550e8400-e29b-41d4-a716-446655440000',
  },
  validation: {
    ulid: 'VAL-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'VAL-550e8400-e29b-41d4-a716-446655440000',
  },
  exposure: {
    ulid: 'HOLD-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'HOLD-550e8400-e29b-41d4-a716-446655440000',
  },
  red_team_run: {
    ulid: 'RT-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'RT-550e8400-e29b-41d4-a716-446655440000',
  },
  portfolio: {
    ulid: 'PORT-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'PORT-550e8400-e29b-41d4-a716-446655440000',
  },
  memo: {
    ulid: 'MEMO-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'MEMO-550e8400-e29b-41d4-a716-446655440000',
  },
  approval: {
    ulid: 'APR-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'APR-550e8400-e29b-41d4-a716-446655440000',
  },
  paper: {
    ulid: 'PAPER-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'PAPER-550e8400-e29b-41d4-a716-446655440000',
  },
  paper_run: {
    ulid: 'PRUN-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'PRUN-550e8400-e29b-41d4-a716-446655440000',
  },
  paper_order: {
    ulid: 'PORD-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'PORD-550e8400-e29b-41d4-a716-446655440000',
  },
  paper_fill: {
    ulid: 'PFILL-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'PFILL-550e8400-e29b-41d4-a716-446655440000',
  },
  review: {
    ulid: 'REV-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'REV-550e8400-e29b-41d4-a716-446655440000',
  },
  agent_run: {
    ulid: 'ARUN-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'ARUN-550e8400-e29b-41d4-a716-446655440000',
  },
  tool_call: {
    ulid: 'TCALL-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'TCALL-550e8400-e29b-41d4-a716-446655440000',
  },
  job: { ulid: 'JOB-01ARZ3NDEKTSV4RRFFQ69G5FAV', uuid: 'JOB-550e8400-e29b-41d4-a716-446655440000' },
  domain_event: {
    ulid: 'EVT-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'EVT-550e8400-e29b-41d4-a716-446655440000',
  },
  audit_event: {
    ulid: 'AUD-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'AUD-550e8400-e29b-41d4-a716-446655440000',
  },
  artifact: {
    ulid: 'ART-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'ART-550e8400-e29b-41d4-a716-446655440000',
  },
  notification: {
    ulid: 'NOTIF-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'NOTIF-550e8400-e29b-41d4-a716-446655440000',
  },
  provenance: {
    ulid: 'PROV-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    uuid: 'PROV-550e8400-e29b-41d4-a716-446655440000',
  },
} as const;
export type PublicIdType = keyof typeof PublicIdSchemas;
export const AnyPublicSemanticIdSchema = z.union([
  ResearchPolicyIdSchema,
  RiskPolicyIdSchema,
  CostModelIdSchema,
  CredentialIdSchema,
  CapabilityIdSchema,
  DatasetIdSchema,
  SnapshotIdSchema,
  DataQualityRunIdSchema,
  DataQualityIssueIdSchema,
  ResearchIdSchema,
  EvidenceIdSchema,
  ConclusionIdSchema,
  ExperimentIdSchema,
  FactorIdSchema,
  StrategyIdSchema,
  ValidationIdSchema,
  ExposureIdSchema,
  RedTeamRunIdSchema,
  PortfolioIdSchema,
  MemoIdSchema,
  ApprovalIdSchema,
  PaperIdSchema,
  PaperRunIdSchema,
  PaperOrderIdSchema,
  PaperFillIdSchema,
  ReviewIdSchema,
  AgentRunIdSchema,
  ToolCallIdSchema,
  JobIdSchema,
  DomainEventIdSchema,
  AuditEventIdSchema,
  ArtifactIdSchema,
  NotificationIdSchema,
  ProvenanceIdSchema,
]);

export const EventTypeObjectTypeMap = {
  'job.updated': 'job',
  'research.created': 'research',
  'research.updated': 'research',
  'research.conclusion.created': 'conclusion',
  'experiment.created': 'experiment',
  'experiment.updated': 'experiment',
  'factor.updated': 'factor',
  'strategy.created': 'strategy_version',
  'strategy.updated': 'strategy_version',
  'validation.created': 'validation',
  'validation.updated': 'validation',
  'validation.holdout.updated': 'validation',
  'approval.created': 'approval',
  'approval.updated': 'approval',
  'paper.created': 'paper',
  'paper.updated': 'paper',
  'paper.run.updated': 'paper_run',
  'review.created': 'review',
  'review.updated': 'review',
  'data.provider.updated': 'provider_connection',
  'data.capability.updated': 'capability',
  'data.quality.updated': 'snapshot',
  'agent.run.updated': 'agent_run',
  'tool.call.updated': 'tool_call',
  'memo.created': 'memo',
  'memo.updated': 'memo',
  'setup.completed': 'settings',
  'configuration.updated': 'settings',
  'configuration.apply_failed': 'settings',
  'database.connection.updated': 'provider_connection',
  'database.connection.failed': 'provider_connection',
  'notification.created': 'notification',
  'notification.updated': 'agent_config',
  'system.health.updated': 'event_stream',
  'system.resync_required': 'event_stream',
} as const;
export const EventObjectLocatorSchemas = {
  job: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  research: z
    .object({
      object_id: z.union([
        z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  conclusion: z
    .object({
      object_id: z.union([
        z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  experiment: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  factor: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  strategy_version: z
    .object({
      object_id: z.union([
        z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1),
      object_revision: z.number().int().min(1),
    })
    .passthrough(),
  validation: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  approval: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  paper: z
    .object({
      object_id: z.union([
        z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  paper_run: z
    .object({
      object_id: z.union([
        z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  review: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  capability: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  snapshot: z
    .object({
      object_id: z.union([
        z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  agent_run: z
    .object({
      object_id: z.union([
        z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  tool_call: z
    .object({
      object_id: z.union([
        z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  memo: z
    .object({
      object_id: z.union([
        z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  notification: z
    .object({
      object_id: z.union([
        z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      object_version: z.number().int().min(1).nullable(),
      object_revision: z.number().int().min(1).nullable(),
    })
    .passthrough(),
  settings: z
    .object({
      object_id: z.literal('SETTINGS-DEFAULT'),
      object_version: z.null(),
      object_revision: z.number().int().min(1),
    })
    .passthrough(),
  provider_connection: z
    .object({
      object_id: z
        .string()
        .regex(new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
      object_version: z.null(),
      object_revision: z.number().int().min(1),
    })
    .passthrough(),
  agent_config: z
    .object({
      object_id: z.union([
        z.literal('RESEARCH_DIRECTOR'),
        z.literal('FACTOR_SCIENTIST'),
        z.literal('STRATEGY_SCIENTIST'),
        z.literal('PORTFOLIO_ANALYST'),
        z.literal('RED_TEAM_RESEARCHER'),
        z.literal('PERFORMANCE_ANALYST'),
      ]),
      object_version: z.null(),
      object_revision: z.number().int().min(1),
    })
    .passthrough(),
  event_stream: z
    .object({
      object_id: z.union([
        z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      object_version: z.null(),
      object_revision: z.number().int().min(1),
    })
    .passthrough(),
} as const;
export const EventObjectExamples = {
  job: { object_id: 'JOB-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  research: { object_id: 'RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  conclusion: {
    object_id: 'CONC-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  experiment: {
    object_id: 'EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  factor: { object_id: 'FAC-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  strategy_version: {
    object_id: 'STRAT-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  validation: {
    object_id: 'VAL-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  approval: { object_id: 'APR-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  paper: { object_id: 'PAPER-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  paper_run: {
    object_id: 'PRUN-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  review: { object_id: 'REV-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  capability: {
    object_id: 'CAP-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  snapshot: { object_id: 'DS-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  agent_run: {
    object_id: 'ARUN-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  tool_call: {
    object_id: 'TCALL-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  memo: { object_id: 'MEMO-01ARZ3NDEKTSV4RRFFQ69G5FAV', object_version: 1, object_revision: 1 },
  notification: {
    object_id: 'NOTIF-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: 1,
    object_revision: 1,
  },
  settings: { object_id: 'SETTINGS-DEFAULT', object_version: null, object_revision: 1 },
  provider_connection: {
    object_id: '550e8400-e29b-41d4-a716-446655440000',
    object_version: null,
    object_revision: 1,
  },
  agent_config: { object_id: 'RESEARCH_DIRECTOR', object_version: null, object_revision: 1 },
  event_stream: {
    object_id: 'EVT-01ARZ3NDEKTSV4RRFFQ69G5FAV',
    object_version: null,
    object_revision: 1,
  },
} as const;

export const CanonicalErrorCodeSchema = z.union([
  z.literal('INVALID_REQUEST'),
  z.literal('RESOURCE_NOT_FOUND'),
  z.literal('PRECONDITION_REQUIRED'),
  z.literal('REVISION_MISMATCH'),
  z.literal('IDEMPOTENCY_CONFLICT'),
  z.literal('IDEMPOTENCY_IN_PROGRESS'),
  z.literal('RESOURCE_CONFLICT'),
  z.literal('SERVICE_DEGRADED'),
  z.literal('INTERNAL_ERROR'),
  z.literal('UNAUTHENTICATED'),
  z.literal('PERMISSION_DENIED'),
  z.literal('HUMAN_APPROVAL_REQUIRED'),
  z.literal('RESEARCH_NOT_MUTABLE'),
  z.literal('RESEARCH_WAITING_USER'),
  z.literal('EXPERIMENT_IMMUTABLE'),
  z.literal('EXPERIMENT_INVALID'),
  z.literal('NON_REPRODUCIBLE'),
  z.literal('MULTIPLE_TESTING_LIMIT_REACHED'),
  z.literal('STRATEGY_VERSION_FROZEN'),
  z.literal('STRATEGY_VERSION_MISMATCH'),
  z.literal('STRATEGY_NOT_FROZEN'),
  z.literal('STRATEGY_NOT_VALIDATED'),
  z.literal('VALIDATION_IN_PROGRESS'),
  z.literal('VALIDATION_FAILED'),
  z.literal('VALIDATION_PREREQUISITES_INCOMPLETE'),
  z.literal('VALIDATION_TEST_BLOCKED'),
  z.literal('HOLDOUT_LOCKED'),
  z.literal('HOLDOUT_APPROVAL_REQUIRED'),
  z.literal('HOLDOUT_PREREQUISITES_INCOMPLETE'),
  z.literal('HOLDOUT_ALREADY_EXPOSED'),
  z.literal('HOLDOUT_RESULT_FORBIDDEN'),
  z.literal('APPROVAL_STALE'),
  z.literal('APPROVAL_ALREADY_RESOLVED'),
  z.literal('APPROVAL_PREREQUISITES_CHANGED'),
  z.literal('APPROVAL_TYPE_MISMATCH'),
  z.literal('DATA_CAPABILITY_MISSING'),
  z.literal('DATA_QUALITY_BLOCKED'),
  z.literal('DATA_SNAPSHOT_MISSING'),
  z.literal('PIT_GUARANTEE_UNAVAILABLE'),
  z.literal('STALE_DATA'),
  z.literal('PROVIDER_UNAVAILABLE'),
  z.literal('JOB_CONFLICT'),
  z.literal('JOB_NOT_CANCELLABLE'),
  z.literal('JOB_LEASE_LOST'),
  z.literal('JOB_FAILED'),
  z.literal('PAPER_APPROVAL_REQUIRED'),
  z.literal('PAPER_RISK_BLOCKED'),
  z.literal('PAPER_DATA_BLOCKED'),
  z.literal('PAPER_DUPLICATE_RUN'),
  z.literal('PAPER_VERSION_MISMATCH'),
  z.literal('RISK_LIMIT_EXCEEDED'),
  z.literal('AGENT_DISABLED'),
  z.literal('AGENT_TOOL_FORBIDDEN'),
  z.literal('AGENT_BUDGET_EXCEEDED'),
  z.literal('AGENT_OUTPUT_INVALID'),
  z.literal('AGENT_MODEL_UNAVAILABLE'),
  z.literal('AGENT_RESUME_CONFLICT'),
  z.literal('AGENT_CONTEXT_STALE'),
  z.literal('AGENT_RETRY_EXHAUSTED'),
  z.literal('TOOL_INPUT_INVALID'),
  z.literal('TOOL_EXECUTION_FAILED'),
  z.literal('CREDENTIAL_INVALID'),
  z.literal('CREDENTIAL_NOT_CONFIGURED'),
  z.literal('CONNECTION_VALIDATION_EXPIRED'),
  z.literal('CONNECTION_KIND_MISMATCH'),
  z.literal('LAST_ACTIVE_KEY_REQUIRED'),
  z.literal('CONFIGURATION_VALIDATION_FAILED'),
  z.literal('CONFIGURATION_APPLY_FAILED'),
  z.literal('CONFIGURATION_RESTART_REQUIRED'),
  z.literal('DATABASE_CONNECTION_FAILED'),
  z.literal('DATABASE_SCHEMA_INCOMPATIBLE'),
  z.literal('DATABASE_SWITCH_FAILED'),
  z.literal('BOOTSTRAP_LOCKED'),
  z.literal('DATABASE_DISCONNECTED'),
  z.literal('CSRF_REQUIRED'),
]);
export const FieldErrorSchema = z
  .object({ field: z.string(), code: z.string(), message: z.string() })
  .strict();
export const ProblemContextSchema = z
  .object({
    object_type: z
      .union([
        z.union([
          z.literal('job'),
          z.literal('research'),
          z.literal('conclusion'),
          z.literal('experiment'),
          z.literal('factor'),
          z.literal('strategy_version'),
          z.literal('validation'),
          z.literal('approval'),
          z.literal('paper'),
          z.literal('paper_run'),
          z.literal('review'),
          z.literal('capability'),
          z.literal('snapshot'),
          z.literal('agent_run'),
          z.literal('tool_call'),
          z.literal('memo'),
          z.literal('notification'),
          z.literal('settings'),
          z.literal('provider_connection'),
          z.literal('agent_config'),
          z.literal('event_stream'),
        ]),
        z.null(),
      ])
      .optional(),
    object_id: z
      .union([
        z.union([
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(39)
              .max(39)
              .regex(
                new RegExp(
                  '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.literal('SETTINGS-DEFAULT'),
          z
            .string()
            .regex(
              new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            ),
          z.union([
            z.literal('RESEARCH_DIRECTOR'),
            z.literal('FACTOR_SCIENTIST'),
            z.literal('STRATEGY_SCIENTIST'),
            z.literal('PORTFOLIO_ANALYST'),
            z.literal('RED_TEAM_RESEARCHER'),
            z.literal('PERFORMANCE_ANALYST'),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
        ]),
        z.null(),
      ])
      .optional(),
    object_version: z.number().int().min(1).nullable().optional(),
    object_revision: z.number().int().min(1).nullable().optional(),
    expected_revision: z.number().int().min(1).nullable().optional(),
    actual_revision: z.number().int().min(1).nullable().optional(),
    approval_id: z
      .union([
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
    validation_id: z
      .union([
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
    retry_after_seconds: z.number().int().min(1).nullable().optional(),
  })
  .strict();
export const ApiProblemSchema = z
  .object({
    type: z.string(),
    title: z.string(),
    status: z.number().int().min(400).max(599),
    code: CanonicalErrorCodeSchema,
    detail: z.string().nullable(),
    instance: z.string().nullable(),
    request_id: z.string(),
    retryable: z.boolean(),
    field_errors: z.array(FieldErrorSchema),
    context: ProblemContextSchema,
  })
  .strict();
export const GeneralAccessKeyLoginRequestSchema = z
  .object({
    key: z
      .string()
      .min(60)
      .max(256)
      .regex(new RegExp('^qfk_gak_[a-z0-9]{16,32}\\.[A-Za-z0-9_-]{43,}$')),
  })
  .strict();
export const GeneralAccessKeyMetadataSchema = z
  .object({
    key_id: z.string().regex(new RegExp('^gak_[a-z0-9]{16,32}$')),
    label: z.string().min(1).max(80),
    masked_hint: z.string().min(3).max(32),
    status: z.union([z.literal('ACTIVE'), z.literal('REVOKED'), z.literal('EXPIRED')]),
    expires_at: z.iso.datetime().nullable(),
    last_used_at: z.iso.datetime().nullable(),
    revision: z.number().int().min(1),
    created_at: z.iso.datetime(),
  })
  .strict();
export const GeneralAccessKeyListSchema = z
  .object({ items: z.array(GeneralAccessKeyMetadataSchema) })
  .strict();
export const GeneralAccessKeyCreateRequestSchema = z
  .object({ label: z.string().min(1).max(80), expires_at: z.iso.datetime().nullable().optional() })
  .strict();
export const GeneralAccessKeyIssuedSchema = z
  .object({
    key: GeneralAccessKeyMetadataSchema,
    secret: z
      .string()
      .min(60)
      .max(256)
      .regex(new RegExp('^qfk_gak_[a-z0-9]{16,32}\\.[A-Za-z0-9_-]{43,}$')),
  })
  .strict();
export const OwnerSessionViewSchema = z
  .object({
    principal: z.literal('OWNER'),
    auth_method: z.literal('GENERAL_ACCESS_KEY'),
    key_id: z.string().regex(new RegExp('^gak_[a-z0-9]{16,32}$')),
    issued_at: z.iso.datetime(),
    last_seen_at: z.iso.datetime(),
    expires_at: z.iso.datetime(),
    csrf_token: z.string().min(32).max(256),
  })
  .strict();
export const SessionBootstrapResponseSchema = z
  .object({ session: OwnerSessionViewSchema })
  .strict();
export const ConfigurationCatalogEntrySchema = z
  .object({
    key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
    group: z.string().min(1).max(64),
    schema_version: z.number().int().min(1),
    scope: z.literal('INSTALLATION'),
    sensitivity: z.union([z.literal('PUBLIC'), z.literal('MASKED'), z.literal('SECRET')]),
    apply_mode: z.union([
      z.literal('LIVE_NEW_WORK'),
      z.literal('DRAIN_RELOAD'),
      z.literal('RESTART_REQUIRED'),
      z.literal('SECURITY_IMMEDIATE'),
    ]),
    consumers: z.array(z.string().min(1).max(80)).min(1),
    dependencies: z.array(z.string().min(1).max(160)),
    schema: z.object({}).passthrough(),
    validator: z.string().min(1).max(160),
    safe_range: z.object({}).passthrough().nullable().optional(),
  })
  .strict();
export const ConfigurationCatalogSchema = z
  .object({
    catalog_version: z.string().min(1).max(64),
    entries: z.array(ConfigurationCatalogEntrySchema),
  })
  .strict();
export const ConfigurationValueWriteSchema = z
  .object({
    key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
    value: z
      .union([
        z.string(),
        z.number(),
        z.boolean(),
        z.object({}).passthrough(),
        z.array(z.unknown()),
        z.null(),
      ])
      .optional(),
    secret: z.string().min(1).max(16384).optional(),
  })
  .strict()
  .refine(
    (value) =>
      [['value'], ['secret']].some((required) =>
        required.every((key) => (value as Record<string, unknown>)[key] !== undefined),
      ),
    { message: 'Object must satisfy one canonical variant' },
  );
export const ConfigurationCandidateRequestSchema = z
  .object({
    base_revision: z.number().int().min(1),
    values: z.array(ConfigurationValueWriteSchema).min(1),
  })
  .strict();
export const ConfigurationValueViewSchema = z
  .object({
    key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
    sensitivity: z.union([z.literal('PUBLIC'), z.literal('MASKED'), z.literal('SECRET')]),
    configured: z.boolean(),
    value: z.union([
      z.string(),
      z.number(),
      z.boolean(),
      z.object({}).passthrough(),
      z.array(z.unknown()),
      z.null(),
    ]),
    masked_hint: z.string().max(80).nullable(),
  })
  .strict();
export const ConfigurationCandidateSchema = z
  .object({
    revision: z.number().int().min(1),
    state: z.union([
      z.literal('CANDIDATE'),
      z.literal('VALIDATED'),
      z.literal('APPLYING'),
      z.literal('FAILED'),
      z.literal('ACTIVE'),
      z.literal('SUPERSEDED'),
    ]),
    base_revision: z.number().int().min(1),
    catalog_version: z.string(),
    values: z.array(ConfigurationValueViewSchema),
    snapshot_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ConfigurationValidationResultSchema = z
  .object({
    revision: z.number().int().min(1),
    status: z.union([z.literal('VALID'), z.literal('INVALID')]),
    errors: z.array(FieldErrorSchema),
    warnings: z.array(FieldErrorSchema),
    validated_at: z.iso.datetime(),
  })
  .strict();
export const ConfigurationActivateRequestSchema = z
  .object({ revision: z.number().int().min(1) })
  .strict();
export const ConfigurationRollbackRequestSchema = z
  .object({ source_revision: z.number().int().min(1) })
  .strict();
export const DatabaseConnectionCandidateSchema = z
  .object({
    revision: z.number().int().min(1),
    state: z.union([
      z.literal('CANDIDATE'),
      z.literal('VALIDATED'),
      z.literal('ACTIVE'),
      z.literal('FAILED'),
      z.literal('SUPERSEDED'),
    ]),
    base_revision: z.number().int().min(1),
    host: z.string().min(1).max(253),
    port: z.number().int().min(1).max(65535),
    database: z.string().min(1).max(63),
    tls_mode: z.union([z.literal('DISABLED'), z.literal('VERIFY_CA'), z.literal('VERIFY_FULL')]),
    username_masked: z.string().min(1).max(80),
    password_configured: z.boolean(),
    client_key_configured: z.boolean(),
    pool_profile: z.string().max(64).nullable().optional(),
    created_at: z.iso.datetime(),
  })
  .strict();
export const DatabaseConnectionStatusSchema = z
  .object({
    state: z.union([
      z.literal('BOOTSTRAP_LOCKED'),
      z.literal('DATABASE_DISCONNECTED'),
      z.literal('VALIDATING'),
      z.literal('APPLYING'),
      z.literal('READY'),
      z.literal('DEGRADED'),
    ]),
    active_revision: z.number().int().min(1).nullable(),
    candidate_revision: z.number().int().min(1).nullable(),
    last_known_good_revision: z.number().int().min(1).nullable(),
    active: z.union([DatabaseConnectionCandidateSchema, z.null()]),
    candidate: z.union([DatabaseConnectionCandidateSchema, z.null()]),
    domain_operations: z.union([
      z.literal('AVAILABLE'),
      z.literal('READ_ONLY_RECOVERY'),
      z.literal('UNAVAILABLE'),
    ]),
    checked_at: z.iso.datetime(),
  })
  .strict();
export const DatabaseConnectionCandidateRequestSchema = z
  .object({
    base_revision: z.number().int().min(1),
    connection: z
      .object({
        host: z.string().min(1).max(253),
        port: z.number().int().min(1).max(65535),
        database: z.string().min(1).max(63),
        tls_mode: z.union([
          z.literal('DISABLED'),
          z.literal('VERIFY_CA'),
          z.literal('VERIFY_FULL'),
        ]),
        username: z.string().min(1).max(128),
        password: z.string().min(1).max(4096).optional(),
        client_key_pem: z.string().min(1).max(16384).optional(),
        ca_certificate_pem: z.string().min(1).max(16384).optional(),
        pool_profile: z.string().max(64).nullable().optional(),
      })
      .strict(),
  })
  .strict();
export const DatabaseConnectionCheckSchema = z
  .object({
    name: z.union([
      z.literal('NETWORK'),
      z.literal('TLS'),
      z.literal('CREDENTIAL'),
      z.literal('POSTGRES_VERSION'),
      z.literal('PRIVILEGE'),
      z.literal('SCHEMA'),
      z.literal('MIGRATION_COMPATIBILITY'),
    ]),
    status: z.union([z.literal('PASS'), z.literal('FAIL'), z.literal('SKIPPED')]),
    detail: z.string().max(300),
  })
  .strict();
export const DatabaseConnectionValidationResultSchema = z
  .object({
    revision: z.number().int().min(1),
    status: z.union([z.literal('VALID'), z.literal('INVALID')]),
    checks: z.array(DatabaseConnectionCheckSchema).min(1),
    validated_at: z.iso.datetime(),
  })
  .strict();
export const SetupStatusSchema = z
  .object({
    completed: z.boolean(),
    owner_session_ready: z.boolean(),
    ai_provider_configured: z.boolean(),
    ai_connection_id: z.string().nullable(),
    data_provider_configured: z.boolean(),
    research_policy_active: z.boolean(),
    research_policy_id: z.union([
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    risk_policy_active: z.boolean(),
    risk_policy_id: z.union([
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.null(),
    ]),
    cost_model_active: z.boolean(),
    cost_model_id: z.union([
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.null(),
    ]),
    fallback_step: z.union([
      z.literal('AI_PROVIDER'),
      z.literal('RESEARCH_DEFAULTS'),
      z.literal('RESEARCH_CONSTITUTION'),
      z.literal(null),
    ]),
  })
  .strict()
  .superRefine((value, context) => {
    const coupled = [
      ['ai_provider_configured', 'ai_connection_id'],
      ['research_policy_active', 'research_policy_id'],
      ['risk_policy_active', 'risk_policy_id'],
      ['cost_model_active', 'cost_model_id'],
    ] as const;
    for (const [activeKey, referenceKey] of coupled) {
      const active = value[activeKey];
      const reference = value[referenceKey];
      if ((active && !reference) || (!active && reference !== null))
        context.addIssue({
          code: 'custom',
          path: [referenceKey],
          message: 'readiness and reference must agree',
        });
    }
    const expectedFallback = !value.ai_provider_configured
      ? 'AI_PROVIDER'
      : !value.cost_model_active
        ? 'RESEARCH_DEFAULTS'
        : !value.research_policy_active || !value.risk_policy_active
          ? 'RESEARCH_CONSTITUTION'
          : null;
    if (value.fallback_step !== expectedFallback)
      context.addIssue({
        code: 'custom',
        path: ['fallback_step'],
        message: 'fallback precedence mismatch',
      });
    if (
      value.completed &&
      (!value.owner_session_ready ||
        !value.ai_provider_configured ||
        !value.ai_connection_id ||
        !value.research_policy_active ||
        !value.research_policy_id ||
        !value.risk_policy_active ||
        !value.risk_policy_id ||
        !value.cost_model_active ||
        !value.cost_model_id ||
        value.fallback_step !== null)
    )
      context.addIssue({
        code: 'custom',
        path: ['completed'],
        message: 'completed readiness contradiction',
      });
  });
export const SetupProviderKindSchema = z.union([z.literal('AI'), z.literal('DATA')]);
export const SetupModelCapabilitySchema = z
  .object({ model_name: z.string(), connection_test_supported: z.literal(true) })
  .strict();
export const DateCoverageSchema = z
  .object({ start: z.iso.date().nullable(), end: z.iso.date().nullable() })
  .strict();
export const PointInTimeCapabilitySchema = z
  .object({
    supported: z.boolean().nullable(),
    available_from: z.iso.date().nullable(),
    semantics: z.string().nullable(),
  })
  .strict();
export const CapabilityLimitationSchema = z
  .object({ code: z.string(), detail: z.string() })
  .strict();
export const DataCapabilitySchema = z
  .object({
    capability_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    provider_id: z.string(),
    capability_key: z.string(),
    state: z.union([
      z.literal('SUPPORTED'),
      z.literal('PARTIAL'),
      z.literal('UNAVAILABLE'),
      z.literal('UNKNOWN'),
    ]),
    asset_classes: z.array(z.string()),
    frequencies: z.array(z.string()),
    coverage: DateCoverageSchema,
    point_in_time: PointInTimeCapabilitySchema,
    fields: z.array(z.string()),
    limitations: z.array(CapabilityLimitationSchema),
    checked_at: z.iso.datetime(),
  })
  .strict();
export const SetupProviderCapabilitySchema = z
  .object({
    provider_id: z.string(),
    display_name: z.string(),
    kind: SetupProviderKindSchema,
    connection_test_supported: z.literal(true),
    models: z.array(SetupModelCapabilitySchema),
    data_capabilities: z.array(DataCapabilitySchema),
  })
  .strict();
export const SetupCapabilityCatalogSchema = z
  .object({
    providers: z.array(SetupProviderCapabilitySchema),
    server_checked_at: z.iso.datetime(),
  })
  .strict();
export const LiveConnectorValidationRequestSchema = z
  .object({
    connection_id: z.string().min(1).max(80).regex(new RegExp('^[A-Za-z0-9._-]+$')),
    endpoint: z.string().min(1).max(2048).regex(new RegExp('^https://')),
    key_id: z.string().min(1).max(160),
    credential: z.string().min(1).max(16384),
    expected_account_id: z.string().min(1).max(160).nullable().optional(),
  })
  .strict();
export const LiveConnectorValidationResultSchema = z
  .object({
    connection_id: z.string().min(1).max(80),
    state: z.union([z.literal('SUCCESS'), z.literal('FAILED')]),
    error_code: z.string().nullable(),
    connector_id: z.string().nullable(),
    protocol_version: z.string().nullable(),
    capabilities_hash: z.string().regex(new RegExp('^[0-9a-f]{64}$')).nullable(),
    account_ids: z.array(z.string()),
    assets: z.array(
      z.union([
        z.literal('EQUITY'),
        z.literal('FUTURE'),
        z.literal('OPTION'),
        z.literal('FX_SPOT'),
        z.literal('CRYPTO_SPOT'),
        z.literal('CRYPTO_PERPETUAL'),
      ]),
    ),
    checked_at: z.iso.datetime(),
  })
  .strict();
export const SetupProviderConnectionValidationRequestSchema = z
  .object({
    provider_id: z.string(),
    kind: SetupProviderKindSchema,
    model_name: z.string().nullable().optional(),
    credential: z.string().min(1),
  })
  .strict();
export const SetupProviderConnectionValidationSuccessSchema = z
  .object({
    connection_id: z.string().min(1),
    provider_id: z.string(),
    kind: SetupProviderKindSchema,
    state: z.literal('SUCCESS'),
    detail: z.string().nullable(),
    data_capabilities: z.array(DataCapabilitySchema),
    checked_at: z.iso.datetime(),
  })
  .strict();
export const SetupProviderConnectionValidationFailureSchema = z
  .object({
    provider_id: z.string(),
    kind: SetupProviderKindSchema,
    state: z.literal('FAILED'),
    detail: z.string().min(1),
    error_code: CanonicalErrorCodeSchema,
    data_capabilities: z.array(DataCapabilitySchema),
    checked_at: z.iso.datetime(),
  })
  .strict();
export const SetupProviderConnectionValidationResultSchema = z.union([
  SetupProviderConnectionValidationSuccessSchema,
  SetupProviderConnectionValidationFailureSchema,
]);
export const SetupCompleteRequestSchema = z
  .object({ configuration_revision: z.number().int().min(1) })
  .strict();
export const ConfigurationConsumerStateSchema = z
  .object({
    consumer: z.string().min(1).max(80),
    desired_revision: z.number().int().min(1),
    applied_revision: z.number().int().min(1).nullable(),
    ack: z.union([z.literal('PENDING'), z.literal('ACKED'), z.literal('FAILED')]),
    error_code: z.union([CanonicalErrorCodeSchema, z.null()]),
    heartbeat_at: z.iso.datetime(),
  })
  .strict();
export const ConfigurationActiveSchema = z
  .object({
    active_revision: z.number().int().min(1),
    last_known_good_revision: z.number().int().min(1),
    catalog_version: z.string(),
    values: z.array(ConfigurationValueViewSchema),
    snapshot_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    consumer_states: z.array(ConfigurationConsumerStateSchema),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const SettingsDetailSchema = ConfigurationActiveSchema;
export const ObjectRefSchema = z
  .object({
    type: z.union([
      z.literal('research_policy'),
      z.literal('risk_policy'),
      z.literal('cost_model'),
      z.literal('credential'),
      z.literal('capability'),
      z.literal('dataset'),
      z.literal('snapshot'),
      z.literal('data_quality_run'),
      z.literal('data_quality_issue'),
      z.literal('research'),
      z.literal('evidence'),
      z.literal('conclusion'),
      z.literal('experiment'),
      z.literal('factor'),
      z.literal('strategy'),
      z.literal('validation'),
      z.literal('exposure'),
      z.literal('red_team_run'),
      z.literal('portfolio'),
      z.literal('memo'),
      z.literal('approval'),
      z.literal('paper'),
      z.literal('paper_run'),
      z.literal('paper_order'),
      z.literal('paper_fill'),
      z.literal('review'),
      z.literal('agent_run'),
      z.literal('tool_call'),
      z.literal('job'),
      z.literal('domain_event'),
      z.literal('audit_event'),
      z.literal('artifact'),
      z.literal('notification'),
      z.literal('provenance'),
    ]),
    id: z.union([
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^CRED-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^CRED-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^DSSET-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^DSSET-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^DQ-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^DQ-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^DQI-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^DQI-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^EVID-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^EVID-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^HOLD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^HOLD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^RT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^RT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^PORT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^PORT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^PORD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^PORD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^PFILL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^PFILL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^AUD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^AUD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
    ]),
    version: z.number().int().min(1).nullable(),
    revision: z.number().int().min(1),
  })
  .strict()
  .superRefine((value, context) => {
    if (!PublicIdSchemas[value.type].safeParse(value.id).success)
      context.addIssue({
        code: 'custom',
        path: ['id'],
        message: 'ObjectRef type and ID prefix must agree',
      });
  });
export const ActionCapabilitySchema = z
  .object({
    action: z.string(),
    visibility: z.union([z.literal('SHOW'), z.literal('HIDE')]),
    allowed: z.boolean(),
    reason_code: z.union([CanonicalErrorCodeSchema, z.null()]),
    reason_detail: z.string().nullable(),
    requires_confirmation: z.boolean(),
    idempotency_required: z.boolean(),
    if_match_required: z.boolean(),
    result_mode: z.union([z.literal('IMMEDIATE'), z.literal('JOB')]),
    danger_level: z.union([
      z.literal('NORMAL'),
      z.literal('STATE_CHANGE'),
      z.literal('IRREVERSIBLE'),
      z.literal('CAPITAL_GATE'),
    ]),
  })
  .strict();
export const OverviewAttentionItemSchema = z
  .object({
    attention_id: z.string(),
    type: z.union([
      z.literal('CRITICAL'),
      z.literal('APPROVAL_REQUIRED'),
      z.literal('AGENT_WAITING'),
      z.literal('VALIDATION_FAILURE'),
      z.literal('INFORMATIONAL'),
    ]),
    severity: z.union([
      z.literal('CRITICAL'),
      z.literal('ACTION_REQUIRED'),
      z.literal('WARNING'),
      z.literal('INFORMATIONAL'),
    ]),
    object: ObjectRefSchema,
    title_key: z.string(),
    summary: z.string(),
    reason_code: z.union([CanonicalErrorCodeSchema, z.null()]),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict();
export const ResearchStatusSchema = z.union([
  z.literal('DRAFT'),
  z.literal('PLANNING'),
  z.literal('RUNNING'),
  z.literal('WAITING_USER'),
  z.literal('PAUSED'),
  z.literal('CANDIDATE_FOUND'),
  z.literal('COMPLETED'),
  z.literal('REJECTED'),
  z.literal('FAILED'),
]);
export const JobProgressSchema = z
  .object({
    mode: z.union([z.literal('NONE'), z.literal('UNITS')]),
    completed_units: z.number().int().min(0).nullable(),
    total_units: z.number().int().min(1).nullable(),
    unit: z.string().nullable(),
    percent: z.number().min(0).max(100).nullable(),
    current_step_key: z.string().nullable(),
    current_step_label: z.string().nullable(),
  })
  .strict();
export const AgentRoleKeySchema = z.union([
  z.literal('RESEARCH_DIRECTOR'),
  z.literal('FACTOR_SCIENTIST'),
  z.literal('STRATEGY_SCIENTIST'),
  z.literal('PORTFOLIO_ANALYST'),
  z.literal('RED_TEAM_RESEARCHER'),
  z.literal('PERFORMANCE_ANALYST'),
]);
export const OverviewCurrentAgentSchema = z
  .object({
    role: AgentRoleKeySchema,
    agent_run_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
  })
  .strict();
export const OverviewActiveResearchItemSchema = z
  .object({
    research_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    title: z.string(),
    status: ResearchStatusSchema,
    evidence_status: z.union([
      z.literal('INSUFFICIENT'),
      z.literal('WEAK'),
      z.literal('MIXED'),
      z.literal('SUPPORTIVE'),
      z.literal('STRONG'),
    ]),
    progress: JobProgressSchema,
    current_agent: z.union([OverviewCurrentAgentSchema, z.null()]),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const OverviewStrategyPipelineSchema = z
  .object({
    candidate: z.number().int().min(0),
    frozen: z.number().int().min(0),
    validating: z.number().int().min(0),
    validated: z.number().int().min(0),
    paper: z.number().int().min(0),
  })
  .strict();
export const ProvenanceRefSchema = z
  .object({
    provenance_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
  })
  .strict();
export const OverviewPaperSummarySchema = z
  .object({
    active_count: z.number().int().min(0),
    total_nav: z.string().nullable(),
    currency: z.string().regex(new RegExp('^[A-Z]{3}$')),
    daily_return: z.string().nullable(),
    mtd_return: z.string().nullable(),
    since_start_return: z.string().nullable(),
    benchmark_since_start_return: z.string().nullable(),
    as_of_date: z.iso.date().nullable(),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
  })
  .strict();
export const ChartXAxisSchema = z
  .object({
    kind: z.union([z.literal('TIME'), z.literal('CATEGORY'), z.literal('NUMERIC')]),
    timezone: z.string().nullable(),
  })
  .strict();
export const ChartValueFormatSchema = z
  .object({
    kind: z.union([
      z.literal('DECIMAL'),
      z.literal('PERCENT'),
      z.literal('BPS'),
      z.literal('CURRENCY'),
      z.literal('INTEGER'),
    ]),
    precision: z.number().int().min(0).max(18).nullable(),
  })
  .strict();
export const ChartPointSchema = z
  .object({ x: z.union([z.string(), z.number()]), y: z.string().nullable() })
  .strict();
export const ChartSeriesSchema = z
  .object({
    series_id: z.string(),
    series_key: z.string(),
    display_label: z.string(),
    unit: z.string(),
    value_format: ChartValueFormatSchema,
    points: z.array(ChartPointSchema),
  })
  .strict();
export const ChartPeriodMarkerSchema = z
  .object({
    period_type: z.union([
      z.literal('RESEARCH'),
      z.literal('VALIDATION'),
      z.literal('HOLDOUT'),
      z.literal('PAPER'),
    ]),
    start: z.iso.date(),
    end: z.iso.date(),
    state: z.union([z.literal('EXPOSED'), z.literal('LOCKED')]),
  })
  .strict();
export const ChartAssumptionSchema = z
  .object({ key: z.string(), value: z.string(), unit: z.string().nullable() })
  .strict();
export const EquityCurveSummaryParamsSchema = z
  .object({ ending_nav: z.string().nullable(), benchmark_ending_nav: z.string().nullable() })
  .strict();
export const ChartSummarySchema = z
  .object({
    template_key: z.literal('chart.equity_curve.summary'),
    params: EquityCurveSummaryParamsSchema,
  })
  .strict();
export const ChartDownsamplingSchema = z
  .object({
    applied: z.boolean(),
    source_points: z.number().int().min(0),
    returned_points: z.number().int().min(0),
    method: z.string().nullable(),
  })
  .strict();
export const ChartAggregateSchema = z
  .object({
    schema_version: z.literal(1),
    chart_id: z.string(),
    chart_type: z.literal('EQUITY_CURVE'),
    metric_key: z.string(),
    x_axis: ChartXAxisSchema,
    series: z.array(ChartSeriesSchema),
    period_markers: z.array(ChartPeriodMarkerSchema),
    assumptions: z.array(ChartAssumptionSchema),
    summary: ChartSummarySchema,
    downsampling: ChartDownsamplingSchema,
    provenance: ProvenanceRefSchema,
    generated_at: z.iso.datetime(),
  })
  .strict();
export const OverviewRecentFindingSchema = z
  .object({
    finding_id: z.string(),
    evidence_status: z.union([
      z.literal('INSUFFICIENT'),
      z.literal('WEAK'),
      z.literal('MIXED'),
      z.literal('SUPPORTIVE'),
      z.literal('STRONG'),
    ]),
    finding: z.string(),
    research: ObjectRefSchema,
    provenance: ProvenanceRefSchema,
    updated_at: z.iso.datetime(),
  })
  .strict();
export const OverviewAgentActivityItemSchema = z
  .object({
    agent_run_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    role: AgentRoleKeySchema,
    objective: z.string(),
    status: z.union([
      z.literal('QUEUED'),
      z.literal('RUNNING'),
      z.literal('WAITING_USER'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('CANCELLED'),
    ]),
    decision_summary: z.string().nullable(),
    next_action: z.string().nullable(),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const OverviewDataHealthSchema = z
  .object({
    state: z.union([
      z.literal('HEALTHY'),
      z.literal('DEGRADED'),
      z.literal('BLOCKED'),
      z.literal('UNKNOWN'),
    ]),
    blocker_count: z.number().int().min(0),
    warning_count: z.number().int().min(0),
    checked_at: z.iso.datetime(),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict();
export const OverviewReadModelSchema = z
  .object({
    as_of: z.iso.datetime(),
    revision: z.number().int().min(1),
    needs_attention: z.array(OverviewAttentionItemSchema),
    active_research: z.array(OverviewActiveResearchItemSchema),
    strategy_pipeline: OverviewStrategyPipelineSchema,
    paper_summary: OverviewPaperSummarySchema,
    paper_performance_chart: z.union([ChartAggregateSchema, z.null()]),
    recent_findings: z.array(OverviewRecentFindingSchema),
    agent_activity: z.array(OverviewAgentActivityItemSchema),
    data_health: OverviewDataHealthSchema,
    provenance: z.array(ProvenanceRefSchema),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict();
export const DataCapabilityListSchema = z.array(DataCapabilitySchema);
export const ResearchSummarySchema = z
  .object({
    research_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    title: z.string(),
    status: ResearchStatusSchema,
    evidence_status: z.union([
      z.literal('INSUFFICIENT'),
      z.literal('WEAK'),
      z.literal('MIXED'),
      z.literal('SUPPORTIVE'),
      z.literal('STRONG'),
    ]),
    current_revision_no: z.number().int().min(1),
    revision: z.number().int().min(1),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const PageInfoSchema = z
  .object({ next_cursor: z.string().nullable(), has_more: z.boolean() })
  .strict();
export const ResearchPageSchema = z
  .object({ items: z.array(ResearchSummarySchema), page: PageInfoSchema })
  .strict();
export const ResearchCreateRequestSchema = z
  .object({
    title: z.string().min(1).max(256),
    original_user_prompt: z.string().min(1),
    research_policy_id: z
      .union([
        z.union([
          z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
  })
  .strict();
export const ResearchStartRequestSchema = z
  .object({
    research_revision_no: z.number().int().min(1),
    capability_evaluation_confirmed: z.literal(true),
  })
  .strict();
export const UniverseSpecSchema = z
  .object({
    asset_class: z.string(),
    symbols: z.array(z.string()),
    universe_id: z.string().nullable(),
  })
  .strict();
export const DateRangeSchema = z.object({ start: z.iso.date(), end: z.iso.date() }).strict();
export const ResearchBriefReadModelSchema = z
  .object({
    revision_no: z.number().int().min(1),
    question: z.string(),
    hypothesis: z.string().nullable(),
    economic_rationale: z.string().nullable(),
    supporting_evidence_definition: z.string().nullable(),
    disconfirming_evidence_definition: z.string().nullable(),
    universe: UniverseSpecSchema,
    benchmark: z.string(),
    period: DateRangeSchema,
    frequency: z.literal('DAILY'),
    content_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict();
export const ResearchConclusionReadModelSchema = z
  .object({
    conclusion_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    evidence_status: z.union([
      z.literal('INSUFFICIENT'),
      z.literal('WEAK'),
      z.literal('MIXED'),
      z.literal('SUPPORTIVE'),
      z.literal('STRONG'),
    ]),
    summary: z.string(),
    evidence_refs: z.array(ObjectRefSchema),
    uncertainties: z.array(z.string()),
    recommendation: z.string().nullable(),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ResearchPlanNodeReadModelSchema = z
  .object({
    node_key: z.string(),
    title: z.string(),
    owner_agent_role: z.string().nullable(),
    status: z.union([
      z.literal('PENDING'),
      z.literal('RUNNING'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('SKIPPED'),
    ]),
    depends_on: z.array(z.string()),
    objective: z.string().nullable(),
    finding_summary: z.string().nullable(),
    experiment_count: z.number().int().min(0),
    sort_order: z.number().int(),
  })
  .strict();
export const ResearchEvidenceResultLocatorSchema = z
  .object({
    result_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    metric_key: z.string().nullable(),
    artifact: z.union([ObjectRefSchema, z.null()]),
  })
  .strict();
export const ResearchEvidenceItemSchema = z
  .object({
    evidence: ObjectRefSchema,
    stance: z.union([z.literal('SUPPORTING'), z.literal('CONTRADICTING'), z.literal('NEUTRAL')]),
    claim: z.string(),
    source_experiment: ObjectRefSchema,
    result_locator: ResearchEvidenceResultLocatorSchema,
    strength: z.union([z.literal('WEAK'), z.literal('MODERATE'), z.literal('STRONG')]),
    limitations: z.string().nullable(),
    is_invalidated: z.boolean(),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const NamedVersionSchema = z.object({ name: z.string(), version: z.string() }).strict();
export const ResearchCurrentAgentWorkSchema = z
  .object({
    agent_run_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    agent_role: z.string(),
    status: z.union([
      z.literal('QUEUED'),
      z.literal('RUNNING'),
      z.literal('WAITING_USER'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('CANCELLED'),
    ]),
    objective: z.string().nullable(),
    current_action: z.string().nullable(),
    tool: z.union([NamedVersionSchema, z.null()]),
    next_action: z.string().nullable(),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const ResearchOverviewReadModelSchema = z
  .object({
    brief: ResearchBriefReadModelSchema,
    current_conclusion: z.union([ResearchConclusionReadModelSchema, z.null()]),
    progress: z.array(ResearchPlanNodeReadModelSchema),
    latest_evidence: z.array(ResearchEvidenceItemSchema),
    current_agent_work: z.union([ResearchCurrentAgentWorkSchema, z.null()]),
  })
  .strict();
export const ResearchPlanReadModelSchema = z
  .object({
    plan_version: z.number().int().min(1),
    source_revision_no: z.number().int().min(1),
    status: z.union([z.literal('ACTIVE'), z.literal('SUPERSEDED')]),
    rationale_summary: z.string().nullable(),
    nodes: z.array(ResearchPlanNodeReadModelSchema),
    content_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ResearchTimelineItemSchema = z
  .object({
    event_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    agent_role: z.string().nullable(),
    objective: z.string().nullable(),
    tool: z.union([NamedVersionSchema, z.null()]),
    result_summary: z.string().nullable(),
    decision_summary: z.string().nullable(),
    next_action: z.string().nullable(),
    object: z.union([ObjectRefSchema, z.null()]),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    occurred_at: z.iso.datetime(),
  })
  .strict();
export const ResearchTimelinePageSchema = z
  .object({ items: z.array(ResearchTimelineItemSchema), page: PageInfoSchema })
  .strict();
export const ExperimentStatusSchema = z.union([
  z.literal('DRAFT'),
  z.literal('QUEUED'),
  z.literal('RUNNING'),
  z.literal('COMPLETED'),
  z.literal('FAILED'),
  z.literal('INVALID'),
  z.literal('CANCELLED'),
]);
export const ExperimentValidityStateSchema = z.union([
  z.literal('PENDING'),
  z.literal('VALID'),
  z.literal('INVALID'),
  z.literal('NON_REPRODUCIBLE'),
]);
export const ResearchExperimentItemSchema = z
  .object({
    experiment: ObjectRefSchema,
    objective: z.string(),
    experiment_type: z.union([
      z.literal('FACTOR_ANALYSIS'),
      z.literal('FAST_BACKTEST'),
      z.literal('PARAMETER_SENSITIVITY'),
      z.literal('DATA_VALIDATION'),
      z.literal('STRICT_VALIDATION'),
    ]),
    status: ExperimentStatusSchema,
    validity_state: ExperimentValidityStateSchema,
    job_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ResearchExperimentPageSchema = z
  .object({ items: z.array(ResearchExperimentItemSchema), page: PageInfoSchema })
  .strict();
export const ResearchEvidencePageSchema = z
  .object({ items: z.array(ResearchEvidenceItemSchema), page: PageInfoSchema })
  .strict();
export const ArtifactReadModelSchema = z
  .object({
    artifact: ObjectRefSchema,
    kind: z.string(),
    media_type: z.string(),
    sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    size_bytes: z.number().int().min(0),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ArtifactPageSchema = z
  .object({ items: z.array(ArtifactReadModelSchema), page: PageInfoSchema })
  .strict();
export const RequesterRefSchema = z
  .object({
    type: z.union([z.literal('AGENT'), z.literal('SYSTEM'), z.literal('OWNER')]),
    id: z.string(),
  })
  .strict();
export const ResearchAuditItemSchema = z
  .object({
    event_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^AUD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^AUD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    action: z.string(),
    actor: RequesterRefSchema,
    object: ObjectRefSchema,
    request_id: z.string(),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    occurred_at: z.iso.datetime(),
  })
  .strict();
export const ResearchAuditPageSchema = z
  .object({ items: z.array(ResearchAuditItemSchema), page: PageInfoSchema })
  .strict();
export const ResearchDetailSchema = z
  .object({
    research_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    title: z.string(),
    original_user_prompt: z.string(),
    normalized_question: z.string().nullable(),
    status: ResearchStatusSchema,
    evidence_status: z.union([
      z.literal('INSUFFICIENT'),
      z.literal('WEAK'),
      z.literal('MIXED'),
      z.literal('SUPPORTIVE'),
      z.literal('STRONG'),
    ]),
    current_revision_no: z.number().int().min(1),
    active_plan_version: z.number().int().min(1).nullable(),
    research_policy_id: z.union([
      z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    director_agent_version: z.string().nullable(),
    current_agent_run_id: z.union([
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.null(),
    ]),
    current_job_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    overview: ResearchOverviewReadModelSchema,
    plan: z.union([ResearchPlanReadModelSchema, z.null()]),
    timeline: ResearchTimelinePageSchema,
    experiments: ResearchExperimentPageSchema,
    evidence: ResearchEvidencePageSchema,
    artifacts: ArtifactPageSchema,
    audit: ResearchAuditPageSchema,
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime(),
    updated_at: z.iso.datetime(),
    completed_at: z.iso.datetime().nullable(),
  })
  .strict();
export const ParameterSchema = z.object({ key: z.string(), value: z.string() }).strict();
export const ExperimentCreateRequestSchema = z
  .object({
    research_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    research_revision_no: z.number().int().min(1),
    objective: z.string(),
    hypothesis: z.string(),
    experiment_type: z.union([
      z.literal('FACTOR_ANALYSIS'),
      z.literal('FAST_BACKTEST'),
      z.literal('PARAMETER_SENSITIVITY'),
      z.literal('DATA_VALIDATION'),
      z.literal('STRICT_VALIDATION'),
    ]),
    data_snapshot_id: z.union([
      z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    factor_id: z
      .union([
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
    factor_version: z.number().int().min(1).nullable().optional(),
    strategy_id: z
      .union([
        z.union([
          z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
    strategy_version: z.number().int().min(1).nullable().optional(),
    cost_model_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    parameters: z.array(ParameterSchema),
    engine_key: z.string(),
    engine_version: z.string(),
  })
  .strict();
export const ExperimentReproduceExactRequestSchema = z
  .object({ mode: z.literal('EXACT').optional() })
  .strict();
export const ExperimentReproduceExecutionOverridesSchema = z
  .object({
    engine_version: z.string().min(1).optional(),
    adapter_version: z.string().min(1).optional(),
    code_version: z.string().min(1).optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length >= 1, {
    message: 'Object requires at least 1 properties',
  });
export const ExperimentReproduceControlledOverrideRequestSchema = z
  .object({
    mode: z.literal('CONTROLLED_OVERRIDE'),
    execution_overrides: ExperimentReproduceExecutionOverridesSchema,
    reason: z.string().min(1).max(4000),
  })
  .strict();
export const ExperimentReproduceRequestSchema = z.union([
  ExperimentReproduceExactRequestSchema,
  ExperimentReproduceControlledOverrideRequestSchema,
]);
export const VersionRefSchema = z
  .object({
    id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
    ]),
    version: z.number().int().min(1),
  })
  .strict();
export const ExperimentSearchSetDimensionSchema = z
  .object({
    parameter_key: z.string(),
    value_type: z.union([
      z.literal('INTEGER'),
      z.literal('DECIMAL'),
      z.literal('STRING'),
      z.literal('BOOLEAN'),
    ]),
    kind: z.literal('SET'),
    values: z
      .array(z.string())
      .min(1)
      .refine((items) => new Set(items.map((item) => JSON.stringify(item))).size === items.length, {
        message: 'Array items must be unique',
      }),
    minimum: z.null(),
    maximum: z.null(),
    step: z.null(),
  })
  .strict();
export const ExperimentSearchRangeDimensionSchema = z
  .object({
    parameter_key: z.string(),
    value_type: z.union([z.literal('INTEGER'), z.literal('DECIMAL')]),
    kind: z.literal('RANGE'),
    values: z.array(z.unknown()).max(0),
    minimum: z.string().regex(new RegExp('^-?(0|[1-9][0-9]*)(\\.[0-9]+)?$')),
    maximum: z.string().regex(new RegExp('^-?(0|[1-9][0-9]*)(\\.[0-9]+)?$')),
    step: z.string().regex(new RegExp('^(0\\.[0-9]*[1-9][0-9]*|[1-9][0-9]*(\\.[0-9]+)?)$')),
  })
  .strict()
  .superRefine((value, context) => {
    const minimum = Number(value.minimum);
    const maximum = Number(value.maximum);
    const step = Number(value.step);
    if (!(minimum < maximum))
      context.addIssue({ code: 'custom', message: 'minimum must be less than maximum' });
    if (!(step > 0)) context.addIssue({ code: 'custom', message: 'step must be positive' });
    if (value.value_type === 'INTEGER' && ![minimum, maximum, step].every(Number.isInteger))
      context.addIssue({
        code: 'custom',
        message: 'INTEGER ranges require integral bounds and step',
      });
  });
export const ExperimentSearchDimensionSchema = z.union([
  ExperimentSearchSetDimensionSchema,
  ExperimentSearchRangeDimensionSchema,
]);
export const ExperimentSearchConfigurationSchema = z
  .object({
    method: z.union([z.literal('GRID'), z.literal('RANDOM')]),
    objective_metric_key: z.string(),
    objective_direction: z.union([z.literal('MAXIMIZE'), z.literal('MINIMIZE')]),
    max_evaluations: z.number().int().min(1),
    seed: z.number().int().nullable(),
  })
  .strict();
export const ExperimentSearchResultNotApplicableSchema = z
  .object({
    state: z.literal('NOT_APPLICABLE'),
    evaluated_count: z.literal(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null(),
    result_ref: z.null(),
    failure_code: z.null(),
  })
  .strict();
export const ExperimentSearchResultPendingSchema = z
  .object({
    state: z.literal('PENDING'),
    evaluated_count: z.literal(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null(),
    result_ref: z.null(),
    failure_code: z.null(),
  })
  .strict();
export const ExperimentSearchResultRunningSchema = z
  .object({
    state: z.literal('RUNNING'),
    evaluated_count: z.number().int().min(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null(),
    result_ref: z.null(),
    failure_code: z.null(),
  })
  .strict();
export const MetricSchema = z
  .object({ key: z.string(), value: z.string(), unit: z.string().nullable() })
  .strict();
export const ExperimentSearchResultCompletedSchema = z
  .object({
    state: z.literal('COMPLETED'),
    evaluated_count: z.number().int().min(1),
    selected_parameters: z.array(ParameterSchema).min(1),
    selected_metric: MetricSchema,
    result_ref: ObjectRefSchema,
    failure_code: z.null(),
  })
  .strict();
export const ExperimentSearchResultFailedSchema = z
  .object({
    state: z.literal('FAILED'),
    evaluated_count: z.number().int().min(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null(),
    result_ref: z.null(),
    failure_code: CanonicalErrorCodeSchema,
  })
  .strict();
export const ExperimentSearchResultSchema = z.union([
  ExperimentSearchResultNotApplicableSchema,
  ExperimentSearchResultPendingSchema,
  ExperimentSearchResultRunningSchema,
  ExperimentSearchResultCompletedSchema,
  ExperimentSearchResultFailedSchema,
]);
export const CodeVersionSchema = z.object({ commit: z.string(), build_id: z.string() }).strict();
export const PolicyRefSchema = z
  .object({
    type: z.union([z.literal('research_policy'), z.literal('risk_policy')]),
    id: z.union([
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
    ]),
    version: z.number().int().min(1),
  })
  .strict();
export const VersionedHashRefSchema = z
  .object({
    id: z.union([
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
    ]),
    version: z.number().int().min(1),
    sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict();
export const ProvenanceSchema = z
  .object({
    provenance_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    schema_version: z.literal(1),
    experiment_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    source_experiment_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    tool_call_id: z.union([
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.null(),
    ]),
    data_snapshot_ids: z.array(
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
    ),
    engine: NamedVersionSchema,
    adapter: z.union([NamedVersionSchema, z.null()]),
    code: CodeVersionSchema,
    policies: z.array(PolicyRefSchema),
    strategy: z.union([
      z.intersection(
        VersionedHashRefSchema,
        z
          .object({
            id: z
              .union([
                z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
                z
                  .string()
                  .min(42)
                  .max(42)
                  .regex(
                    new RegExp(
                      '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  ),
              ])
              .optional(),
          })
          .passthrough(),
      ),
      z.null(),
    ]),
    factors: z.array(
      z.intersection(
        VersionedHashRefSchema,
        z
          .object({
            id: z
              .union([
                z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
                z
                  .string()
                  .min(40)
                  .max(40)
                  .regex(
                    new RegExp(
                      '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  ),
              ])
              .optional(),
          })
          .passthrough(),
      ),
    ),
    cost_model: z.union([
      z.intersection(
        VersionedHashRefSchema,
        z
          .object({
            id: z
              .union([
                z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
                z
                  .string()
                  .min(41)
                  .max(41)
                  .regex(
                    new RegExp(
                      '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  ),
              ])
              .optional(),
          })
          .passthrough(),
      ),
      z.null(),
    ]),
    parameters_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')).nullable(),
    input_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    output_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    calculated_at: z.iso.datetime(),
  })
  .strict();
export const ExperimentDetailSchema = z
  .object({
    experiment_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    research_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    parent_experiment_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    source_experiment_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    research_revision_no: z.number().int().min(1),
    objective: z.string(),
    hypothesis: z.string(),
    experiment_type: z.string(),
    status: ExperimentStatusSchema,
    validity_state: ExperimentValidityStateSchema,
    data_snapshot_id: z.union([
      z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    factor_ref: z.union([
      z.intersection(
        VersionRefSchema,
        z
          .object({
            id: z
              .union([
                z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
                z
                  .string()
                  .min(40)
                  .max(40)
                  .regex(
                    new RegExp(
                      '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  ),
              ])
              .optional(),
          })
          .passthrough(),
      ),
      z.null(),
    ]),
    strategy_ref: z.union([
      z.intersection(
        VersionRefSchema,
        z
          .object({
            id: z
              .union([
                z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
                z
                  .string()
                  .min(42)
                  .max(42)
                  .regex(
                    new RegExp(
                      '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  ),
              ])
              .optional(),
          })
          .passthrough(),
      ),
      z.null(),
    ]),
    cost_model_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    parameters: z.array(ParameterSchema),
    parameters_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    search_space: z.array(ExperimentSearchDimensionSchema),
    search_configuration: z.union([ExperimentSearchConfigurationSchema, z.null()]),
    search_result: ExperimentSearchResultSchema,
    metrics: z.array(MetricSchema),
    artifacts: z.array(ArtifactReadModelSchema),
    engine: NamedVersionSchema,
    adapter: z.union([NamedVersionSchema, z.null()]),
    code_version: z.string(),
    job_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    provenance: z.union([ProvenanceSchema, z.null()]),
    action_capabilities: z.array(ActionCapabilitySchema),
    started_at: z.iso.datetime().nullable(),
    finished_at: z.iso.datetime().nullable(),
    created_at: z.iso.datetime(),
    invalidated_at: z.iso.datetime().nullable(),
    invalid_reason_code: z.union([CanonicalErrorCodeSchema, z.null()]),
    invalid_reason_detail: z.string().nullable(),
  })
  .strict();
export const StrategySignalSchema = z
  .object({
    factor_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    factor_version: z.number().int().min(1),
    direction: z.union([z.literal('LONG'), z.literal('SHORT')]),
    weight: z.string(),
  })
  .strict();
export const StrategyRulesSchema = z
  .object({
    selection_count: z.number().int().min(1),
    weighting: z.union([z.literal('EQUAL'), z.literal('SCORE'), z.literal('VOLATILITY')]),
    rebalance_frequency: z.union([
      z.literal('DAILY'),
      z.literal('WEEKLY'),
      z.literal('MONTHLY'),
      z.literal('QUARTERLY'),
    ]),
    long_short: z.boolean(),
    leverage_limit: z.string(),
    position_limit: z.string(),
  })
  .strict();
export const StrategyCreateRequestSchema = z
  .object({
    research_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    name: z.string(),
    thesis: z.string(),
    universe: UniverseSpecSchema,
    signals: z.array(StrategySignalSchema).min(1),
    rules: StrategyRulesSchema,
    cost_model_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    benchmark: z.string(),
    research_period: DateRangeSchema,
    validation_period: DateRangeSchema,
    holdout_period: DateRangeSchema,
    known_failure_modes: z.array(z.string()),
  })
  .strict();
export const FreezeStrategyRequestSchema = z
  .object({ expected_spec_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')) })
  .strict();
export const BacktestRequestSchema = z
  .object({
    snapshot_id: z.union([
      z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    cost_model_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    engine_key: z.string(),
    engine_version: z.string(),
    parameters: z.array(ParameterSchema),
  })
  .strict();
export const StrategySpecificationSchema = z
  .object({
    thesis: z.string(),
    universe: UniverseSpecSchema,
    signals: z.array(StrategySignalSchema),
    rules: StrategyRulesSchema,
    cost_model_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    benchmark: z.string(),
    research_period: DateRangeSchema,
    validation_period: DateRangeSchema,
    holdout_period: DateRangeSchema,
    known_failure_modes: z.array(z.string()),
    spec_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict();
export const StrategyBacktestResultSummarySchema = z
  .object({
    experiment: ObjectRefSchema,
    status: ExperimentStatusSchema,
    validity_state: ExperimentValidityStateSchema,
    result_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    job_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    provenance: ProvenanceRefSchema,
    started_at: z.iso.datetime().nullable(),
    finished_at: z.iso.datetime(),
  })
  .strict();
export const StrategyLatestBacktestAvailableSchema = z
  .object({
    state: z.literal('AVAILABLE'),
    result: StrategyBacktestResultSummarySchema,
    metrics: z.array(MetricSchema),
    chart: ChartAggregateSchema,
  })
  .strict();
export const StrategyLatestBacktestUnavailableSchema = z
  .object({
    state: z.union([z.literal('EMPTY'), z.literal('LOCKED')]),
    result: z.null(),
    metrics: z.array(z.unknown()).max(0),
    chart: z.null(),
  })
  .strict();
export const StrategyLatestBacktestSchema = z.union([
  StrategyLatestBacktestAvailableSchema,
  StrategyLatestBacktestUnavailableSchema,
]);
export const ValidationResultCountsSchema = z
  .object({
    pending: z.number().int().min(0),
    running: z.number().int().min(0),
    pass: z.number().int().min(0),
    warn: z.number().int().min(0),
    fail: z.number().int().min(0),
    locked: z.number().int().min(0),
    skipped: z.number().int().min(0),
  })
  .strict();
export const StrategyValidationSummarySchema = z
  .object({
    validation: ObjectRefSchema,
    status: z.union([
      z.literal('QUEUED'),
      z.literal('RUNNING'),
      z.literal('WAITING_HOLDOUT'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('CANCELLED'),
    ]),
    result: z.union([z.literal('PASS'), z.literal('WARN'), z.literal('FAIL'), z.literal(null)]),
    holdout_state: z.union([
      z.literal('LOCKED'),
      z.literal('APPROVAL_PENDING'),
      z.literal('UNLOCKED'),
      z.literal('RUNNING'),
      z.literal('EXPOSED'),
      z.literal('FAILED'),
    ]),
    test_counts: ValidationResultCountsSchema,
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    revision: z.number().int().min(1),
  })
  .strict();
export const StrategyVersionDetailSchema = z
  .object({
    strategy_id: z.union([
      z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    name: z.string(),
    version: z.number().int().min(1),
    lifecycle_state: z.union([
      z.literal('CANDIDATE'),
      z.literal('FROZEN'),
      z.literal('VALIDATING'),
      z.literal('VALIDATED'),
      z.literal('REJECTED'),
      z.literal('PAPER'),
      z.literal('RETIRED'),
    ]),
    is_frozen: z.boolean(),
    thesis: z.string(),
    universe: UniverseSpecSchema,
    signals: z.array(StrategySignalSchema),
    rules: StrategyRulesSchema,
    cost_model_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    benchmark: z.string(),
    research_period: DateRangeSchema,
    validation_period: DateRangeSchema,
    holdout_period: DateRangeSchema,
    known_failure_modes: z.array(z.string()),
    spec_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    specification: StrategySpecificationSchema,
    latest_backtest: StrategyLatestBacktestSchema,
    validation_summary: z.union([StrategyValidationSummarySchema, z.null()]),
    artifacts: z.array(ArtifactReadModelSchema),
    provenance: z.array(ProvenanceRefSchema),
    frozen_at: z.iso.datetime().nullable(),
    frozen_by: z.string().nullable(),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime(),
  })
  .strict();
export const NewExperimentResourceRefSchema = z
  .object({
    type: z.literal('experiment'),
    id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    version: z.null(),
    revision: z.literal(1),
  })
  .strict();
export const ExperimentReproduceAcceptedSchema = z
  .object({
    job_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    status: z.union([z.literal('QUEUED'), z.literal('RUNNING')]),
    progress: JobProgressSchema,
    resource_ref: NewExperimentResourceRefSchema,
    source_experiment_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    source_provenance: ProvenanceRefSchema,
    reproduce_mode: z.union([z.literal('EXACT'), z.literal('CONTROLLED_OVERRIDE')]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ValidationCreateRequestSchema = z
  .object({
    strategy_id: z.union([
      z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    strategy_version: z.number().int().min(1),
    policy_id: z.union([
      z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    strict_engine_key: z.string(),
    strict_engine_version: z.string(),
    test_suite_version: z.string(),
  })
  .strict();
export const ValidationTestResultSchema = z
  .object({
    test_key: z.string(),
    attempt_no: z.number().int().min(1),
    test_version: z.string(),
    state: z.union([
      z.literal('PENDING'),
      z.literal('RUNNING'),
      z.literal('PASS'),
      z.literal('WARN'),
      z.literal('FAIL'),
      z.literal('LOCKED'),
      z.literal('SKIPPED'),
    ]),
    purpose: z.string(),
    configuration_summary: z.string(),
    calculated_result: z.string().nullable(),
    interpretation: z.string().nullable(),
    failure_code: z.union([CanonicalErrorCodeSchema, z.null()]),
    failure_detail: z.string().nullable(),
    warning_codes: z.array(z.string()),
    artifact_ids: z.array(
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
    ),
    provenance: z.union([ProvenanceRefSchema, z.null()]),
    override_permitted: z.literal(false),
  })
  .strict();
export const ValidationDetailSchema = z
  .object({
    validation_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    strategy: z.intersection(
      VersionRefSchema,
      z
        .object({
          id: z
            .union([
              z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                ),
            ])
            .optional(),
        })
        .passthrough(),
    ),
    policy_id: z.union([
      z.string().min(29).max(29).regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    strict_engine: NamedVersionSchema,
    status: z.union([
      z.literal('QUEUED'),
      z.literal('RUNNING'),
      z.literal('WAITING_HOLDOUT'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('CANCELLED'),
    ]),
    result: z.union([z.literal('PASS'), z.literal('WARN'), z.literal('FAIL'), z.literal(null)]),
    test_suite_version: z.string(),
    tests: z.array(ValidationTestResultSchema),
    warnings: z.array(z.string()),
    failures: z.array(z.string()),
    holdout_state: z.union([
      z.literal('LOCKED'),
      z.literal('APPROVAL_PENDING'),
      z.literal('UNLOCKED'),
      z.literal('RUNNING'),
      z.literal('EXPOSED'),
      z.literal('FAILED'),
    ]),
    red_team_run_id: z.union([
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^RT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^RT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    job_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    started_at: z.iso.datetime().nullable(),
    finished_at: z.iso.datetime().nullable(),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ApprovalSummarySchema = z
  .object({
    approval_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    status: z.union([
      z.literal('PENDING'),
      z.literal('APPROVED'),
      z.literal('REJECTED'),
      z.literal('STALE'),
      z.literal('CANCELLED'),
    ]),
    revision: z.number().int().min(1),
  })
  .strict();
export const HoldoutGateSchema = z
  .object({
    validation_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    state: z.union([
      z.literal('LOCKED'),
      z.literal('APPROVAL_PENDING'),
      z.literal('UNLOCKED'),
      z.literal('RUNNING'),
      z.literal('EXPOSED'),
      z.literal('FAILED'),
    ]),
    exposure_count: z.number().int().min(0),
    period: DateRangeSchema,
    approval: z.union([ApprovalSummarySchema, z.null()]),
    action_capabilities: z.array(ActionCapabilitySchema),
    revision: z.number().int().min(1),
    validation: ValidationDetailSchema.optional(),
  })
  .strict();
export const HoldoutResultSchema = z
  .object({
    validation_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    exposure_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^HOLD-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^HOLD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    result: z.union([z.literal('PASS'), z.literal('WARN'), z.literal('FAIL')]),
    metrics: z.array(MetricSchema),
    provenance: ProvenanceSchema,
    exposed_at: z.iso.datetime(),
  })
  .strict();
export const HoldoutApprovalRequestSchema = z.object({ reason: z.string().min(1) }).strict();
export const HoldoutRunRequestSchema = z
  .object({
    approval_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
  })
  .strict();
export const ApprovalSubjectSchema = z
  .object({
    type: z.union([z.literal('STRATEGY_VERSION'), z.literal('VALIDATION'), z.literal('PAPER')]),
    id: z.union([
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
    ]),
    version: z.number().int().min(1).nullable(),
    revision: z.number().int().min(1),
    sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict();
export const ApprovalListItemSchema = z
  .object({
    approval_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    type: z.union([
      z.literal('HOLDOUT_UNLOCK'),
      z.literal('PAPER_DEPLOYMENT'),
      z.literal('PAPER_ALLOCATION_CHANGE'),
      z.literal('RETIRE_PAPER'),
    ]),
    subject: ApprovalSubjectSchema,
    requester: RequesterRefSchema,
    reason: z.string(),
    status: z.union([
      z.literal('PENDING'),
      z.literal('APPROVED'),
      z.literal('REJECTED'),
      z.literal('STALE'),
      z.literal('CANCELLED'),
    ]),
    requested_at: z.iso.datetime(),
    decided_at: z.iso.datetime().nullable(),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict();
export const ApprovalPageSchema = z
  .object({ items: z.array(ApprovalListItemSchema), page: PageInfoSchema })
  .strict();
export const ApprovalPrerequisiteSchema = z
  .object({
    key: z.string(),
    state: z.union([z.literal('PASS'), z.literal('WARN'), z.literal('FAIL')]),
    detail: z.string(),
  })
  .strict();
export const RiskSummarySchema = z
  .object({
    risk_level: z.union([
      z.literal('LOW'),
      z.literal('MEDIUM'),
      z.literal('HIGH'),
      z.literal('CRITICAL'),
    ]),
    warning_codes: z.array(z.string()),
  })
  .strict();
export const ApprovalEffectSchema = z.object({ code: z.string(), detail: z.string() }).strict();
export const ApprovalDetailSchema = z
  .object({
    approval_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    type: z.union([
      z.literal('HOLDOUT_UNLOCK'),
      z.literal('PAPER_DEPLOYMENT'),
      z.literal('PAPER_ALLOCATION_CHANGE'),
      z.literal('RETIRE_PAPER'),
    ]),
    subject: ApprovalSubjectSchema,
    requester: RequesterRefSchema,
    reason: z.string(),
    prerequisites: z.array(ApprovalPrerequisiteSchema),
    risk_summary: RiskSummarySchema,
    effects: z.array(ApprovalEffectSchema),
    status: z.union([
      z.literal('PENDING'),
      z.literal('APPROVED'),
      z.literal('REJECTED'),
      z.literal('STALE'),
      z.literal('CANCELLED'),
    ]),
    requested_at: z.iso.datetime(),
    decided_at: z.iso.datetime().nullable(),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict();
export const ApprovalDecisionRequestSchema = z
  .object({ acknowledged_subject_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')) })
  .strict();
export const ApprovalRejectRequestSchema = z
  .object({
    reason: z.string().min(1).max(4000),
    acknowledged_subject_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict();
export const JobAcceptedSchema = z
  .object({
    job_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    status: z.union([z.literal('QUEUED'), z.literal('RUNNING')]),
    progress: JobProgressSchema,
    resource_ref: z.union([ObjectRefSchema, z.null()]),
    created_at: z.iso.datetime(),
  })
  .strict();
export const ApprovalDecisionResultSchema = z
  .object({
    approval: ApprovalDetailSchema,
    subject_ref: ObjectRefSchema,
    next_job: z.union([JobAcceptedSchema, z.null()]),
  })
  .strict();
export const MemoGenerateRequestSchema = z
  .object({
    strategy_id: z.union([
      z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    strategy_version: z.number().int().min(1),
  })
  .strict();
export const MemoEvidenceLinkSchema = z
  .object({
    experiment_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    provenance: ProvenanceRefSchema,
  })
  .strict();
export const MemoSectionSchema = z
  .object({
    section_key: z.string(),
    title: z.string(),
    content: z.string(),
    evidence_links: z.array(MemoEvidenceLinkSchema),
  })
  .strict();
export const MemoDetailSchema = z
  .object({
    memo_id: z.union([
      z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    strategy: z.intersection(
      VersionRefSchema,
      z
        .object({
          id: z
            .union([
              z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                ),
            ])
            .optional(),
        })
        .passthrough(),
    ),
    status: z.union([z.literal('GENERATING'), z.literal('FINAL'), z.literal('FAILED')]),
    sections: z.array(MemoSectionSchema),
    provenance: z.array(ProvenanceRefSchema),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime(),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const AgentConfigSchema = z
  .object({
    role_key: AgentRoleKeySchema,
    enabled: z.boolean(),
    model_provider: z.string(),
    model_name: z.string(),
    ai_connection_id: z.string(),
    ai_connection_revision: z.number().int().min(1),
    runtime_profile: z.string(),
    tool_timeout_seconds: z.number().int().min(1),
    max_steps_override: z.number().int().min(1).nullable(),
    max_tool_calls_override: z.number().int().min(1).nullable(),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime(),
    updated_at: z.iso.datetime(),
  })
  .strict();
export const AgentConfigListSchema = z.array(AgentConfigSchema);
export const AgentConfigUpdateSchema = z
  .object({
    enabled: z.boolean().optional(),
    runtime_profile: z.string().min(1).max(32).optional(),
    tool_timeout_seconds: z.number().int().min(1).optional(),
    max_steps_override: z.number().int().min(1).nullable().optional(),
    max_tool_calls_override: z.number().int().min(1).nullable().optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length >= 1, {
    message: 'Object requires at least 1 properties',
  });
export const JobResultRefSchema = z
  .object({
    object_type: z.union([
      z.union([
        z.literal('job'),
        z.literal('research'),
        z.literal('conclusion'),
        z.literal('experiment'),
        z.literal('factor'),
        z.literal('strategy_version'),
        z.literal('validation'),
        z.literal('approval'),
        z.literal('paper'),
        z.literal('paper_run'),
        z.literal('review'),
        z.literal('capability'),
        z.literal('snapshot'),
        z.literal('agent_run'),
        z.literal('tool_call'),
        z.literal('memo'),
        z.literal('notification'),
        z.literal('settings'),
        z.literal('provider_connection'),
        z.literal('agent_config'),
        z.literal('event_stream'),
      ]),
      z.null(),
    ]),
    object_id: z.union([
      z.union([
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.union([
          z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.literal('SETTINGS-DEFAULT'),
        z
          .string()
          .regex(
            new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
        z.union([
          z.literal('RESEARCH_DIRECTOR'),
          z.literal('FACTOR_SCIENTIST'),
          z.literal('STRATEGY_SCIENTIST'),
          z.literal('PORTFOLIO_ANALYST'),
          z.literal('RED_TEAM_RESEARCHER'),
          z.literal('PERFORMANCE_ANALYST'),
        ]),
        z.union([
          z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
      ]),
      z.null(),
    ]),
    object_version: z.number().int().min(1).nullable(),
    object_revision: z.number().int().min(1).nullable(),
    artifact_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
  })
  .strict();
export const JobDetailSchema = z
  .object({
    job_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    job_type: z.string(),
    status: z.union([
      z.literal('QUEUED'),
      z.literal('RUNNING'),
      z.literal('WAITING_USER'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('CANCELLED'),
    ]),
    progress: JobProgressSchema,
    error_code: z.union([CanonicalErrorCodeSchema, z.null()]),
    result_ref: z.union([JobResultRefSchema, z.null()]),
    queued_at: z.iso.datetime(),
    started_at: z.iso.datetime().nullable(),
    finished_at: z.iso.datetime().nullable(),
    last_updated_at: z.iso.datetime(),
    revision: z.number().int().min(1),
  })
  .strict();
export const EventTypeSchema = z.union([
  z.literal('job.updated'),
  z.literal('research.created'),
  z.literal('research.updated'),
  z.literal('research.conclusion.created'),
  z.literal('experiment.created'),
  z.literal('experiment.updated'),
  z.literal('factor.updated'),
  z.literal('strategy.created'),
  z.literal('strategy.updated'),
  z.literal('validation.created'),
  z.literal('validation.updated'),
  z.literal('validation.holdout.updated'),
  z.literal('approval.created'),
  z.literal('approval.updated'),
  z.literal('paper.created'),
  z.literal('paper.updated'),
  z.literal('paper.run.updated'),
  z.literal('review.created'),
  z.literal('review.updated'),
  z.literal('data.provider.updated'),
  z.literal('data.capability.updated'),
  z.literal('data.quality.updated'),
  z.literal('agent.run.updated'),
  z.literal('tool.call.updated'),
  z.literal('memo.created'),
  z.literal('memo.updated'),
  z.literal('setup.completed'),
  z.literal('configuration.updated'),
  z.literal('configuration.apply_failed'),
  z.literal('database.connection.updated'),
  z.literal('database.connection.failed'),
  z.literal('notification.created'),
  z.literal('notification.updated'),
  z.literal('system.health.updated'),
  z.literal('system.resync_required'),
]);
export const EventWaitingOnSchema = z
  .object({
    type: z.literal('JOB'),
    job_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
  })
  .strict();
export const EventPayloadSchema = z
  .object({
    status: z.string().nullable().optional(),
    state: z.string().nullable().optional(),
    reason_code: z.union([CanonicalErrorCodeSchema, z.null()]).optional(),
    resync_from_sequence: z.number().int().min(1).nullable().optional(),
    progress_mode: z.union([z.literal('NONE'), z.literal('UNITS'), z.literal(null)]).optional(),
    completed_units: z.number().int().min(0).nullable().optional(),
    total_units: z.number().int().min(1).nullable().optional(),
    current_step_key: z.string().nullable().optional(),
    agent_run_id: z
      .union([
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
    role: z.union([AgentRoleKeySchema, z.null()]).optional(),
    objective: z.string().nullable().optional(),
    research_id: z
      .union([
        z.union([
          z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            ),
        ]),
        z.null(),
      ])
      .optional(),
    object_type: z
      .union([
        z.union([
          z.literal('job'),
          z.literal('research'),
          z.literal('conclusion'),
          z.literal('experiment'),
          z.literal('factor'),
          z.literal('strategy_version'),
          z.literal('validation'),
          z.literal('approval'),
          z.literal('paper'),
          z.literal('paper_run'),
          z.literal('review'),
          z.literal('capability'),
          z.literal('snapshot'),
          z.literal('agent_run'),
          z.literal('tool_call'),
          z.literal('memo'),
          z.literal('notification'),
          z.literal('settings'),
          z.literal('provider_connection'),
          z.literal('agent_config'),
          z.literal('event_stream'),
        ]),
        z.null(),
      ])
      .optional(),
    object_id: z
      .union([
        z.union([
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(39)
              .max(39)
              .regex(
                new RegExp(
                  '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.union([
            z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
          z.literal('SETTINGS-DEFAULT'),
          z
            .string()
            .regex(
              new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            ),
          z.union([
            z.literal('RESEARCH_DIRECTOR'),
            z.literal('FACTOR_SCIENTIST'),
            z.literal('STRATEGY_SCIENTIST'),
            z.literal('PORTFOLIO_ANALYST'),
            z.literal('RED_TEAM_RESEARCHER'),
            z.literal('PERFORMANCE_ANALYST'),
          ]),
          z.union([
            z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              ),
          ]),
        ]),
        z.null(),
      ])
      .optional(),
    object_version: z.number().int().min(1).nullable().optional(),
    object_revision: z.number().int().min(1).nullable().optional(),
    waiting_on: z.union([EventWaitingOnSchema, z.null()]).optional(),
  })
  .strict()
  .superRefine((value, context) => {
    const locatorKeys = ['object_type', 'object_id', 'object_version', 'object_revision'] as const;
    const present = locatorKeys.filter((key) => value[key] !== undefined);
    if (present.length > 0 && present.length !== locatorKeys.length)
      context.addIssue({ code: 'custom', message: 'Event payload locator fields are dependent' });
    if (present.length === locatorKeys.length) {
      if (value.object_type === null) {
        if (
          value.object_id !== null ||
          value.object_version !== null ||
          value.object_revision !== null
        )
          context.addIssue({
            code: 'custom',
            message: 'Null event payload locator must be wholly null',
          });
      } else if (value.object_type !== undefined) {
        const result = EventObjectLocatorSchemas[value.object_type].safeParse(value);
        if (!result.success)
          context.addIssue({ code: 'custom', message: 'Event payload object locator is invalid' });
      }
    }
  });
export const SseEnvelopeSchema = z
  .object({
    schema_version: z.literal(1),
    event_id: z.union([
      z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        ),
    ]),
    sequence: z.number().int().min(1),
    event_type: EventTypeSchema,
    occurred_at: z.iso.datetime(),
    object_type: z.union([
      z.literal('job'),
      z.literal('research'),
      z.literal('conclusion'),
      z.literal('experiment'),
      z.literal('factor'),
      z.literal('strategy_version'),
      z.literal('validation'),
      z.literal('approval'),
      z.literal('paper'),
      z.literal('paper_run'),
      z.literal('review'),
      z.literal('capability'),
      z.literal('snapshot'),
      z.literal('agent_run'),
      z.literal('tool_call'),
      z.literal('memo'),
      z.literal('notification'),
      z.literal('settings'),
      z.literal('provider_connection'),
      z.literal('agent_config'),
      z.literal('event_stream'),
    ]),
    object_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(29).max(29).regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(39)
          .max(39)
          .regex(
            new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.literal('SETTINGS-DEFAULT'),
      z
        .string()
        .regex(new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
      z.union([
        z.literal('RESEARCH_DIRECTOR'),
        z.literal('FACTOR_SCIENTIST'),
        z.literal('STRATEGY_SCIENTIST'),
        z.literal('PORTFOLIO_ANALYST'),
        z.literal('RED_TEAM_RESEARCHER'),
        z.literal('PERFORMANCE_ANALYST'),
      ]),
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
    ]),
    object_version: z.number().int().min(1).nullable(),
    object_revision: z.number().int().min(1).nullable(),
    request_id: z.string().nullable(),
    job_id: z.union([
      z.union([
        z.string().min(30).max(30).regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(40)
          .max(40)
          .regex(
            new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          ),
      ]),
      z.null(),
    ]),
    agent_run_id: z.union([
      z.union([
        z.string().min(31).max(31).regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(41)
          .max(41)
          .regex(
            new RegExp(
              '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.null(),
    ]),
    tool_call_id: z.union([
      z.union([
        z.string().min(32).max(32).regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$')),
        z
          .string()
          .min(42)
          .max(42)
          .regex(
            new RegExp(
              '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            ),
          ),
      ]),
      z.null(),
    ]),
    payload: EventPayloadSchema,
  })
  .strict()
  .superRefine((value, context) => {
    if (EventTypeObjectTypeMap[value.event_type] !== value.object_type)
      context.addIssue({
        code: 'custom',
        path: ['object_type'],
        message: 'Event type and object type must agree',
      });
    if (!EventObjectLocatorSchemas[value.object_type].safeParse(value).success)
      context.addIssue({
        code: 'custom',
        path: ['object_id'],
        message: 'Event object locator is invalid',
      });
  });
