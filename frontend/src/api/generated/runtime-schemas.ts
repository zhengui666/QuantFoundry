// Generated from canonical openapi-v1.yaml. Do not edit.
import { z } from 'zod';

const canonicalJson = (value: unknown): string => {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value && typeof value === 'object') {
    const object = value as Record<string, unknown>;
    return (
      '{' +
      Object.keys(object)
        .sort()
        .map((key) => JSON.stringify(key) + ':' + canonicalJson(object[key]))
        .join(',') +
      '}'
    );
  }
  return JSON.stringify(value);
};

const normalizeCanonicalDecimal = (value: string) => {
  const [integer = '', fraction = ''] = value.split('.');
  const negative = integer.startsWith('-');
  const digits = (negative ? integer.slice(1) : integer).replace(/^0+(?=\d)/, '');
  const trimmedFraction = fraction.replace(/0+$/, '');
  return {
    negative: negative && (digits !== '0' || trimmedFraction !== ''),
    integer: digits,
    fraction: trimmedFraction,
  };
};
const compareCanonicalDecimal = (left: string, right: string) => {
  const a = normalizeCanonicalDecimal(left);
  const b = normalizeCanonicalDecimal(right);
  if (a.negative !== b.negative) return a.negative ? -1 : 1;
  const sign = a.negative ? -1 : 1;
  if (a.integer.length !== b.integer.length) return (a.integer.length - b.integer.length) * sign;
  if (a.integer !== b.integer) return (a.integer < b.integer ? -1 : 1) * sign;
  const width = Math.max(a.fraction.length, b.fraction.length);
  const af = a.fraction.padEnd(width, '0');
  const bf = b.fraction.padEnd(width, '0');
  return (af === bf ? 0 : af < bf ? -1 : 1) * sign;
};
const isCanonicalInteger = (value: string) => !normalizeCanonicalDecimal(value).fraction;
export const ResearchPolicyIdSchema = z
  .string()
  .min(29)
  .max(39)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(29)
        .max(29)
        .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const RiskPolicyIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const CostModelIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const CredentialIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^CRED-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^CRED-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const CapabilityIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const DatasetIdSchema = z
  .string()
  .min(32)
  .max(42)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(32)
        .max(32)
        .regex(new RegExp('^DSSET-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^DSSET-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const SnapshotIdSchema = z
  .string()
  .min(29)
  .max(39)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(29)
        .max(29)
        .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const DataQualityRunIdSchema = z
  .string()
  .min(29)
  .max(39)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(29)
        .max(29)
        .regex(new RegExp('^DQ-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^DQ-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const DataQualityIssueIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^DQI-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^DQI-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ResearchIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const EvidenceIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^EVID-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^EVID-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ConclusionIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ExperimentIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const FactorIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const StrategyIdSchema = z
  .string()
  .min(32)
  .max(42)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(32)
        .max(32)
        .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ValidationIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ExposureIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^HOLD-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^HOLD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const RedTeamRunIdSchema = z
  .string()
  .min(29)
  .max(39)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(29)
        .max(29)
        .regex(new RegExp('^RT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(39)
        .max(39)
        .regex(
          new RegExp('^RT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const PortfolioIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^PORT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^PORT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const MemoIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ApprovalIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const PaperIdSchema = z
  .string()
  .min(32)
  .max(42)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(32)
        .max(32)
        .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const PaperRunIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const PaperOrderIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^PORD-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^PORD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const PaperFillIdSchema = z
  .string()
  .min(32)
  .max(42)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(32)
        .max(32)
        .regex(new RegExp('^PFILL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^PFILL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ReviewIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const AgentRunIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ToolCallIdSchema = z
  .string()
  .min(32)
  .max(42)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(32)
        .max(32)
        .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const JobIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const DomainEventIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const AuditEventIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^AUD-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^AUD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ArtifactIdSchema = z
  .string()
  .min(30)
  .max(40)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(30)
        .max(30)
        .regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(40)
        .max(40)
        .regex(
          new RegExp('^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const NotificationIdSchema = z
  .string()
  .min(32)
  .max(42)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(32)
        .max(32)
        .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(42)
        .max(42)
        .regex(
          new RegExp('^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ProvenanceIdSchema = z
  .string()
  .min(31)
  .max(41)
  .superRefine((value, context) => {
    const matches = [
      z
        .string()
        .min(31)
        .max(31)
        .regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
        .safeParse(value).success,
      z
        .string()
        .min(41)
        .max(41)
        .regex(
          new RegExp('^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        )
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
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
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  research: z
    .object({
      object_id: z
        .string()
        .min(31)
        .max(41)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(31)
              .max(31)
              .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  conclusion: z
    .object({
      object_id: z
        .string()
        .min(31)
        .max(41)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(31)
              .max(31)
              .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  experiment: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  factor: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  strategy_version: z
    .object({
      object_id: z
        .string()
        .min(32)
        .max(42)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(32)
              .max(32)
              .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.number().int().min(1),
      object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
    })
    .passthrough(),
  validation: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  approval: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  paper: z
    .object({
      object_id: z
        .string()
        .min(32)
        .max(42)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(32)
              .max(32)
              .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  paper_run: z
    .object({
      object_id: z
        .string()
        .min(31)
        .max(41)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(31)
              .max(31)
              .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  review: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  capability: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  snapshot: z
    .object({
      object_id: z
        .string()
        .min(29)
        .max(39)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(29)
              .max(29)
              .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(39)
              .max(39)
              .regex(
                new RegExp(
                  '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  agent_run: z
    .object({
      object_id: z
        .string()
        .min(31)
        .max(41)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(31)
              .max(31)
              .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  tool_call: z
    .object({
      object_id: z
        .string()
        .min(32)
        .max(42)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(32)
              .max(32)
              .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  memo: z
    .object({
      object_id: z
        .string()
        .min(31)
        .max(41)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(31)
              .max(31)
              .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(41)
              .max(41)
              .regex(
                new RegExp(
                  '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  notification: z
    .object({
      object_id: z
        .string()
        .min(32)
        .max(42)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(32)
              .max(32)
              .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(42)
              .max(42)
              .regex(
                new RegExp(
                  '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.union([z.number().int().min(1), z.null()]),
      object_revision: z.union([z.number().int().min(1), z.null()]),
    })
    .passthrough(),
  settings: z
    .object({
      object_id: z.literal('SETTINGS-DEFAULT'),
      object_version: z.null().nullable(),
      object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
    })
    .passthrough(),
  provider_connection: z
    .object({
      object_id: z
        .string()
        .regex(new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')),
      object_version: z.null().nullable(),
      object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
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
      object_version: z.null().nullable(),
      object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
    })
    .passthrough(),
  event_stream: z
    .object({
      object_id: z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
      object_version: z.null().nullable(),
      object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'field'), {
    path: ['field'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'code'), {
    path: ['code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'message'), {
    path: ['message'],
    message: 'Required property is missing',
  });
export const ProblemContextSchema = z
  .object({
    object_type: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .union([
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
            ])
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    object_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .unknown()
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(29)
                  .max(39)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(29)
                        .max(29)
                        .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(39)
                        .max(39)
                        .regex(
                          new RegExp(
                            '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z.literal('SETTINGS-DEFAULT').safeParse(value).success,
                z
                  .string()
                  .regex(
                    new RegExp(
                      '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
                z
                  .union([
                    z.literal('RESEARCH_DIRECTOR'),
                    z.literal('FACTOR_SCIENTIST'),
                    z.literal('STRATEGY_SCIENTIST'),
                    z.literal('PORTFOLIO_ANALYST'),
                    z.literal('RED_TEAM_RESEARCHER'),
                    z.literal('PERFORMANCE_ANALYST'),
                  ])
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches === 0)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match at least one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches === 0)
          context.addIssue({
            code: 'custom',
            message: 'Value must match at least one canonical variant',
          });
      })
      .optional(),
    object_version: z.union([z.number().int().min(1), z.null()]).optional(),
    object_revision: z
      .union([
        z.number().int().min(1).refine(Number.isSafeInteger, {
          message: 'Integer must be exactly representable in JavaScript',
        }),
        z.null(),
      ])
      .optional(),
    expected_revision: z.union([z.number().int().min(1), z.null()]).optional(),
    actual_revision: z.union([z.number().int().min(1), z.null()]).optional(),
    approval_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(40)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(30)
                  .max(30)
                  .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(40)
                  .max(40)
                  .regex(
                    new RegExp(
                      '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    validation_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(40)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(30)
                  .max(30)
                  .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(40)
                  .max(40)
                  .regex(
                    new RegExp(
                      '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    retry_after_seconds: z.union([z.number().int().min(1), z.null()]).optional(),
  })
  .strict()
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('job') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('research') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('conclusion') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('experiment') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('factor') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('strategy_version') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.number().int().min(1),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_version'), {
                    path: ['object_version'],
                    message: 'Required property is missing',
                  })
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('validation') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('approval') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('review') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('capability') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('snapshot') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('tool_call') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('memo') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('notification') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('settings') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.literal('SETTINGS-DEFAULT').optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('provider_connection') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .regex(
                        new RegExp(
                          '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_config') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .union([
                        z.literal('RESEARCH_DIRECTOR'),
                        z.literal('FACTOR_SCIENTIST'),
                        z.literal('STRATEGY_SCIENTIST'),
                        z.literal('PORTFOLIO_ANALYST'),
                        z.literal('RED_TEAM_RESEARCHER'),
                        z.literal('PERFORMANCE_ANALYST'),
                      ])
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('event_stream') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_id: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_id'), {
              path: ['object_id'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_type: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('job.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('job').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('research.created'), z.literal('research.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('research').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('research.conclusion.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('conclusion').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('experiment.created'),
                z.literal('experiment.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('experiment').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('factor.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('factor').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('strategy.created'), z.literal('strategy.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('strategy_version').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('validation.created'),
                z.literal('validation.updated'),
                z.literal('validation.holdout.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('validation').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('approval.created'), z.literal('approval.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('approval').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('paper.created'), z.literal('paper.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('paper.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('review.created'), z.literal('review.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('review').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.provider.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.capability.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('capability').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.quality.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('snapshot').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('agent.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('tool.call.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('tool_call').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.union([z.literal('memo.created'), z.literal('memo.updated')]) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('memo').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('setup.completed') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('configuration.updated'),
                z.literal('configuration.apply_failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('database.connection.updated'),
                z.literal('database.connection.failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('notification').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_config').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('system.health.updated'),
                z.literal('system.resync_required'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('event_stream').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_type'))
      for (const key of ['object_id', 'object_version', 'object_revision'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_id'))
      for (const key of ['object_type', 'object_version', 'object_revision'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_version'))
      for (const key of ['object_type', 'object_id', 'object_revision'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_revision'))
      for (const key of ['object_type', 'object_id', 'object_version'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  });
export const ApiProblemSchema = z
  .object({
    type: z.url(),
    title: z.string(),
    status: z.number().int().min(400).max(599),
    code: CanonicalErrorCodeSchema,
    detail: z.union([z.string(), z.null()]),
    instance: z.union([z.string(), z.null()]),
    request_id: z.string(),
    retryable: z.boolean(),
    field_errors: z.array(FieldErrorSchema),
    context: ProblemContextSchema,
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'code'), {
    path: ['code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'instance'), {
    path: ['instance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'request_id'), {
    path: ['request_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'retryable'), {
    path: ['retryable'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'field_errors'), {
    path: ['field_errors'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'context'), {
    path: ['context'],
    message: 'Required property is missing',
  });
export const GeneralAccessKeyLoginRequestSchema = z
  .object({
    key: z
      .string()
      .min(60)
      .max(256)
      .regex(new RegExp('^qfk_gak_[a-z0-9]{16,32}\\.[A-Za-z0-9_-]{43,}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  });
export const GeneralAccessKeyMetadataSchema = z
  .object({
    key_id: z.string().regex(new RegExp('^gak_[a-z0-9]{16,32}$')),
    label: z.string().min(1).max(80),
    masked_hint: z.string().min(3).max(32),
    status: z.union([z.literal('ACTIVE'), z.literal('REVOKED'), z.literal('EXPIRED')]),
    expires_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    last_used_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key_id'), {
    path: ['key_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'label'), {
    path: ['label'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'masked_hint'), {
    path: ['masked_hint'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'expires_at'), {
    path: ['expires_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'last_used_at'), {
    path: ['last_used_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const GeneralAccessKeyListSchema = z
  .object({ items: z.array(GeneralAccessKeyMetadataSchema) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  });
export const GeneralAccessKeyCreateRequestSchema = z
  .object({
    label: z.string().min(1).max(80),
    expires_at: z.union([z.iso.datetime({ offset: true }), z.null()]).optional(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'label'), {
    path: ['label'],
    message: 'Required property is missing',
  });
export const GeneralAccessKeyIssuedSchema = z
  .object({
    key: GeneralAccessKeyMetadataSchema,
    secret: z
      .string()
      .min(60)
      .max(256)
      .regex(new RegExp('^qfk_gak_[a-z0-9]{16,32}\\.[A-Za-z0-9_-]{43,}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'secret'), {
    path: ['secret'],
    message: 'Required property is missing',
  });
export const OwnerSessionViewSchema = z
  .object({
    principal: z.literal('OWNER'),
    auth_method: z.literal('GENERAL_ACCESS_KEY'),
    key_id: z.string().regex(new RegExp('^gak_[a-z0-9]{16,32}$')),
    issued_at: z.iso.datetime({ offset: true }),
    last_seen_at: z.iso.datetime({ offset: true }),
    expires_at: z.iso.datetime({ offset: true }),
    csrf_token: z.string().min(32).max(256),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'principal'), {
    path: ['principal'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'auth_method'), {
    path: ['auth_method'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'key_id'), {
    path: ['key_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'issued_at'), {
    path: ['issued_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'last_seen_at'), {
    path: ['last_seen_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'expires_at'), {
    path: ['expires_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'csrf_token'), {
    path: ['csrf_token'],
    message: 'Required property is missing',
  });
export const SessionBootstrapResponseSchema = z
  .object({ session: OwnerSessionViewSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'session'), {
    path: ['session'],
    message: 'Required property is missing',
  });
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
    safe_range: z.union([z.object({}).passthrough(), z.null()]).optional(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'group'), {
    path: ['group'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'schema_version'), {
    path: ['schema_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'scope'), {
    path: ['scope'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sensitivity'), {
    path: ['sensitivity'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'apply_mode'), {
    path: ['apply_mode'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'consumers'), {
    path: ['consumers'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'dependencies'), {
    path: ['dependencies'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'schema'), {
    path: ['schema'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validator'), {
    path: ['validator'],
    message: 'Required property is missing',
  });
export const ConfigurationCatalogSchema = z
  .object({
    catalog_version: z.string().min(1).max(64),
    entries: z.array(ConfigurationCatalogEntrySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'catalog_version'), {
    path: ['catalog_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'entries'), {
    path: ['entries'],
    message: 'Required property is missing',
  });
export const ConfigurationValueWriteSchema = z
  .object({
    key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
    value: z.unknown().optional(),
    secret: z.unknown().optional(),
  })
  .passthrough()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    const matches = [
      z
        .object({
          key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
          value: z.unknown().superRefine((value, context) => {
            const matches = [
              z.string().safeParse(value).success,
              z.number().safeParse(value).success,
              z.boolean().safeParse(value).success,
              z.object({}).passthrough().safeParse(value).success,
              z.array(z.unknown()).safeParse(value).success,
              z.null().nullable().safeParse(value).success,
            ].filter(Boolean).length;
            if (matches === 0)
              context.addIssue({
                code: 'custom',
                message: 'Value must match at least one canonical variant',
              });
          }),
          secret: z
            .unknown()
            .refine((value) => !z.unknown().safeParse(value).success, {
              message: 'Value must not match the excluded schema',
            })
            .optional(),
        })
        .strict()
        .refine((value) => Object.hasOwn(value, 'key'), {
          path: ['key'],
          message: 'Required property is missing',
        })
        .refine((value) => Object.hasOwn(value, 'value'), {
          path: ['value'],
          message: 'Required property is missing',
        })
        .safeParse(value).success,
      z
        .object({
          key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
          secret: z.string().min(1).max(16384),
          value: z
            .unknown()
            .refine((value) => !z.unknown().safeParse(value).success, {
              message: 'Value must not match the excluded schema',
            })
            .optional(),
        })
        .strict()
        .refine((value) => Object.hasOwn(value, 'key'), {
          path: ['key'],
          message: 'Required property is missing',
        })
        .refine((value) => Object.hasOwn(value, 'secret'), {
          path: ['secret'],
          message: 'Required property is missing',
        })
        .safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const ConfigurationCandidateRequestSchema = z
  .object({
    base_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    values: z.array(ConfigurationValueWriteSchema).min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'base_revision'), {
    path: ['base_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'values'), {
    path: ['values'],
    message: 'Required property is missing',
  });
export const ConfigurationValueViewSchema = z
  .object({
    key: z.string().regex(new RegExp('^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')),
    sensitivity: z.union([z.literal('PUBLIC'), z.literal('MASKED'), z.literal('SECRET')]),
    configured: z.boolean(),
    value: z.unknown().superRefine((value, context) => {
      const matches = [
        z.string().safeParse(value).success,
        z.number().safeParse(value).success,
        z.boolean().safeParse(value).success,
        z.object({}).passthrough().safeParse(value).success,
        z.array(z.unknown()).safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches === 0)
        context.addIssue({
          code: 'custom',
          message: 'Value must match at least one canonical variant',
        });
    }),
    masked_hint: z.union([z.string().max(80), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sensitivity'), {
    path: ['sensitivity'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'configured'), {
    path: ['configured'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value'), {
    path: ['value'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'masked_hint'), {
    path: ['masked_hint'],
    message: 'Required property is missing',
  });
export const ConfigurationCandidateSchema = z
  .object({
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    state: z.union([
      z.literal('CANDIDATE'),
      z.literal('VALIDATED'),
      z.literal('APPLYING'),
      z.literal('FAILED'),
      z.literal('ACTIVE'),
      z.literal('SUPERSEDED'),
    ]),
    base_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    catalog_version: z.string(),
    values: z.array(ConfigurationValueViewSchema),
    snapshot_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'base_revision'), {
    path: ['base_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'catalog_version'), {
    path: ['catalog_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'values'), {
    path: ['values'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'snapshot_sha256'), {
    path: ['snapshot_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ConfigurationValidationResultSchema = z
  .object({
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    status: z.union([z.literal('VALID'), z.literal('INVALID')]),
    errors: z.array(FieldErrorSchema),
    warnings: z.array(FieldErrorSchema),
    validated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'errors'), {
    path: ['errors'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'warnings'), {
    path: ['warnings'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validated_at'), {
    path: ['validated_at'],
    message: 'Required property is missing',
  });
export const ConfigurationActivateRequestSchema = z
  .object({
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  });
export const ConfigurationRollbackRequestSchema = z
  .object({
    source_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'source_revision'), {
    path: ['source_revision'],
    message: 'Required property is missing',
  });
export const DatabaseConnectionCandidateSchema = z
  .object({
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    state: z.union([
      z.literal('CANDIDATE'),
      z.literal('VALIDATED'),
      z.literal('ACTIVE'),
      z.literal('FAILED'),
      z.literal('SUPERSEDED'),
    ]),
    base_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    host: z.string().min(1).max(253),
    port: z.number().int().min(1).max(65535),
    database: z.string().min(1).max(63),
    tls_mode: z.union([z.literal('DISABLED'), z.literal('VERIFY_CA'), z.literal('VERIFY_FULL')]),
    username_masked: z.string().min(1).max(80),
    password_configured: z.boolean(),
    client_key_configured: z.boolean(),
    pool_profile: z.union([z.string().max(64), z.null()]).optional(),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'base_revision'), {
    path: ['base_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'host'), {
    path: ['host'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'port'), {
    path: ['port'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'database'), {
    path: ['database'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tls_mode'), {
    path: ['tls_mode'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'username_masked'), {
    path: ['username_masked'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'password_configured'), {
    path: ['password_configured'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'client_key_configured'), {
    path: ['client_key_configured'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
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
    active_revision: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    candidate_revision: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    last_known_good_revision: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    active: z.unknown().superRefine((value, context) => {
      const matches = [
        DatabaseConnectionCandidateSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    candidate: z.unknown().superRefine((value, context) => {
      const matches = [
        DatabaseConnectionCandidateSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    domain_operations: z.union([
      z.literal('AVAILABLE'),
      z.literal('READ_ONLY_RECOVERY'),
      z.literal('UNAVAILABLE'),
    ]),
    checked_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'active_revision'), {
    path: ['active_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'candidate_revision'), {
    path: ['candidate_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'last_known_good_revision'), {
    path: ['last_known_good_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'active'), {
    path: ['active'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'candidate'), {
    path: ['candidate'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'domain_operations'), {
    path: ['domain_operations'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checked_at'), {
    path: ['checked_at'],
    message: 'Required property is missing',
  });
export const DatabaseConnectionCandidateRequestSchema = z
  .object({
    base_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
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
        username: z.string().min(1).max(128).optional(),
        password: z.string().min(1).max(4096).optional(),
        client_key_pem: z.string().min(1).max(16384).optional(),
        ca_certificate_pem: z.string().min(1).max(16384).optional(),
        pool_profile: z.union([z.string().max(64), z.null()]).optional(),
      })
      .strict()
      .refine((value) => Object.hasOwn(value, 'host'), {
        path: ['host'],
        message: 'Required property is missing',
      })
      .refine((value) => Object.hasOwn(value, 'port'), {
        path: ['port'],
        message: 'Required property is missing',
      })
      .refine((value) => Object.hasOwn(value, 'database'), {
        path: ['database'],
        message: 'Required property is missing',
      })
      .refine((value) => Object.hasOwn(value, 'tls_mode'), {
        path: ['tls_mode'],
        message: 'Required property is missing',
      }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'base_revision'), {
    path: ['base_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'connection'), {
    path: ['connection'],
    message: 'Required property is missing',
  });
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'name'), {
    path: ['name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  });
export const DatabaseConnectionValidationResultSchema = z
  .object({
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    status: z.union([z.literal('VALID'), z.literal('INVALID')]),
    checks: z.array(DatabaseConnectionCheckSchema).min(1),
    validated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checks'), {
    path: ['checks'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validated_at'), {
    path: ['validated_at'],
    message: 'Required property is missing',
  });
export const SetupStatusSchema = z
  .object({
    completed: z.boolean(),
    owner_session_ready: z.boolean(),
    ai_provider_configured: z.boolean(),
    ai_connection_id: z.union([z.string(), z.null()]),
    data_provider_configured: z.boolean(),
    research_policy_active: z.boolean(),
    research_policy_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(29)
          .max(39)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(29)
                .max(29)
                .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(39)
                .max(39)
                .regex(
                  new RegExp(
                    '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    risk_policy_active: z.boolean(),
    risk_policy_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    cost_model_active: z.boolean(),
    cost_model_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    fallback_step: z.union([
      z.literal('AI_PROVIDER'),
      z.literal('RESEARCH_DEFAULTS'),
      z.literal('RESEARCH_CONSTITUTION'),
      z.literal(null),
    ]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'completed'), {
    path: ['completed'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'owner_session_ready'), {
    path: ['owner_session_ready'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'ai_provider_configured'), {
    path: ['ai_provider_configured'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'ai_connection_id'), {
    path: ['ai_connection_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_provider_configured'), {
    path: ['data_provider_configured'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_policy_active'), {
    path: ['research_policy_active'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_policy_id'), {
    path: ['research_policy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'risk_policy_active'), {
    path: ['risk_policy_active'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'risk_policy_id'), {
    path: ['risk_policy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_active'), {
    path: ['cost_model_active'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'fallback_step'), {
    path: ['fallback_step'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ ai_provider_configured: z.literal(true) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'ai_provider_configured'), {
              path: ['ai_provider_configured'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ ai_connection_id: z.string().min(1).optional() }).passthrough()
              : z.object({ ai_connection_id: z.null().nullable().optional() }).passthrough()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ research_policy_active: z.literal(true) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'research_policy_active'), {
              path: ['research_policy_active'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    research_policy_id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.object({ research_policy_id: z.null().nullable().optional() }).passthrough()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ risk_policy_active: z.literal(true) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'risk_policy_active'), {
              path: ['risk_policy_active'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    risk_policy_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.object({ risk_policy_id: z.null().nullable().optional() }).passthrough()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ cost_model_active: z.literal(true) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'cost_model_active'), {
              path: ['cost_model_active'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    cost_model_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.object({ cost_model_id: z.null().nullable().optional() }).passthrough()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ ai_provider_configured: z.literal(false) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'ai_provider_configured'), {
              path: ['ai_provider_configured'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ fallback_step: z.literal('AI_PROVIDER').optional() }).passthrough()
              : z.unknown().superRefine((value, context) => {
                  const conditional = z
                    .object({ cost_model_active: z.literal(false) })
                    .passthrough()
                    .refine((value) => Object.hasOwn(value, 'cost_model_active'), {
                      path: ['cost_model_active'],
                      message: 'Required property is missing',
                    })
                    .safeParse(value).success;
                  const result = (
                    conditional
                      ? z
                          .object({ fallback_step: z.literal('RESEARCH_DEFAULTS').optional() })
                          .passthrough()
                      : z.unknown().superRefine((value, context) => {
                          const conditional = z
                            .unknown()
                            .superRefine((value, context) => {
                              const matches = [
                                z
                                  .object({ research_policy_active: z.literal(false) })
                                  .passthrough()
                                  .refine(
                                    (value) => Object.hasOwn(value, 'research_policy_active'),
                                    {
                                      path: ['research_policy_active'],
                                      message: 'Required property is missing',
                                    },
                                  )
                                  .safeParse(value).success,
                                z
                                  .object({ risk_policy_active: z.literal(false) })
                                  .passthrough()
                                  .refine((value) => Object.hasOwn(value, 'risk_policy_active'), {
                                    path: ['risk_policy_active'],
                                    message: 'Required property is missing',
                                  })
                                  .safeParse(value).success,
                              ].filter(Boolean).length;
                              if (matches === 0)
                                context.addIssue({
                                  code: 'custom',
                                  message: 'Value must match at least one canonical variant',
                                });
                            })
                            .safeParse(value).success;
                          const result = (
                            conditional
                              ? z
                                  .object({
                                    fallback_step: z.literal('RESEARCH_CONSTITUTION').optional(),
                                  })
                                  .passthrough()
                              : z
                                  .object({ fallback_step: z.null().nullable().optional() })
                                  .passthrough()
                          ).safeParse(value);
                          if (!result.success)
                            for (const issue of result.error.issues)
                              context.addIssue({
                                code: 'custom',
                                path: issue.path as (string | number)[],
                                message: issue.message,
                              });
                        })
                  ).safeParse(value);
                  if (!result.success)
                    for (const issue of result.error.issues)
                      context.addIssue({
                        code: 'custom',
                        path: issue.path as (string | number)[],
                        message: issue.message,
                      });
                })
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ completed: z.literal(true) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'completed'), {
              path: ['completed'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    owner_session_ready: z.literal(true).optional(),
                    ai_provider_configured: z.literal(true).optional(),
                    ai_connection_id: z.string().min(1).optional(),
                    research_policy_active: z.literal(true).optional(),
                    research_policy_id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    risk_policy_active: z.literal(true).optional(),
                    risk_policy_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    cost_model_active: z.literal(true).optional(),
                    cost_model_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    fallback_step: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  })
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'model_name'), {
    path: ['model_name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'connection_test_supported'), {
    path: ['connection_test_supported'],
    message: 'Required property is missing',
  });
export const DateCoverageSchema = z
  .object({ start: z.union([z.iso.date(), z.null()]), end: z.union([z.iso.date(), z.null()]) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'start'), {
    path: ['start'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'end'), {
    path: ['end'],
    message: 'Required property is missing',
  });
export const PointInTimeCapabilitySchema = z
  .object({
    supported: z.union([z.boolean(), z.null()]),
    available_from: z.union([z.iso.date(), z.null()]),
    semantics: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'supported'), {
    path: ['supported'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'available_from'), {
    path: ['available_from'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'semantics'), {
    path: ['semantics'],
    message: 'Required property is missing',
  });
export const CapabilityLimitationSchema = z
  .object({ code: z.string(), detail: z.string() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'code'), {
    path: ['code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  });
export const DataCapabilitySchema = z
  .object({
    capability_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    checked_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'capability_id'), {
    path: ['capability_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provider_id'), {
    path: ['provider_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'capability_key'), {
    path: ['capability_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'asset_classes'), {
    path: ['asset_classes'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'frequencies'), {
    path: ['frequencies'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'coverage'), {
    path: ['coverage'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'point_in_time'), {
    path: ['point_in_time'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'fields'), {
    path: ['fields'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'limitations'), {
    path: ['limitations'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checked_at'), {
    path: ['checked_at'],
    message: 'Required property is missing',
  });
export const SetupProviderCapabilitySchema = z
  .object({
    provider_id: z.string(),
    display_name: z.string(),
    kind: SetupProviderKindSchema,
    connection_test_supported: z.literal(true),
    models: z.array(SetupModelCapabilitySchema),
    data_capabilities: z.array(DataCapabilitySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'provider_id'), {
    path: ['provider_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'display_name'), {
    path: ['display_name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'connection_test_supported'), {
    path: ['connection_test_supported'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'models'), {
    path: ['models'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_capabilities'), {
    path: ['data_capabilities'],
    message: 'Required property is missing',
  });
export const SetupCapabilityCatalogSchema = z
  .object({
    providers: z.array(SetupProviderCapabilitySchema),
    server_checked_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'providers'), {
    path: ['providers'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'server_checked_at'), {
    path: ['server_checked_at'],
    message: 'Required property is missing',
  });
export const LiveConnectorValidationRequestSchema = z
  .object({
    connection_id: z.string().min(1).max(80).regex(new RegExp('^[A-Za-z0-9._-]+$')),
    endpoint: z.url().min(1).max(2048).regex(new RegExp('^https://')),
    key_id: z.string().min(1).max(160),
    credential: z.string().min(1).max(16384),
    expected_account_id: z.union([z.string().min(1).max(160), z.null()]).optional(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'connection_id'), {
    path: ['connection_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'endpoint'), {
    path: ['endpoint'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'key_id'), {
    path: ['key_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'credential'), {
    path: ['credential'],
    message: 'Required property is missing',
  });
export const LiveConnectorValidationResultSchema = z
  .object({
    connection_id: z.string().min(1).max(80),
    state: z.union([z.literal('SUCCESS'), z.literal('FAILED')]),
    error_code: z.union([z.string(), z.null()]),
    connector_id: z.union([z.string(), z.null()]),
    protocol_version: z.union([z.string(), z.null()]),
    capabilities_hash: z.union([z.string().regex(new RegExp('^[0-9a-f]{64}$')), z.null()]),
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
    checked_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'connection_id'), {
    path: ['connection_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'error_code'), {
    path: ['error_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'connector_id'), {
    path: ['connector_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'protocol_version'), {
    path: ['protocol_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'capabilities_hash'), {
    path: ['capabilities_hash'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'account_ids'), {
    path: ['account_ids'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'assets'), {
    path: ['assets'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checked_at'), {
    path: ['checked_at'],
    message: 'Required property is missing',
  });
export const SetupProviderConnectionValidationRequestSchema = z
  .object({
    provider_id: z.string(),
    kind: SetupProviderKindSchema,
    model_name: z.union([z.string(), z.null()]).optional(),
    credential: z.string().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'provider_id'), {
    path: ['provider_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'credential'), {
    path: ['credential'],
    message: 'Required property is missing',
  });
export const SetupProviderConnectionValidationSuccessSchema = z
  .object({
    connection_id: z.string().min(1),
    provider_id: z.string(),
    kind: SetupProviderKindSchema,
    state: z.literal('SUCCESS'),
    detail: z.union([z.string(), z.null()]),
    data_capabilities: z.array(DataCapabilitySchema),
    checked_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'connection_id'), {
    path: ['connection_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provider_id'), {
    path: ['provider_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_capabilities'), {
    path: ['data_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checked_at'), {
    path: ['checked_at'],
    message: 'Required property is missing',
  });
export const SetupProviderConnectionValidationFailureSchema = z
  .object({
    provider_id: z.string(),
    kind: SetupProviderKindSchema,
    state: z.literal('FAILED'),
    detail: z.string().min(1),
    error_code: CanonicalErrorCodeSchema,
    data_capabilities: z.array(DataCapabilitySchema),
    checked_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'provider_id'), {
    path: ['provider_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'error_code'), {
    path: ['error_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_capabilities'), {
    path: ['data_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checked_at'), {
    path: ['checked_at'],
    message: 'Required property is missing',
  });
export const SetupProviderConnectionValidationResultSchema = z
  .unknown()
  .superRefine((value, context) => {
    const matches = [
      SetupProviderConnectionValidationSuccessSchema.safeParse(value).success,
      SetupProviderConnectionValidationFailureSchema.safeParse(value).success,
    ].filter(Boolean).length;
    if (matches !== 1)
      context.addIssue({
        code: 'custom',
        message: 'Value must match exactly one canonical variant',
      });
  });
export const SetupCompleteRequestSchema = z
  .object({
    configuration_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'configuration_revision'), {
    path: ['configuration_revision'],
    message: 'Required property is missing',
  });
export const ConfigurationConsumerStateSchema = z
  .object({
    consumer: z.string().min(1).max(80),
    desired_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    applied_revision: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    ack: z.union([z.literal('PENDING'), z.literal('ACKED'), z.literal('FAILED')]),
    error_code: z.unknown().superRefine((value, context) => {
      const matches = [
        CanonicalErrorCodeSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    heartbeat_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'consumer'), {
    path: ['consumer'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'desired_revision'), {
    path: ['desired_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'applied_revision'), {
    path: ['applied_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'ack'), {
    path: ['ack'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'error_code'), {
    path: ['error_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'heartbeat_at'), {
    path: ['heartbeat_at'],
    message: 'Required property is missing',
  });
export const ConfigurationActiveSchema = z
  .object({
    active_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    last_known_good_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    catalog_version: z.string(),
    values: z.array(ConfigurationValueViewSchema),
    snapshot_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    consumer_states: z.array(ConfigurationConsumerStateSchema),
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'active_revision'), {
    path: ['active_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'last_known_good_revision'), {
    path: ['last_known_good_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'catalog_version'), {
    path: ['catalog_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'values'), {
    path: ['values'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'snapshot_sha256'), {
    path: ['snapshot_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'consumer_states'), {
    path: ['consumer_states'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const SettingsDetailSchema = ConfigurationActiveSchema.superRefine((value, context) => {
  for (const result of [ConfigurationActiveSchema.safeParse(value)]) {
    if (!result.success) {
      for (const issue of result.error.issues)
        context.addIssue({
          code: 'custom',
          path: issue.path as (string | number)[],
          message: issue.message,
        });
    }
  }
});
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
    id: z.unknown(),
    version: z.union([z.number().int().min(1), z.null()]),
    revision: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    const schema = PublicIdSchemas[value.type as keyof typeof PublicIdSchemas];
    if (schema && !schema.safeParse(value.id).success)
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
    reason_code: z.unknown().superRefine((value, context) => {
      const matches = [
        CanonicalErrorCodeSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    reason_detail: z.union([z.string(), z.null()]),
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'action'), {
    path: ['action'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'visibility'), {
    path: ['visibility'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'allowed'), {
    path: ['allowed'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reason_code'), {
    path: ['reason_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reason_detail'), {
    path: ['reason_detail'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'requires_confirmation'), {
    path: ['requires_confirmation'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'idempotency_required'), {
    path: ['idempotency_required'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'if_match_required'), {
    path: ['if_match_required'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_mode'), {
    path: ['result_mode'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'danger_level'), {
    path: ['danger_level'],
    message: 'Required property is missing',
  });
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
    reason_code: z.unknown().superRefine((value, context) => {
      const matches = [
        CanonicalErrorCodeSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'attention_id'), {
    path: ['attention_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'severity'), {
    path: ['severity'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object'), {
    path: ['object'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title_key'), {
    path: ['title_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'summary'), {
    path: ['summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reason_code'), {
    path: ['reason_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  });
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
    completed_units: z.union([
      z.number().int().min(0).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    total_units: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    unit: z.union([z.string(), z.null()]),
    percent: z.union([z.number().min(0).max(100), z.null()]),
    current_step_key: z.union([z.string(), z.null()]),
    current_step_label: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'mode'), {
    path: ['mode'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'completed_units'), {
    path: ['completed_units'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'total_units'), {
    path: ['total_units'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'unit'), {
    path: ['unit'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'percent'), {
    path: ['percent'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_step_key'), {
    path: ['current_step_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_step_label'), {
    path: ['current_step_label'],
    message: 'Required property is missing',
  });
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
    agent_run_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'role'), {
    path: ['role'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'agent_run_id'), {
    path: ['agent_run_id'],
    message: 'Required property is missing',
  });
export const OverviewActiveResearchItemSchema = z
  .object({
    research_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    current_agent: z.unknown().superRefine((value, context) => {
      const matches = [
        OverviewCurrentAgentSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    action_capabilities: z.array(ActionCapabilitySchema),
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'research_id'), {
    path: ['research_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_status'), {
    path: ['evidence_status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'progress'), {
    path: ['progress'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_agent'), {
    path: ['current_agent'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const OverviewStrategyPipelineSchema = z
  .object({
    candidate: z.number().int().min(0),
    frozen: z.number().int().min(0),
    validating: z.number().int().min(0),
    validated: z.number().int().min(0),
    paper: z.number().int().min(0),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'candidate'), {
    path: ['candidate'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'frozen'), {
    path: ['frozen'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validating'), {
    path: ['validating'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validated'), {
    path: ['validated'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'paper'), {
    path: ['paper'],
    message: 'Required property is missing',
  });
export const ProvenanceRefSchema = z
  .object({
    provenance_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'provenance_id'), {
    path: ['provenance_id'],
    message: 'Required property is missing',
  });
export const OverviewPaperSummarySchema = z
  .object({
    active_count: z.number().int().min(0),
    total_nav: z.union([z.string(), z.null()]),
    currency: z.string().regex(new RegExp('^[A-Z]{3}$')),
    daily_return: z.union([z.string(), z.null()]),
    mtd_return: z.union([z.string(), z.null()]),
    since_start_return: z.union([z.string(), z.null()]),
    benchmark_since_start_return: z.union([z.string(), z.null()]),
    as_of_date: z.union([z.iso.date(), z.null()]),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'active_count'), {
    path: ['active_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'total_nav'), {
    path: ['total_nav'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'currency'), {
    path: ['currency'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'daily_return'), {
    path: ['daily_return'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'mtd_return'), {
    path: ['mtd_return'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'since_start_return'), {
    path: ['since_start_return'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'benchmark_since_start_return'), {
    path: ['benchmark_since_start_return'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'as_of_date'), {
    path: ['as_of_date'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  });
export const ChartXAxisSchema = z
  .object({
    kind: z.union([z.literal('TIME'), z.literal('CATEGORY'), z.literal('NUMERIC')]),
    timezone: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'timezone'), {
    path: ['timezone'],
    message: 'Required property is missing',
  });
export const ChartValueFormatSchema = z
  .object({
    kind: z.union([
      z.literal('DECIMAL'),
      z.literal('PERCENT'),
      z.literal('BPS'),
      z.literal('CURRENCY'),
      z.literal('INTEGER'),
    ]),
    precision: z.union([z.number().int().min(0).max(18), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'precision'), {
    path: ['precision'],
    message: 'Required property is missing',
  });
export const ChartPointSchema = z
  .object({
    x: z.unknown().superRefine((value, context) => {
      const matches = [
        z.string().safeParse(value).success,
        z.number().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    y: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'x'), {
    path: ['x'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'y'), {
    path: ['y'],
    message: 'Required property is missing',
  });
export const ChartSeriesSchema = z
  .object({
    series_id: z.string(),
    series_key: z.string(),
    display_label: z.string(),
    unit: z.string(),
    value_format: ChartValueFormatSchema,
    points: z.array(ChartPointSchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'series_id'), {
    path: ['series_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'series_key'), {
    path: ['series_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'display_label'), {
    path: ['display_label'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'unit'), {
    path: ['unit'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value_format'), {
    path: ['value_format'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'points'), {
    path: ['points'],
    message: 'Required property is missing',
  });
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'period_type'), {
    path: ['period_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'start'), {
    path: ['start'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'end'), {
    path: ['end'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  });
export const ChartAssumptionSchema = z
  .object({ key: z.string(), value: z.string(), unit: z.union([z.string(), z.null()]) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value'), {
    path: ['value'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'unit'), {
    path: ['unit'],
    message: 'Required property is missing',
  });
export const EquityCurveSummaryParamsSchema = z
  .object({
    ending_nav: z.union([z.string(), z.null()]),
    benchmark_ending_nav: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'ending_nav'), {
    path: ['ending_nav'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'benchmark_ending_nav'), {
    path: ['benchmark_ending_nav'],
    message: 'Required property is missing',
  });
export const ChartSummarySchema = z
  .object({
    template_key: z.literal('chart.equity_curve.summary'),
    params: EquityCurveSummaryParamsSchema,
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'template_key'), {
    path: ['template_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'params'), {
    path: ['params'],
    message: 'Required property is missing',
  });
export const ChartDownsamplingSchema = z
  .object({
    applied: z.boolean(),
    source_points: z.number().int().min(0),
    returned_points: z.number().int().min(0),
    method: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'applied'), {
    path: ['applied'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_points'), {
    path: ['source_points'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'returned_points'), {
    path: ['returned_points'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'method'), {
    path: ['method'],
    message: 'Required property is missing',
  });
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
    generated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'schema_version'), {
    path: ['schema_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'chart_id'), {
    path: ['chart_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'chart_type'), {
    path: ['chart_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'metric_key'), {
    path: ['metric_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'x_axis'), {
    path: ['x_axis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'series'), {
    path: ['series'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'period_markers'), {
    path: ['period_markers'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'assumptions'), {
    path: ['assumptions'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'summary'), {
    path: ['summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'downsampling'), {
    path: ['downsampling'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'generated_at'), {
    path: ['generated_at'],
    message: 'Required property is missing',
  });
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
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'finding_id'), {
    path: ['finding_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_status'), {
    path: ['evidence_status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'finding'), {
    path: ['finding'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research'), {
    path: ['research'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const OverviewAgentActivityItemSchema = z
  .object({
    agent_run_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    decision_summary: z.union([z.string(), z.null()]),
    next_action: z.union([z.string(), z.null()]),
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'agent_run_id'), {
    path: ['agent_run_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'role'), {
    path: ['role'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'decision_summary'), {
    path: ['decision_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'next_action'), {
    path: ['next_action'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
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
    checked_at: z.iso.datetime({ offset: true }),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'blocker_count'), {
    path: ['blocker_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'warning_count'), {
    path: ['warning_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'checked_at'), {
    path: ['checked_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  });
export const OverviewReadModelSchema = z
  .object({
    as_of: z.iso.datetime({ offset: true }),
    revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    needs_attention: z.array(OverviewAttentionItemSchema),
    active_research: z.array(OverviewActiveResearchItemSchema),
    strategy_pipeline: OverviewStrategyPipelineSchema,
    paper_summary: OverviewPaperSummarySchema,
    paper_performance_chart: z.unknown().superRefine((value, context) => {
      const matches = [
        ChartAggregateSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    recent_findings: z.array(OverviewRecentFindingSchema),
    agent_activity: z.array(OverviewAgentActivityItemSchema),
    data_health: OverviewDataHealthSchema,
    provenance: z.array(ProvenanceRefSchema),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'as_of'), {
    path: ['as_of'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'needs_attention'), {
    path: ['needs_attention'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'active_research'), {
    path: ['active_research'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy_pipeline'), {
    path: ['strategy_pipeline'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'paper_summary'), {
    path: ['paper_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'paper_performance_chart'), {
    path: ['paper_performance_chart'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'recent_findings'), {
    path: ['recent_findings'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'agent_activity'), {
    path: ['agent_activity'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_health'), {
    path: ['data_health'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  });
export const DataCapabilityListSchema = z.array(DataCapabilitySchema);
export const ResearchSummarySchema = z
  .object({
    research_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'research_id'), {
    path: ['research_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_status'), {
    path: ['evidence_status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_revision_no'), {
    path: ['current_revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const PageInfoSchema = z
  .object({ next_cursor: z.union([z.string(), z.null()]), has_more: z.boolean() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'next_cursor'), {
    path: ['next_cursor'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'has_more'), {
    path: ['has_more'],
    message: 'Required property is missing',
  });
export const ResearchPageSchema = z
  .object({ items: z.array(ResearchSummarySchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
export const ResearchCreateRequestSchema = z
  .object({
    title: z.string().min(1).max(256),
    original_user_prompt: z.string().min(1),
    research_policy_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(39)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(29)
                  .max(29)
                  .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(39)
                  .max(39)
                  .regex(
                    new RegExp(
                      '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'original_user_prompt'), {
    path: ['original_user_prompt'],
    message: 'Required property is missing',
  });
export const ResearchStartRequestSchema = z
  .object({
    research_revision_no: z.number().int().min(1),
    capability_evaluation_confirmed: z.literal(true),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'research_revision_no'), {
    path: ['research_revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'capability_evaluation_confirmed'), {
    path: ['capability_evaluation_confirmed'],
    message: 'Required property is missing',
  });
export const UniverseSpecSchema = z
  .object({
    asset_class: z.string(),
    symbols: z.array(z.string()),
    universe_id: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'asset_class'), {
    path: ['asset_class'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'symbols'), {
    path: ['symbols'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'universe_id'), {
    path: ['universe_id'],
    message: 'Required property is missing',
  });
export const DateRangeSchema = z
  .object({ start: z.iso.date(), end: z.iso.date() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'start'), {
    path: ['start'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'end'), {
    path: ['end'],
    message: 'Required property is missing',
  });
export const ResearchBriefReadModelSchema = z
  .object({
    revision_no: z.number().int().min(1),
    question: z.string(),
    hypothesis: z.union([z.string(), z.null()]),
    economic_rationale: z.union([z.string(), z.null()]),
    supporting_evidence_definition: z.union([z.string(), z.null()]),
    disconfirming_evidence_definition: z.union([z.string(), z.null()]),
    universe: UniverseSpecSchema,
    benchmark: z.string(),
    period: DateRangeSchema,
    frequency: z.literal('DAILY'),
    content_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'revision_no'), {
    path: ['revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'question'), {
    path: ['question'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'hypothesis'), {
    path: ['hypothesis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'economic_rationale'), {
    path: ['economic_rationale'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'supporting_evidence_definition'), {
    path: ['supporting_evidence_definition'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'disconfirming_evidence_definition'), {
    path: ['disconfirming_evidence_definition'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'universe'), {
    path: ['universe'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'benchmark'), {
    path: ['benchmark'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'period'), {
    path: ['period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'frequency'), {
    path: ['frequency'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'content_sha256'), {
    path: ['content_sha256'],
    message: 'Required property is missing',
  });
export const ResearchConclusionReadModelSchema = z
  .object({
    conclusion_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    recommendation: z.union([z.string(), z.null()]),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'conclusion_id'), {
    path: ['conclusion_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_status'), {
    path: ['evidence_status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'summary'), {
    path: ['summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_refs'), {
    path: ['evidence_refs'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'uncertainties'), {
    path: ['uncertainties'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'recommendation'), {
    path: ['recommendation'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ResearchPlanNodeReadModelSchema = z
  .object({
    node_key: z.string(),
    title: z.string(),
    owner_agent_role: z.union([z.string(), z.null()]),
    status: z.union([
      z.literal('PENDING'),
      z.literal('RUNNING'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('SKIPPED'),
    ]),
    depends_on: z.array(z.string()),
    objective: z.union([z.string(), z.null()]),
    finding_summary: z.union([z.string(), z.null()]),
    experiment_count: z.number().int().min(0),
    sort_order: z.number().int(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'node_key'), {
    path: ['node_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'owner_agent_role'), {
    path: ['owner_agent_role'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'depends_on'), {
    path: ['depends_on'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'finding_summary'), {
    path: ['finding_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'experiment_count'), {
    path: ['experiment_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sort_order'), {
    path: ['sort_order'],
    message: 'Required property is missing',
  });
export const ResearchEvidenceResultLocatorSchema = z
  .object({
    result_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    metric_key: z.union([z.string(), z.null()]),
    artifact: z.unknown().superRefine((value, context) => {
      const matches = [
        ObjectRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'result_sha256'), {
    path: ['result_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'metric_key'), {
    path: ['metric_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'artifact'), {
    path: ['artifact'],
    message: 'Required property is missing',
  });
export const ResearchEvidenceItemSchema = z
  .object({
    evidence: ObjectRefSchema,
    stance: z.union([z.literal('SUPPORTING'), z.literal('CONTRADICTING'), z.literal('NEUTRAL')]),
    claim: z.string(),
    source_experiment: ObjectRefSchema,
    result_locator: ResearchEvidenceResultLocatorSchema,
    strength: z.union([z.literal('WEAK'), z.literal('MODERATE'), z.literal('STRONG')]),
    limitations: z.union([z.string(), z.null()]),
    is_invalidated: z.boolean(),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'evidence'), {
    path: ['evidence'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'stance'), {
    path: ['stance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'claim'), {
    path: ['claim'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_experiment'), {
    path: ['source_experiment'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_locator'), {
    path: ['result_locator'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strength'), {
    path: ['strength'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'limitations'), {
    path: ['limitations'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'is_invalidated'), {
    path: ['is_invalidated'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const NamedVersionSchema = z
  .object({ name: z.string(), version: z.string() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'name'), {
    path: ['name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  });
export const ResearchCurrentAgentWorkSchema = z
  .object({
    agent_run_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    agent_role: z.string(),
    status: z.union([
      z.literal('QUEUED'),
      z.literal('RUNNING'),
      z.literal('WAITING_USER'),
      z.literal('COMPLETED'),
      z.literal('FAILED'),
      z.literal('CANCELLED'),
    ]),
    objective: z.union([z.string(), z.null()]),
    current_action: z.union([z.string(), z.null()]),
    tool: z.unknown().superRefine((value, context) => {
      const matches = [
        NamedVersionSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    next_action: z.union([z.string(), z.null()]),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'agent_run_id'), {
    path: ['agent_run_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'agent_role'), {
    path: ['agent_role'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_action'), {
    path: ['current_action'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tool'), {
    path: ['tool'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'next_action'), {
    path: ['next_action'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const ResearchOverviewReadModelSchema = z
  .object({
    brief: ResearchBriefReadModelSchema,
    current_conclusion: z.unknown().superRefine((value, context) => {
      const matches = [
        ResearchConclusionReadModelSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    progress: z.array(ResearchPlanNodeReadModelSchema),
    latest_evidence: z.array(ResearchEvidenceItemSchema),
    current_agent_work: z.unknown().superRefine((value, context) => {
      const matches = [
        ResearchCurrentAgentWorkSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'brief'), {
    path: ['brief'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_conclusion'), {
    path: ['current_conclusion'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'progress'), {
    path: ['progress'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'latest_evidence'), {
    path: ['latest_evidence'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_agent_work'), {
    path: ['current_agent_work'],
    message: 'Required property is missing',
  });
export const ResearchPlanReadModelSchema = z
  .object({
    plan_version: z.number().int().min(1),
    source_revision_no: z.number().int().min(1),
    status: z.union([z.literal('ACTIVE'), z.literal('SUPERSEDED')]),
    rationale_summary: z.union([z.string(), z.null()]),
    nodes: z.array(ResearchPlanNodeReadModelSchema),
    content_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'plan_version'), {
    path: ['plan_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_revision_no'), {
    path: ['source_revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'rationale_summary'), {
    path: ['rationale_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'nodes'), {
    path: ['nodes'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'content_sha256'), {
    path: ['content_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ResearchTimelineItemSchema = z
  .object({
    event_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    agent_role: z.union([z.string(), z.null()]),
    objective: z.union([z.string(), z.null()]),
    tool: z.unknown().superRefine((value, context) => {
      const matches = [
        NamedVersionSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    result_summary: z.union([z.string(), z.null()]),
    decision_summary: z.union([z.string(), z.null()]),
    next_action: z.union([z.string(), z.null()]),
    object: z.unknown().superRefine((value, context) => {
      const matches = [
        ObjectRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    occurred_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'event_id'), {
    path: ['event_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'agent_role'), {
    path: ['agent_role'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tool'), {
    path: ['tool'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_summary'), {
    path: ['result_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'decision_summary'), {
    path: ['decision_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'next_action'), {
    path: ['next_action'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object'), {
    path: ['object'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'occurred_at'), {
    path: ['occurred_at'],
    message: 'Required property is missing',
  });
export const ResearchTimelinePageSchema = z
  .object({ items: z.array(ResearchTimelineItemSchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
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
    job_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'experiment'), {
    path: ['experiment'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'experiment_type'), {
    path: ['experiment_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validity_state'), {
    path: ['validity_state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ResearchExperimentPageSchema = z
  .object({ items: z.array(ResearchExperimentItemSchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
export const ResearchEvidencePageSchema = z
  .object({ items: z.array(ResearchEvidenceItemSchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
export const ArtifactReadModelSchema = z
  .object({
    artifact: ObjectRefSchema,
    kind: z.string(),
    media_type: z.string(),
    sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    size_bytes: z.number().int().min(0).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'artifact'), {
    path: ['artifact'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'media_type'), {
    path: ['media_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sha256'), {
    path: ['sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'size_bytes'), {
    path: ['size_bytes'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ArtifactPageSchema = z
  .object({ items: z.array(ArtifactReadModelSchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
export const RequesterRefSchema = z
  .object({
    type: z.union([z.literal('AGENT'), z.literal('SYSTEM'), z.literal('OWNER')]),
    id: z.string(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  });
export const ResearchAuditItemSchema = z
  .object({
    event_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^AUD-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^AUD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    action: z.string(),
    actor: RequesterRefSchema,
    object: ObjectRefSchema,
    request_id: z.string(),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    occurred_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'event_id'), {
    path: ['event_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action'), {
    path: ['action'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'actor'), {
    path: ['actor'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object'), {
    path: ['object'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'request_id'), {
    path: ['request_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'occurred_at'), {
    path: ['occurred_at'],
    message: 'Required property is missing',
  });
export const ResearchAuditPageSchema = z
  .object({ items: z.array(ResearchAuditItemSchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
export const ResearchDetailSchema = z
  .object({
    research_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    title: z.string(),
    original_user_prompt: z.string(),
    normalized_question: z.union([z.string(), z.null()]),
    status: ResearchStatusSchema,
    evidence_status: z.union([
      z.literal('INSUFFICIENT'),
      z.literal('WEAK'),
      z.literal('MIXED'),
      z.literal('SUPPORTIVE'),
      z.literal('STRONG'),
    ]),
    current_revision_no: z.number().int().min(1),
    active_plan_version: z.union([z.number().int().min(1), z.null()]),
    research_policy_id: z
      .string()
      .min(29)
      .max(39)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(29)
            .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    director_agent_version: z.union([z.string(), z.null()]),
    current_agent_run_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    current_job_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    overview: ResearchOverviewReadModelSchema,
    plan: z.unknown().superRefine((value, context) => {
      const matches = [
        ResearchPlanReadModelSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    timeline: ResearchTimelinePageSchema,
    experiments: ResearchExperimentPageSchema,
    evidence: ResearchEvidencePageSchema,
    artifacts: ArtifactPageSchema,
    audit: ResearchAuditPageSchema,
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime({ offset: true }),
    updated_at: z.iso.datetime({ offset: true }),
    completed_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'research_id'), {
    path: ['research_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'original_user_prompt'), {
    path: ['original_user_prompt'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'normalized_question'), {
    path: ['normalized_question'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_status'), {
    path: ['evidence_status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_revision_no'), {
    path: ['current_revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'active_plan_version'), {
    path: ['active_plan_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_policy_id'), {
    path: ['research_policy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'director_agent_version'), {
    path: ['director_agent_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_agent_run_id'), {
    path: ['current_agent_run_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'current_job_id'), {
    path: ['current_job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'overview'), {
    path: ['overview'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'plan'), {
    path: ['plan'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'timeline'), {
    path: ['timeline'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'experiments'), {
    path: ['experiments'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence'), {
    path: ['evidence'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'artifacts'), {
    path: ['artifacts'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'audit'), {
    path: ['audit'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'completed_at'), {
    path: ['completed_at'],
    message: 'Required property is missing',
  });
export const ParameterSchema = z
  .object({ key: z.string(), value: z.string() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value'), {
    path: ['value'],
    message: 'Required property is missing',
  });
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
      .refine((items) => new Set(items.map(canonicalJson)).size === items.length, {
        message: 'Array items must be unique',
      }),
    minimum: z.null().nullable(),
    maximum: z.null().nullable(),
    step: z.null().nullable(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'parameter_key'), {
    path: ['parameter_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value_type'), {
    path: ['value_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'values'), {
    path: ['values'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'minimum'), {
    path: ['minimum'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'maximum'), {
    path: ['maximum'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'step'), {
    path: ['step'],
    message: 'Required property is missing',
  });
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
  .refine((value) => Object.hasOwn(value, 'parameter_key'), {
    path: ['parameter_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value_type'), {
    path: ['value_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'kind'), {
    path: ['kind'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'values'), {
    path: ['values'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'minimum'), {
    path: ['minimum'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'maximum'), {
    path: ['maximum'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'step'), {
    path: ['step'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    if (compareCanonicalDecimal(value.minimum, value.maximum) >= 0)
      context.addIssue({ code: 'custom', message: 'minimum must be less than maximum' });
    if (compareCanonicalDecimal(value.step, '0') <= 0)
      context.addIssue({ code: 'custom', message: 'step must be positive' });
    if (
      value.value_type === 'INTEGER' &&
      ![value.minimum, value.maximum, value.step].every(isCanonicalInteger)
    )
      context.addIssue({
        code: 'custom',
        message: 'INTEGER ranges require integral bounds and step',
      });
  });
export const ExperimentSearchDimensionSchema = z.unknown().superRefine((value, context) => {
  const matches = [
    ExperimentSearchSetDimensionSchema.safeParse(value).success,
    ExperimentSearchRangeDimensionSchema.safeParse(value).success,
  ].filter(Boolean).length;
  if (matches !== 1)
    context.addIssue({ code: 'custom', message: 'Value must match exactly one canonical variant' });
});
export const ExperimentSearchConfigurationSchema = z
  .object({
    method: z.union([z.literal('GRID'), z.literal('RANDOM')]),
    objective_metric_key: z.string(),
    objective_direction: z.union([z.literal('MAXIMIZE'), z.literal('MINIMIZE')]),
    max_evaluations: z.number().int().min(1),
    seed: z.union([
      z.number().int().refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'method'), {
    path: ['method'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective_metric_key'), {
    path: ['objective_metric_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective_direction'), {
    path: ['objective_direction'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'max_evaluations'), {
    path: ['max_evaluations'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'seed'), {
    path: ['seed'],
    message: 'Required property is missing',
  });
export const ExperimentCreateRequestSchema = z
  .object({
    research_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    data_snapshot_id: z
      .string()
      .min(29)
      .max(39)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(29)
            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    factor_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(40)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(30)
                  .max(30)
                  .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(40)
                  .max(40)
                  .regex(
                    new RegExp(
                      '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    factor_version: z.union([z.number().int().min(1), z.null()]).optional(),
    strategy_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(32)
            .max(42)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(32)
                  .max(32)
                  .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(42)
                  .max(42)
                  .regex(
                    new RegExp(
                      '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    strategy_version: z.union([z.number().int().min(1), z.null()]).optional(),
    cost_model_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    parameters: z.array(ParameterSchema),
    search_space: z.array(ExperimentSearchDimensionSchema).optional(),
    search_configuration: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          ExperimentSearchConfigurationSchema.safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    engine_key: z.string(),
    engine_version: z.string(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'research_id'), {
    path: ['research_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_revision_no'), {
    path: ['research_revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'hypothesis'), {
    path: ['hypothesis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'experiment_type'), {
    path: ['experiment_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_snapshot_id'), {
    path: ['data_snapshot_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'parameters'), {
    path: ['parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'engine_key'), {
    path: ['engine_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'engine_version'), {
    path: ['engine_version'],
    message: 'Required property is missing',
  });
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'mode'), {
    path: ['mode'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'execution_overrides'), {
    path: ['execution_overrides'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reason'), {
    path: ['reason'],
    message: 'Required property is missing',
  });
export const ExperimentReproduceRequestSchema = z.unknown().superRefine((value, context) => {
  const matches = [
    ExperimentReproduceExactRequestSchema.safeParse(value).success,
    ExperimentReproduceControlledOverrideRequestSchema.safeParse(value).success,
  ].filter(Boolean).length;
  if (matches !== 1)
    context.addIssue({ code: 'custom', message: 'Value must match exactly one canonical variant' });
});
export const VersionRefSchema = z
  .object({
    id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    version: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  });
export const ExperimentSearchResultNotApplicableSchema = z
  .object({
    state: z.literal('NOT_APPLICABLE'),
    evaluated_count: z.literal(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null().nullable(),
    result_ref: z.null().nullable(),
    failure_code: z.null().nullable(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evaluated_count'), {
    path: ['evaluated_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_parameters'), {
    path: ['selected_parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_metric'), {
    path: ['selected_metric'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_ref'), {
    path: ['result_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_code'), {
    path: ['failure_code'],
    message: 'Required property is missing',
  });
export const ExperimentSearchResultPendingSchema = z
  .object({
    state: z.literal('PENDING'),
    evaluated_count: z.literal(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null().nullable(),
    result_ref: z.null().nullable(),
    failure_code: z.null().nullable(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evaluated_count'), {
    path: ['evaluated_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_parameters'), {
    path: ['selected_parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_metric'), {
    path: ['selected_metric'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_ref'), {
    path: ['result_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_code'), {
    path: ['failure_code'],
    message: 'Required property is missing',
  });
export const ExperimentSearchResultRunningSchema = z
  .object({
    state: z.literal('RUNNING'),
    evaluated_count: z.number().int().min(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null().nullable(),
    result_ref: z.null().nullable(),
    failure_code: z.null().nullable(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evaluated_count'), {
    path: ['evaluated_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_parameters'), {
    path: ['selected_parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_metric'), {
    path: ['selected_metric'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_ref'), {
    path: ['result_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_code'), {
    path: ['failure_code'],
    message: 'Required property is missing',
  });
export const MetricSchema = z
  .object({ key: z.string(), value: z.string(), unit: z.union([z.string(), z.null()]) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'value'), {
    path: ['value'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'unit'), {
    path: ['unit'],
    message: 'Required property is missing',
  });
export const ExperimentSearchResultCompletedSchema = z
  .object({
    state: z.literal('COMPLETED'),
    evaluated_count: z.number().int().min(1),
    selected_parameters: z.array(ParameterSchema).min(1),
    selected_metric: MetricSchema,
    result_ref: ObjectRefSchema,
    failure_code: z.null().nullable(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evaluated_count'), {
    path: ['evaluated_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_parameters'), {
    path: ['selected_parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_metric'), {
    path: ['selected_metric'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_ref'), {
    path: ['result_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_code'), {
    path: ['failure_code'],
    message: 'Required property is missing',
  });
export const ExperimentSearchResultFailedSchema = z
  .object({
    state: z.literal('FAILED'),
    evaluated_count: z.number().int().min(0),
    selected_parameters: z.array(z.unknown()).max(0),
    selected_metric: z.null().nullable(),
    result_ref: z.null().nullable(),
    failure_code: CanonicalErrorCodeSchema,
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evaluated_count'), {
    path: ['evaluated_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_parameters'), {
    path: ['selected_parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'selected_metric'), {
    path: ['selected_metric'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_ref'), {
    path: ['result_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_code'), {
    path: ['failure_code'],
    message: 'Required property is missing',
  });
export const ExperimentSearchResultSchema = z.unknown().superRefine((value, context) => {
  const matches = [
    ExperimentSearchResultNotApplicableSchema.safeParse(value).success,
    ExperimentSearchResultPendingSchema.safeParse(value).success,
    ExperimentSearchResultRunningSchema.safeParse(value).success,
    ExperimentSearchResultCompletedSchema.safeParse(value).success,
    ExperimentSearchResultFailedSchema.safeParse(value).success,
  ].filter(Boolean).length;
  if (matches !== 1)
    context.addIssue({ code: 'custom', message: 'Value must match exactly one canonical variant' });
});
export const CodeVersionSchema = z
  .object({ commit: z.string(), build_id: z.string() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'commit'), {
    path: ['commit'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'build_id'), {
    path: ['build_id'],
    message: 'Required property is missing',
  });
export const PolicyRefSchema = z
  .object({
    type: z.union([z.literal('research_policy'), z.literal('risk_policy')]),
    id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(29)
          .max(39)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(29)
                .max(29)
                .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(39)
                .max(39)
                .regex(
                  new RegExp(
                    '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    version: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ type: z.literal('research_policy') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'type'), {
              path: ['type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ type: z.literal('risk_policy') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'type'), {
              path: ['type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RISK-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RISK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  });
export const VersionedHashRefSchema = z
  .object({
    id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    version: z.number().int().min(1),
    sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sha256'), {
    path: ['sha256'],
    message: 'Required property is missing',
  });
export const ProvenanceSchema = z
  .object({
    provenance_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^PROV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^PROV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    schema_version: z.literal(1),
    experiment_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    source_experiment_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    tool_call_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    data_snapshot_ids: z.array(
      z
        .string()
        .min(29)
        .max(39)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(29)
              .max(29)
              .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(39)
              .max(39)
              .regex(
                new RegExp(
                  '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
    ),
    engine: NamedVersionSchema,
    adapter: z.unknown().superRefine((value, context) => {
      const matches = [
        NamedVersionSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    code: CodeVersionSchema,
    policies: z.array(PolicyRefSchema),
    strategy: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .unknown()
          .superRefine((value, context) => {
            for (const result of [
              VersionedHashRefSchema.safeParse(value),
              z
                .object({
                  id: z
                    .string()
                    .min(32)
                    .max(42)
                    .superRefine((value, context) => {
                      const matches = [
                        z
                          .string()
                          .min(32)
                          .max(32)
                          .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                          .safeParse(value).success,
                        z
                          .string()
                          .min(42)
                          .max(42)
                          .regex(
                            new RegExp(
                              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                            ),
                          )
                          .safeParse(value).success,
                      ].filter(Boolean).length;
                      if (matches !== 1)
                        context.addIssue({
                          code: 'custom',
                          message: 'Value must match exactly one canonical variant',
                        });
                    })
                    .optional(),
                })
                .passthrough()
                .safeParse(value),
            ]) {
              if (!result.success) {
                for (const issue of result.error.issues)
                  context.addIssue({
                    code: 'custom',
                    path: issue.path as (string | number)[],
                    message: issue.message,
                  });
              }
            }
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    factors: z.array(
      z.unknown().superRefine((value, context) => {
        for (const result of [
          VersionedHashRefSchema.safeParse(value),
          z
            .object({
              id: z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .optional(),
            })
            .passthrough()
            .safeParse(value),
        ]) {
          if (!result.success) {
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
          }
        }
      }),
    ),
    cost_model: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .unknown()
          .superRefine((value, context) => {
            for (const result of [
              VersionedHashRefSchema.safeParse(value),
              z
                .object({
                  id: z
                    .string()
                    .min(31)
                    .max(41)
                    .superRefine((value, context) => {
                      const matches = [
                        z
                          .string()
                          .min(31)
                          .max(31)
                          .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                          .safeParse(value).success,
                        z
                          .string()
                          .min(41)
                          .max(41)
                          .regex(
                            new RegExp(
                              '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                            ),
                          )
                          .safeParse(value).success,
                      ].filter(Boolean).length;
                      if (matches !== 1)
                        context.addIssue({
                          code: 'custom',
                          message: 'Value must match exactly one canonical variant',
                        });
                    })
                    .optional(),
                })
                .passthrough()
                .safeParse(value),
            ]) {
              if (!result.success) {
                for (const issue of result.error.issues)
                  context.addIssue({
                    code: 'custom',
                    path: issue.path as (string | number)[],
                    message: issue.message,
                  });
              }
            }
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    parameters_sha256: z.union([z.string().regex(new RegExp('^[0-9a-f]{64}$')), z.null()]),
    input_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    output_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    calculated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'provenance_id'), {
    path: ['provenance_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'schema_version'), {
    path: ['schema_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'experiment_id'), {
    path: ['experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_experiment_id'), {
    path: ['source_experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tool_call_id'), {
    path: ['tool_call_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_snapshot_ids'), {
    path: ['data_snapshot_ids'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'engine'), {
    path: ['engine'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'adapter'), {
    path: ['adapter'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'code'), {
    path: ['code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'policies'), {
    path: ['policies'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy'), {
    path: ['strategy'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'factors'), {
    path: ['factors'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model'), {
    path: ['cost_model'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'parameters_sha256'), {
    path: ['parameters_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'input_sha256'), {
    path: ['input_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'output_sha256'), {
    path: ['output_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'calculated_at'), {
    path: ['calculated_at'],
    message: 'Required property is missing',
  });
export const ExperimentDetailSchema = z
  .object({
    experiment_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    research_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    parent_experiment_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    source_experiment_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    research_revision_no: z.number().int().min(1),
    objective: z.string(),
    hypothesis: z.string(),
    experiment_type: z.string(),
    status: ExperimentStatusSchema,
    validity_state: ExperimentValidityStateSchema,
    data_snapshot_id: z
      .string()
      .min(29)
      .max(39)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(29)
            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    factor_ref: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .unknown()
          .superRefine((value, context) => {
            for (const result of [
              VersionRefSchema.safeParse(value),
              z
                .object({
                  id: z
                    .string()
                    .min(30)
                    .max(40)
                    .superRefine((value, context) => {
                      const matches = [
                        z
                          .string()
                          .min(30)
                          .max(30)
                          .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                          .safeParse(value).success,
                        z
                          .string()
                          .min(40)
                          .max(40)
                          .regex(
                            new RegExp(
                              '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                            ),
                          )
                          .safeParse(value).success,
                      ].filter(Boolean).length;
                      if (matches !== 1)
                        context.addIssue({
                          code: 'custom',
                          message: 'Value must match exactly one canonical variant',
                        });
                    })
                    .optional(),
                })
                .passthrough()
                .safeParse(value),
            ]) {
              if (!result.success) {
                for (const issue of result.error.issues)
                  context.addIssue({
                    code: 'custom',
                    path: issue.path as (string | number)[],
                    message: issue.message,
                  });
              }
            }
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    strategy_ref: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .unknown()
          .superRefine((value, context) => {
            for (const result of [
              VersionRefSchema.safeParse(value),
              z
                .object({
                  id: z
                    .string()
                    .min(32)
                    .max(42)
                    .superRefine((value, context) => {
                      const matches = [
                        z
                          .string()
                          .min(32)
                          .max(32)
                          .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                          .safeParse(value).success,
                        z
                          .string()
                          .min(42)
                          .max(42)
                          .regex(
                            new RegExp(
                              '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                            ),
                          )
                          .safeParse(value).success,
                      ].filter(Boolean).length;
                      if (matches !== 1)
                        context.addIssue({
                          code: 'custom',
                          message: 'Value must match exactly one canonical variant',
                        });
                    })
                    .optional(),
                })
                .passthrough()
                .safeParse(value),
            ]) {
              if (!result.success) {
                for (const issue of result.error.issues)
                  context.addIssue({
                    code: 'custom',
                    path: issue.path as (string | number)[],
                    message: issue.message,
                  });
              }
            }
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    cost_model_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    parameters: z.array(ParameterSchema),
    parameters_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    search_space: z.array(ExperimentSearchDimensionSchema),
    search_configuration: z.unknown().superRefine((value, context) => {
      const matches = [
        ExperimentSearchConfigurationSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    search_result: ExperimentSearchResultSchema,
    metrics: z.array(MetricSchema),
    artifacts: z.array(ArtifactReadModelSchema),
    engine: NamedVersionSchema,
    adapter: z.unknown().superRefine((value, context) => {
      const matches = [
        NamedVersionSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    code_version: z.string(),
    job_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    action_capabilities: z.array(ActionCapabilitySchema),
    started_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    finished_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    created_at: z.iso.datetime({ offset: true }),
    invalidated_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    invalid_reason_code: z.unknown().superRefine((value, context) => {
      const matches = [
        CanonicalErrorCodeSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    invalid_reason_detail: z.union([z.string(), z.null()]),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'experiment_id'), {
    path: ['experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_id'), {
    path: ['research_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'parent_experiment_id'), {
    path: ['parent_experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_experiment_id'), {
    path: ['source_experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_revision_no'), {
    path: ['research_revision_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'objective'), {
    path: ['objective'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'hypothesis'), {
    path: ['hypothesis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'experiment_type'), {
    path: ['experiment_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validity_state'), {
    path: ['validity_state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'data_snapshot_id'), {
    path: ['data_snapshot_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'factor_ref'), {
    path: ['factor_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy_ref'), {
    path: ['strategy_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'parameters'), {
    path: ['parameters'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'parameters_sha256'), {
    path: ['parameters_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'search_space'), {
    path: ['search_space'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'search_configuration'), {
    path: ['search_configuration'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'search_result'), {
    path: ['search_result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'metrics'), {
    path: ['metrics'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'artifacts'), {
    path: ['artifacts'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'engine'), {
    path: ['engine'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'adapter'), {
    path: ['adapter'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'code_version'), {
    path: ['code_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'started_at'), {
    path: ['started_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'finished_at'), {
    path: ['finished_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'invalidated_at'), {
    path: ['invalidated_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'invalid_reason_code'), {
    path: ['invalid_reason_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'invalid_reason_detail'), {
    path: ['invalid_reason_detail'],
    message: 'Required property is missing',
  });
export const StrategySignalSchema = z
  .object({
    factor_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    factor_version: z.number().int().min(1),
    direction: z.union([z.literal('LONG'), z.literal('SHORT')]),
    weight: z.string(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'factor_id'), {
    path: ['factor_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'factor_version'), {
    path: ['factor_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'direction'), {
    path: ['direction'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'weight'), {
    path: ['weight'],
    message: 'Required property is missing',
  });
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'selection_count'), {
    path: ['selection_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'weighting'), {
    path: ['weighting'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'rebalance_frequency'), {
    path: ['rebalance_frequency'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'long_short'), {
    path: ['long_short'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'leverage_limit'), {
    path: ['leverage_limit'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'position_limit'), {
    path: ['position_limit'],
    message: 'Required property is missing',
  });
export const StrategyCreateRequestSchema = z
  .object({
    research_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    name: z.string(),
    thesis: z.string(),
    universe: UniverseSpecSchema,
    signals: z.array(StrategySignalSchema).min(1),
    rules: StrategyRulesSchema,
    cost_model_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    benchmark: z.string(),
    research_period: DateRangeSchema,
    validation_period: DateRangeSchema,
    holdout_period: DateRangeSchema,
    known_failure_modes: z.array(z.string()),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'research_id'), {
    path: ['research_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'name'), {
    path: ['name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'thesis'), {
    path: ['thesis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'universe'), {
    path: ['universe'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'signals'), {
    path: ['signals'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'rules'), {
    path: ['rules'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'benchmark'), {
    path: ['benchmark'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_period'), {
    path: ['research_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validation_period'), {
    path: ['validation_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'holdout_period'), {
    path: ['holdout_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'known_failure_modes'), {
    path: ['known_failure_modes'],
    message: 'Required property is missing',
  });
export const FreezeStrategyRequestSchema = z
  .object({ expected_spec_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'expected_spec_sha256'), {
    path: ['expected_spec_sha256'],
    message: 'Required property is missing',
  });
export const BacktestRequestSchema = z
  .object({
    snapshot_id: z
      .string()
      .min(29)
      .max(39)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(29)
            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    cost_model_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    engine_key: z.string(),
    engine_version: z.string(),
    parameters: z.array(ParameterSchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'snapshot_id'), {
    path: ['snapshot_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'engine_key'), {
    path: ['engine_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'engine_version'), {
    path: ['engine_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'parameters'), {
    path: ['parameters'],
    message: 'Required property is missing',
  });
export const StrategySpecificationSchema = z
  .object({
    thesis: z.string(),
    universe: UniverseSpecSchema,
    signals: z.array(StrategySignalSchema),
    rules: StrategyRulesSchema,
    cost_model_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    benchmark: z.string(),
    research_period: DateRangeSchema,
    validation_period: DateRangeSchema,
    holdout_period: DateRangeSchema,
    known_failure_modes: z.array(z.string()),
    spec_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'thesis'), {
    path: ['thesis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'universe'), {
    path: ['universe'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'signals'), {
    path: ['signals'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'rules'), {
    path: ['rules'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'benchmark'), {
    path: ['benchmark'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_period'), {
    path: ['research_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validation_period'), {
    path: ['validation_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'holdout_period'), {
    path: ['holdout_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'known_failure_modes'), {
    path: ['known_failure_modes'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'spec_sha256'), {
    path: ['spec_sha256'],
    message: 'Required property is missing',
  });
export const StrategyBacktestResultSummarySchema = z
  .object({
    experiment: ObjectRefSchema,
    status: ExperimentStatusSchema,
    validity_state: ExperimentValidityStateSchema,
    result_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    job_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    provenance: ProvenanceRefSchema,
    started_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    finished_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'experiment'), {
    path: ['experiment'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validity_state'), {
    path: ['validity_state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_sha256'), {
    path: ['result_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'started_at'), {
    path: ['started_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'finished_at'), {
    path: ['finished_at'],
    message: 'Required property is missing',
  });
export const StrategyLatestBacktestAvailableSchema = z
  .object({
    state: z.literal('AVAILABLE'),
    result: StrategyBacktestResultSummarySchema,
    metrics: z.array(MetricSchema),
    chart: ChartAggregateSchema,
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result'), {
    path: ['result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'metrics'), {
    path: ['metrics'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'chart'), {
    path: ['chart'],
    message: 'Required property is missing',
  });
export const StrategyLatestBacktestUnavailableSchema = z
  .object({
    state: z.union([z.literal('EMPTY'), z.literal('LOCKED')]),
    result: z.null().nullable(),
    metrics: z.array(z.unknown()).max(0),
    chart: z.null().nullable(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result'), {
    path: ['result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'metrics'), {
    path: ['metrics'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'chart'), {
    path: ['chart'],
    message: 'Required property is missing',
  });
export const StrategyLatestBacktestSchema = z.unknown().superRefine((value, context) => {
  const matches = [
    StrategyLatestBacktestAvailableSchema.safeParse(value).success,
    StrategyLatestBacktestUnavailableSchema.safeParse(value).success,
  ].filter(Boolean).length;
  if (matches !== 1)
    context.addIssue({ code: 'custom', message: 'Value must match exactly one canonical variant' });
});
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'pending'), {
    path: ['pending'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'running'), {
    path: ['running'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'pass'), {
    path: ['pass'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'warn'), {
    path: ['warn'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'fail'), {
    path: ['fail'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'locked'), {
    path: ['locked'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'skipped'), {
    path: ['skipped'],
    message: 'Required property is missing',
  });
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
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    revision: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'validation'), {
    path: ['validation'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result'), {
    path: ['result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'holdout_state'), {
    path: ['holdout_state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'test_counts'), {
    path: ['test_counts'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  });
export const StrategyVersionDetailSchema = z
  .object({
    strategy_id: z
      .string()
      .min(32)
      .max(42)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(32)
            .max(32)
            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    cost_model_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^COST-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^COST-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    benchmark: z.string(),
    research_period: DateRangeSchema,
    validation_period: DateRangeSchema,
    holdout_period: DateRangeSchema,
    known_failure_modes: z.array(z.string()),
    spec_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
    specification: StrategySpecificationSchema,
    latest_backtest: StrategyLatestBacktestSchema,
    validation_summary: z.unknown().superRefine((value, context) => {
      const matches = [
        StrategyValidationSummarySchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    artifacts: z.array(ArtifactReadModelSchema),
    provenance: z.array(ProvenanceRefSchema),
    frozen_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    frozen_by: z.union([z.string(), z.null()]),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'strategy_id'), {
    path: ['strategy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'name'), {
    path: ['name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'lifecycle_state'), {
    path: ['lifecycle_state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'is_frozen'), {
    path: ['is_frozen'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'thesis'), {
    path: ['thesis'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'universe'), {
    path: ['universe'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'signals'), {
    path: ['signals'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'rules'), {
    path: ['rules'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'cost_model_id'), {
    path: ['cost_model_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'benchmark'), {
    path: ['benchmark'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'research_period'), {
    path: ['research_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validation_period'), {
    path: ['validation_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'holdout_period'), {
    path: ['holdout_period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'known_failure_modes'), {
    path: ['known_failure_modes'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'spec_sha256'), {
    path: ['spec_sha256'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'specification'), {
    path: ['specification'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'latest_backtest'), {
    path: ['latest_backtest'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'validation_summary'), {
    path: ['validation_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'artifacts'), {
    path: ['artifacts'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'frozen_at'), {
    path: ['frozen_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'frozen_by'), {
    path: ['frozen_by'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const NewExperimentResourceRefSchema = z
  .object({
    type: z.literal('experiment'),
    id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    version: z.null().nullable(),
    revision: z.literal(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  });
export const ExperimentReproduceAcceptedSchema = z
  .object({
    job_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    status: z.union([z.literal('QUEUED'), z.literal('RUNNING')]),
    progress: JobProgressSchema,
    resource_ref: NewExperimentResourceRefSchema,
    source_experiment_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    source_provenance: ProvenanceRefSchema,
    reproduce_mode: z.union([z.literal('EXACT'), z.literal('CONTROLLED_OVERRIDE')]),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'progress'), {
    path: ['progress'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'resource_ref'), {
    path: ['resource_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_experiment_id'), {
    path: ['source_experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'source_provenance'), {
    path: ['source_provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reproduce_mode'), {
    path: ['reproduce_mode'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ValidationCreateRequestSchema = z
  .object({
    strategy_id: z
      .string()
      .min(32)
      .max(42)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(32)
            .max(32)
            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    strategy_version: z.number().int().min(1),
    policy_id: z
      .string()
      .min(29)
      .max(39)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(29)
            .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    strict_engine_key: z.string(),
    strict_engine_version: z.string(),
    test_suite_version: z.string(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'strategy_id'), {
    path: ['strategy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy_version'), {
    path: ['strategy_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'policy_id'), {
    path: ['policy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strict_engine_key'), {
    path: ['strict_engine_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strict_engine_version'), {
    path: ['strict_engine_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'test_suite_version'), {
    path: ['test_suite_version'],
    message: 'Required property is missing',
  });
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
    calculated_result: z.union([z.string(), z.null()]),
    interpretation: z.union([z.string(), z.null()]),
    failure_code: z.unknown().superRefine((value, context) => {
      const matches = [
        CanonicalErrorCodeSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    failure_detail: z.union([z.string(), z.null()]),
    warning_codes: z.array(z.string()),
    artifact_ids: z.array(
      z
        .string()
        .min(30)
        .max(40)
        .superRefine((value, context) => {
          const matches = [
            z
              .string()
              .min(30)
              .max(30)
              .regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
              .safeParse(value).success,
            z
              .string()
              .min(40)
              .max(40)
              .regex(
                new RegExp(
                  '^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                ),
              )
              .safeParse(value).success,
          ].filter(Boolean).length;
          if (matches !== 1)
            context.addIssue({
              code: 'custom',
              message: 'Value must match exactly one canonical variant',
            });
        }),
    ),
    provenance: z.unknown().superRefine((value, context) => {
      const matches = [
        ProvenanceRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    override_permitted: z.literal(false),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'test_key'), {
    path: ['test_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'attempt_no'), {
    path: ['attempt_no'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'test_version'), {
    path: ['test_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'purpose'), {
    path: ['purpose'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'configuration_summary'), {
    path: ['configuration_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'calculated_result'), {
    path: ['calculated_result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'interpretation'), {
    path: ['interpretation'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_code'), {
    path: ['failure_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failure_detail'), {
    path: ['failure_detail'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'warning_codes'), {
    path: ['warning_codes'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'artifact_ids'), {
    path: ['artifact_ids'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'override_permitted'), {
    path: ['override_permitted'],
    message: 'Required property is missing',
  });
export const ValidationDetailSchema = z
  .object({
    validation_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    strategy: z.unknown().superRefine((value, context) => {
      for (const result of [
        VersionRefSchema.safeParse(value),
        z
          .object({
            id: z
              .string()
              .min(32)
              .max(42)
              .superRefine((value, context) => {
                const matches = [
                  z
                    .string()
                    .min(32)
                    .max(32)
                    .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                    .safeParse(value).success,
                  z
                    .string()
                    .min(42)
                    .max(42)
                    .regex(
                      new RegExp(
                        '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                      ),
                    )
                    .safeParse(value).success,
                ].filter(Boolean).length;
                if (matches !== 1)
                  context.addIssue({
                    code: 'custom',
                    message: 'Value must match exactly one canonical variant',
                  });
              })
              .optional(),
          })
          .passthrough()
          .safeParse(value),
      ]) {
        if (!result.success) {
          for (const issue of result.error.issues)
            context.addIssue({
              code: 'custom',
              path: issue.path as (string | number)[],
              message: issue.message,
            });
        }
      }
    }),
    policy_id: z
      .string()
      .min(29)
      .max(39)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(29)
            .max(29)
            .regex(new RegExp('^RP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(39)
            .max(39)
            .regex(
              new RegExp(
                '^RP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    red_team_run_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(29)
          .max(39)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(29)
                .max(29)
                .regex(new RegExp('^RT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(39)
                .max(39)
                .regex(
                  new RegExp(
                    '^RT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    job_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    started_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    finished_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'validation_id'), {
    path: ['validation_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy'), {
    path: ['strategy'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'policy_id'), {
    path: ['policy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strict_engine'), {
    path: ['strict_engine'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result'), {
    path: ['result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'test_suite_version'), {
    path: ['test_suite_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tests'), {
    path: ['tests'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'warnings'), {
    path: ['warnings'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'failures'), {
    path: ['failures'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'holdout_state'), {
    path: ['holdout_state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'red_team_run_id'), {
    path: ['red_team_run_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'started_at'), {
    path: ['started_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'finished_at'), {
    path: ['finished_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ApprovalSummarySchema = z
  .object({
    approval_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    status: z.union([
      z.literal('PENDING'),
      z.literal('APPROVED'),
      z.literal('REJECTED'),
      z.literal('STALE'),
      z.literal('CANCELLED'),
    ]),
    revision: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'approval_id'), {
    path: ['approval_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  });
export const HoldoutGateSchema = z
  .object({
    validation_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    approval: z.unknown().superRefine((value, context) => {
      const matches = [
        ApprovalSummarySchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    action_capabilities: z.array(ActionCapabilitySchema),
    revision: z.number().int().min(1),
    validation: ValidationDetailSchema.optional(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'validation_id'), {
    path: ['validation_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'exposure_count'), {
    path: ['exposure_count'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'period'), {
    path: ['period'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'approval'), {
    path: ['approval'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  });
export const HoldoutResultSchema = z
  .object({
    validation_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    exposure_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^HOLD-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^HOLD-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    result: z.union([z.literal('PASS'), z.literal('WARN'), z.literal('FAIL')]),
    metrics: z.array(MetricSchema),
    provenance: ProvenanceSchema,
    exposed_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'validation_id'), {
    path: ['validation_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'exposure_id'), {
    path: ['exposure_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result'), {
    path: ['result'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'metrics'), {
    path: ['metrics'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'exposed_at'), {
    path: ['exposed_at'],
    message: 'Required property is missing',
  });
export const HoldoutApprovalRequestSchema = z
  .object({ reason: z.string().min(1) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'reason'), {
    path: ['reason'],
    message: 'Required property is missing',
  });
export const HoldoutRunRequestSchema = z
  .object({
    approval_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'approval_id'), {
    path: ['approval_id'],
    message: 'Required property is missing',
  });
export const ApprovalSubjectSchema = z
  .object({
    type: z.union([z.literal('STRATEGY_VERSION'), z.literal('VALIDATION'), z.literal('PAPER')]),
    id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    version: z.union([z.number().int().min(1), z.null()]),
    revision: z.number().int().min(1),
    sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'id'), {
    path: ['id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'version'), {
    path: ['version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sha256'), {
    path: ['sha256'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ type: z.literal('STRATEGY_VERSION') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'type'), {
              path: ['type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ type: z.literal('VALIDATION') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'type'), {
              path: ['type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ type: z.literal('PAPER') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'type'), {
              path: ['type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  });
export const ApprovalListItemSchema = z
  .object({
    approval_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    requested_at: z.iso.datetime({ offset: true }),
    decided_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'approval_id'), {
    path: ['approval_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'subject'), {
    path: ['subject'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'requester'), {
    path: ['requester'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reason'), {
    path: ['reason'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'requested_at'), {
    path: ['requested_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'decided_at'), {
    path: ['decided_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  });
export const ApprovalPageSchema = z
  .object({ items: z.array(ApprovalListItemSchema), page: PageInfoSchema })
  .strict()
  .refine((value) => Object.hasOwn(value, 'items'), {
    path: ['items'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'page'), {
    path: ['page'],
    message: 'Required property is missing',
  });
export const ApprovalPrerequisiteSchema = z
  .object({
    key: z.string(),
    state: z.union([z.literal('PASS'), z.literal('WARN'), z.literal('FAIL')]),
    detail: z.string(),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'key'), {
    path: ['key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'state'), {
    path: ['state'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  });
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
  .strict()
  .refine((value) => Object.hasOwn(value, 'risk_level'), {
    path: ['risk_level'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'warning_codes'), {
    path: ['warning_codes'],
    message: 'Required property is missing',
  });
export const ApprovalEffectSchema = z
  .object({ code: z.string(), detail: z.string() })
  .strict()
  .refine((value) => Object.hasOwn(value, 'code'), {
    path: ['code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'detail'), {
    path: ['detail'],
    message: 'Required property is missing',
  });
export const ApprovalDetailSchema = z
  .object({
    approval_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    requested_at: z.iso.datetime({ offset: true }),
    decided_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'approval_id'), {
    path: ['approval_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'subject'), {
    path: ['subject'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'requester'), {
    path: ['requester'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'reason'), {
    path: ['reason'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'prerequisites'), {
    path: ['prerequisites'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'risk_summary'), {
    path: ['risk_summary'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'effects'), {
    path: ['effects'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'requested_at'), {
    path: ['requested_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'decided_at'), {
    path: ['decided_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  });
export const ApprovalDecisionRequestSchema = z
  .object({ acknowledged_subject_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')) })
  .strict()
  .refine((value) => Object.hasOwn(value, 'acknowledged_subject_sha256'), {
    path: ['acknowledged_subject_sha256'],
    message: 'Required property is missing',
  });
export const ApprovalRejectRequestSchema = z
  .object({
    reason: z.string().min(1).max(4000),
    acknowledged_subject_sha256: z.string().regex(new RegExp('^[0-9a-f]{64}$')),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'reason'), {
    path: ['reason'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'acknowledged_subject_sha256'), {
    path: ['acknowledged_subject_sha256'],
    message: 'Required property is missing',
  });
export const JobAcceptedSchema = z
  .object({
    job_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    status: z.union([z.literal('QUEUED'), z.literal('RUNNING')]),
    progress: JobProgressSchema,
    resource_ref: z.unknown().superRefine((value, context) => {
      const matches = [
        ObjectRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    created_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'progress'), {
    path: ['progress'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'resource_ref'), {
    path: ['resource_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  });
export const ApprovalDecisionResultSchema = z
  .object({
    approval: ApprovalDetailSchema,
    subject_ref: ObjectRefSchema,
    next_job: z.unknown().superRefine((value, context) => {
      const matches = [
        JobAcceptedSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'approval'), {
    path: ['approval'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'subject_ref'), {
    path: ['subject_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'next_job'), {
    path: ['next_job'],
    message: 'Required property is missing',
  });
export const MemoGenerateRequestSchema = z
  .object({
    strategy_id: z
      .string()
      .min(32)
      .max(42)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(32)
            .max(32)
            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(42)
            .max(42)
            .regex(
              new RegExp(
                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    strategy_version: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'strategy_id'), {
    path: ['strategy_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy_version'), {
    path: ['strategy_version'],
    message: 'Required property is missing',
  });
export const MemoEvidenceLinkSchema = z
  .object({
    experiment_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    provenance: ProvenanceRefSchema,
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'experiment_id'), {
    path: ['experiment_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  });
export const MemoSectionSchema = z
  .object({
    section_key: z.string(),
    title: z.string(),
    content: z.string(),
    evidence_links: z.array(MemoEvidenceLinkSchema),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'section_key'), {
    path: ['section_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'title'), {
    path: ['title'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'content'), {
    path: ['content'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'evidence_links'), {
    path: ['evidence_links'],
    message: 'Required property is missing',
  });
export const MemoDetailSchema = z
  .object({
    memo_id: z
      .string()
      .min(31)
      .max(41)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(31)
            .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(41)
            .max(41)
            .regex(
              new RegExp(
                '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    strategy: z.unknown().superRefine((value, context) => {
      for (const result of [
        VersionRefSchema.safeParse(value),
        z
          .object({
            id: z
              .string()
              .min(32)
              .max(42)
              .superRefine((value, context) => {
                const matches = [
                  z
                    .string()
                    .min(32)
                    .max(32)
                    .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                    .safeParse(value).success,
                  z
                    .string()
                    .min(42)
                    .max(42)
                    .regex(
                      new RegExp(
                        '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                      ),
                    )
                    .safeParse(value).success,
                ].filter(Boolean).length;
                if (matches !== 1)
                  context.addIssue({
                    code: 'custom',
                    message: 'Value must match exactly one canonical variant',
                  });
              })
              .optional(),
          })
          .passthrough()
          .safeParse(value),
      ]) {
        if (!result.success) {
          for (const issue of result.error.issues)
            context.addIssue({
              code: 'custom',
              path: issue.path as (string | number)[],
              message: issue.message,
            });
        }
      }
    }),
    status: z.union([z.literal('GENERATING'), z.literal('FINAL'), z.literal('FAILED')]),
    sections: z.array(MemoSectionSchema),
    provenance: z.array(ProvenanceRefSchema),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime({ offset: true }),
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'memo_id'), {
    path: ['memo_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'strategy'), {
    path: ['strategy'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sections'), {
    path: ['sections'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'provenance'), {
    path: ['provenance'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const AgentConfigSchema = z
  .object({
    role_key: AgentRoleKeySchema,
    enabled: z.boolean(),
    model_provider: z.string(),
    model_name: z.string(),
    ai_connection_id: z.string(),
    ai_connection_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
      message: 'Integer must be exactly representable in JavaScript',
    }),
    runtime_profile: z.string(),
    tool_timeout_seconds: z.number().int().min(1),
    max_steps_override: z.union([z.number().int().min(1), z.null()]),
    max_tool_calls_override: z.union([z.number().int().min(1), z.null()]),
    revision: z.number().int().min(1),
    action_capabilities: z.array(ActionCapabilitySchema),
    created_at: z.iso.datetime({ offset: true }),
    updated_at: z.iso.datetime({ offset: true }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'role_key'), {
    path: ['role_key'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'enabled'), {
    path: ['enabled'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'model_provider'), {
    path: ['model_provider'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'model_name'), {
    path: ['model_name'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'ai_connection_id'), {
    path: ['ai_connection_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'ai_connection_revision'), {
    path: ['ai_connection_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'runtime_profile'), {
    path: ['runtime_profile'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tool_timeout_seconds'), {
    path: ['tool_timeout_seconds'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'max_steps_override'), {
    path: ['max_steps_override'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'max_tool_calls_override'), {
    path: ['max_tool_calls_override'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'action_capabilities'), {
    path: ['action_capabilities'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'created_at'), {
    path: ['created_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'updated_at'), {
    path: ['updated_at'],
    message: 'Required property is missing',
  });
export const AgentConfigListSchema = z.array(AgentConfigSchema);
export const AgentConfigUpdateSchema = z
  .object({
    enabled: z.boolean().optional(),
    runtime_profile: z.string().min(1).max(32).optional(),
    tool_timeout_seconds: z.number().int().min(1).optional(),
    max_steps_override: z.union([z.number().int().min(1), z.null()]).optional(),
    max_tool_calls_override: z.union([z.number().int().min(1), z.null()]).optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length >= 1, {
    message: 'Object requires at least 1 properties',
  });
export const JobResultRefSchema = z
  .object({
    object_type: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .union([
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
          ])
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    object_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .unknown()
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(31)
                .max(41)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(31)
                      .max(31)
                      .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(41)
                      .max(41)
                      .regex(
                        new RegExp(
                          '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(31)
                .max(41)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(31)
                      .max(31)
                      .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(41)
                      .max(41)
                      .regex(
                        new RegExp(
                          '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(32)
                .max(42)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(32)
                      .max(32)
                      .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(42)
                      .max(42)
                      .regex(
                        new RegExp(
                          '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(32)
                .max(42)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(32)
                      .max(32)
                      .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(42)
                      .max(42)
                      .regex(
                        new RegExp(
                          '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(31)
                .max(41)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(31)
                      .max(31)
                      .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(41)
                      .max(41)
                      .regex(
                        new RegExp(
                          '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(29)
                .max(39)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(29)
                      .max(29)
                      .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(39)
                      .max(39)
                      .regex(
                        new RegExp(
                          '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(31)
                .max(41)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(31)
                      .max(31)
                      .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(41)
                      .max(41)
                      .regex(
                        new RegExp(
                          '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(32)
                .max(42)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(32)
                      .max(32)
                      .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(42)
                      .max(42)
                      .regex(
                        new RegExp(
                          '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(31)
                .max(41)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(31)
                      .max(31)
                      .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(41)
                      .max(41)
                      .regex(
                        new RegExp(
                          '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z
                .string()
                .min(32)
                .max(42)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(32)
                      .max(32)
                      .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(42)
                      .max(42)
                      .regex(
                        new RegExp(
                          '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
              z.literal('SETTINGS-DEFAULT').safeParse(value).success,
              z
                .string()
                .regex(
                  new RegExp(
                    '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
              z
                .union([
                  z.literal('RESEARCH_DIRECTOR'),
                  z.literal('FACTOR_SCIENTIST'),
                  z.literal('STRATEGY_SCIENTIST'),
                  z.literal('PORTFOLIO_ANALYST'),
                  z.literal('RED_TEAM_RESEARCHER'),
                  z.literal('PERFORMANCE_ANALYST'),
                ])
                .safeParse(value).success,
              z
                .string()
                .min(30)
                .max(40)
                .superRefine((value, context) => {
                  const matches = [
                    z
                      .string()
                      .min(30)
                      .max(30)
                      .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                      .safeParse(value).success,
                    z
                      .string()
                      .min(40)
                      .max(40)
                      .regex(
                        new RegExp(
                          '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .safeParse(value).success,
                  ].filter(Boolean).length;
                  if (matches !== 1)
                    context.addIssue({
                      code: 'custom',
                      message: 'Value must match exactly one canonical variant',
                    });
                })
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches === 0)
              context.addIssue({
                code: 'custom',
                message: 'Value must match at least one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches === 0)
        context.addIssue({
          code: 'custom',
          message: 'Value must match at least one canonical variant',
        });
    }),
    object_version: z.union([z.number().int().min(1), z.null()]),
    object_revision: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    artifact_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^ART-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^ART-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'object_type'), {
    path: ['object_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_id'), {
    path: ['object_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_version'), {
    path: ['object_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_revision'), {
    path: ['object_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'artifact_id'), {
    path: ['artifact_id'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('job') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('research') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('conclusion') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('experiment') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('factor') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('strategy_version') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.number().int().min(1),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_version'), {
                    path: ['object_version'],
                    message: 'Required property is missing',
                  })
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('validation') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('approval') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('review') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('capability') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('snapshot') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('tool_call') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('memo') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('notification') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('settings') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.literal('SETTINGS-DEFAULT').optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('provider_connection') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .regex(
                        new RegExp(
                          '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_config') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .union([
                        z.literal('RESEARCH_DIRECTOR'),
                        z.literal('FACTOR_SCIENTIST'),
                        z.literal('STRATEGY_SCIENTIST'),
                        z.literal('PORTFOLIO_ANALYST'),
                        z.literal('RED_TEAM_RESEARCHER'),
                        z.literal('PERFORMANCE_ANALYST'),
                      ])
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('event_stream') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_id: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_id'), {
              path: ['object_id'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_type: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('job.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('job').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('research.created'), z.literal('research.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('research').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('research.conclusion.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('conclusion').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('experiment.created'),
                z.literal('experiment.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('experiment').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('factor.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('factor').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('strategy.created'), z.literal('strategy.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('strategy_version').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('validation.created'),
                z.literal('validation.updated'),
                z.literal('validation.holdout.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('validation').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('approval.created'), z.literal('approval.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('approval').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('paper.created'), z.literal('paper.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('paper.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('review.created'), z.literal('review.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('review').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.provider.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.capability.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('capability').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.quality.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('snapshot').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('agent.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('tool.call.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('tool_call').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.union([z.literal('memo.created'), z.literal('memo.updated')]) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('memo').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('setup.completed') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('configuration.updated'),
                z.literal('configuration.apply_failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('database.connection.updated'),
                z.literal('database.connection.failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('notification').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_config').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('system.health.updated'),
                z.literal('system.resync_required'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('event_stream').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  });
export const JobDetailSchema = z
  .object({
    job_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
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
    error_code: z.unknown().superRefine((value, context) => {
      const matches = [
        CanonicalErrorCodeSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    result_ref: z.unknown().superRefine((value, context) => {
      const matches = [
        JobResultRefSchema.safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    queued_at: z.iso.datetime({ offset: true }),
    started_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    finished_at: z.union([z.iso.datetime({ offset: true }), z.null()]),
    last_updated_at: z.iso.datetime({ offset: true }),
    revision: z.number().int().min(1),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_type'), {
    path: ['job_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'status'), {
    path: ['status'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'progress'), {
    path: ['progress'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'error_code'), {
    path: ['error_code'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'result_ref'), {
    path: ['result_ref'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'queued_at'), {
    path: ['queued_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'started_at'), {
    path: ['started_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'finished_at'), {
    path: ['finished_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'last_updated_at'), {
    path: ['last_updated_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'revision'), {
    path: ['revision'],
    message: 'Required property is missing',
  });
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
    job_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'type'), {
    path: ['type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  });
export const EventPayloadSchema = z
  .object({
    status: z.union([z.string(), z.null()]).optional(),
    state: z.union([z.string(), z.null()]).optional(),
    reason_code: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          CanonicalErrorCodeSchema.safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    resync_from_sequence: z
      .union([z.string().regex(new RegExp('^[1-9][0-9]*$')), z.null()])
      .optional(),
    progress_mode: z.union([z.literal('NONE'), z.literal('UNITS'), z.literal(null)]).optional(),
    completed_units: z
      .union([
        z.number().int().min(0).refine(Number.isSafeInteger, {
          message: 'Integer must be exactly representable in JavaScript',
        }),
        z.null(),
      ])
      .optional(),
    total_units: z
      .union([
        z.number().int().min(1).refine(Number.isSafeInteger, {
          message: 'Integer must be exactly representable in JavaScript',
        }),
        z.null(),
      ])
      .optional(),
    current_step_key: z.union([z.string(), z.null()]).optional(),
    agent_run_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(41)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(31)
                  .max(31)
                  .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(41)
                  .max(41)
                  .regex(
                    new RegExp(
                      '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    role: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          AgentRoleKeySchema.safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    objective: z.union([z.string(), z.null()]).optional(),
    research_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(31)
            .max(41)
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(31)
                  .max(31)
                  .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                  .safeParse(value).success,
                z
                  .string()
                  .min(41)
                  .max(41)
                  .regex(
                    new RegExp(
                      '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches !== 1)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match exactly one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    object_type: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .union([
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
            ])
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
    object_id: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          z
            .unknown()
            .superRefine((value, context) => {
              const matches = [
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(29)
                  .max(39)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(29)
                        .max(29)
                        .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(39)
                        .max(39)
                        .regex(
                          new RegExp(
                            '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(31)
                  .max(41)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(31)
                        .max(31)
                        .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(41)
                        .max(41)
                        .regex(
                          new RegExp(
                            '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z
                  .string()
                  .min(32)
                  .max(42)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(32)
                        .max(32)
                        .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(42)
                        .max(42)
                        .regex(
                          new RegExp(
                            '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
                z.literal('SETTINGS-DEFAULT').safeParse(value).success,
                z
                  .string()
                  .regex(
                    new RegExp(
                      '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                    ),
                  )
                  .safeParse(value).success,
                z
                  .union([
                    z.literal('RESEARCH_DIRECTOR'),
                    z.literal('FACTOR_SCIENTIST'),
                    z.literal('STRATEGY_SCIENTIST'),
                    z.literal('PORTFOLIO_ANALYST'),
                    z.literal('RED_TEAM_RESEARCHER'),
                    z.literal('PERFORMANCE_ANALYST'),
                  ])
                  .safeParse(value).success,
                z
                  .string()
                  .min(30)
                  .max(40)
                  .superRefine((value, context) => {
                    const matches = [
                      z
                        .string()
                        .min(30)
                        .max(30)
                        .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                        .safeParse(value).success,
                      z
                        .string()
                        .min(40)
                        .max(40)
                        .regex(
                          new RegExp(
                            '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                          ),
                        )
                        .safeParse(value).success,
                    ].filter(Boolean).length;
                    if (matches !== 1)
                      context.addIssue({
                        code: 'custom',
                        message: 'Value must match exactly one canonical variant',
                      });
                  })
                  .safeParse(value).success,
              ].filter(Boolean).length;
              if (matches === 0)
                context.addIssue({
                  code: 'custom',
                  message: 'Value must match at least one canonical variant',
                });
            })
            .safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches === 0)
          context.addIssue({
            code: 'custom',
            message: 'Value must match at least one canonical variant',
          });
      })
      .optional(),
    object_version: z.union([z.number().int().min(1), z.null()]).optional(),
    object_revision: z
      .union([
        z.number().int().min(1).refine(Number.isSafeInteger, {
          message: 'Integer must be exactly representable in JavaScript',
        }),
        z.null(),
      ])
      .optional(),
    waiting_on: z
      .unknown()
      .superRefine((value, context) => {
        const matches = [
          EventWaitingOnSchema.safeParse(value).success,
          z.null().nullable().safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      })
      .optional(),
  })
  .strict()
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('job') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('research') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('conclusion') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('experiment') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('factor') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('strategy_version') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.number().int().min(1),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_version'), {
                    path: ['object_version'],
                    message: 'Required property is missing',
                  })
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('validation') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('approval') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('review') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('capability') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('snapshot') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('tool_call') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('memo') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('notification') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('settings') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.literal('SETTINGS-DEFAULT').optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('provider_connection') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .regex(
                        new RegExp(
                          '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_config') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .union([
                        z.literal('RESEARCH_DIRECTOR'),
                        z.literal('FACTOR_SCIENTIST'),
                        z.literal('STRATEGY_SCIENTIST'),
                        z.literal('PORTFOLIO_ANALYST'),
                        z.literal('RED_TEAM_RESEARCHER'),
                        z.literal('PERFORMANCE_ANALYST'),
                      ])
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('event_stream') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_id: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_id'), {
              path: ['object_id'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_type: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('job.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('job').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('research.created'), z.literal('research.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('research').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('research.conclusion.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('conclusion').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('experiment.created'),
                z.literal('experiment.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('experiment').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('factor.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('factor').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('strategy.created'), z.literal('strategy.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('strategy_version').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('validation.created'),
                z.literal('validation.updated'),
                z.literal('validation.holdout.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('validation').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('approval.created'), z.literal('approval.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('approval').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('paper.created'), z.literal('paper.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('paper.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('review.created'), z.literal('review.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('review').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.provider.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.capability.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('capability').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.quality.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('snapshot').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('agent.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('tool.call.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('tool_call').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.union([z.literal('memo.created'), z.literal('memo.updated')]) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('memo').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('setup.completed') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('configuration.updated'),
                z.literal('configuration.apply_failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('database.connection.updated'),
                z.literal('database.connection.failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('notification').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_config').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('system.health.updated'),
                z.literal('system.resync_required'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('event_stream').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_type'))
      for (const key of ['object_id', 'object_version', 'object_revision'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_id'))
      for (const key of ['object_type', 'object_version', 'object_revision'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_version'))
      for (const key of ['object_type', 'object_id', 'object_revision'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
  .superRefine((value, context) => {
    if (Object.hasOwn(value, 'object_revision'))
      for (const key of ['object_type', 'object_id', 'object_version'] as string[])
        if (!Object.hasOwn(value, key))
          context.addIssue({
            code: 'custom',
            path: [key],
            message: 'Dependent property is required',
          });
  })
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
        const result =
          EventObjectLocatorSchemas[
            value.object_type as keyof typeof EventObjectLocatorSchemas
          ].safeParse(value);
        if (!result.success)
          context.addIssue({ code: 'custom', message: 'Event payload object locator is invalid' });
      }
    }
  });
export const SseEnvelopeSchema = z
  .object({
    schema_version: z.literal(1),
    event_id: z
      .string()
      .min(30)
      .max(40)
      .superRefine((value, context) => {
        const matches = [
          z
            .string()
            .min(30)
            .max(30)
            .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
            .safeParse(value).success,
          z
            .string()
            .min(40)
            .max(40)
            .regex(
              new RegExp(
                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
              ),
            )
            .safeParse(value).success,
        ].filter(Boolean).length;
        if (matches !== 1)
          context.addIssue({
            code: 'custom',
            message: 'Value must match exactly one canonical variant',
          });
      }),
    sequence: z.string().regex(new RegExp('^[1-9][0-9]*$')),
    event_type: EventTypeSchema,
    occurred_at: z.iso.datetime({ offset: true }),
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
    object_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(29)
          .max(39)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(29)
                .max(29)
                .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(39)
                .max(39)
                .regex(
                  new RegExp(
                    '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.literal('SETTINGS-DEFAULT').safeParse(value).success,
        z
          .string()
          .regex(
            new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
          )
          .safeParse(value).success,
        z
          .union([
            z.literal('RESEARCH_DIRECTOR'),
            z.literal('FACTOR_SCIENTIST'),
            z.literal('STRATEGY_SCIENTIST'),
            z.literal('PORTFOLIO_ANALYST'),
            z.literal('RED_TEAM_RESEARCHER'),
            z.literal('PERFORMANCE_ANALYST'),
          ])
          .safeParse(value).success,
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
      ].filter(Boolean).length;
      if (matches === 0)
        context.addIssue({
          code: 'custom',
          message: 'Value must match at least one canonical variant',
        });
    }),
    object_version: z.union([z.number().int().min(1), z.null()]),
    object_revision: z.union([
      z.number().int().min(1).refine(Number.isSafeInteger, {
        message: 'Integer must be exactly representable in JavaScript',
      }),
      z.null(),
    ]),
    request_id: z.union([z.string(), z.null()]),
    job_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(30)
          .max(40)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(30)
                .max(30)
                .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(40)
                .max(40)
                .regex(
                  new RegExp(
                    '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    agent_run_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(31)
          .max(41)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(31)
                .max(31)
                .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(41)
                .max(41)
                .regex(
                  new RegExp(
                    '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    tool_call_id: z.unknown().superRefine((value, context) => {
      const matches = [
        z
          .string()
          .min(32)
          .max(42)
          .superRefine((value, context) => {
            const matches = [
              z
                .string()
                .min(32)
                .max(32)
                .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                .safeParse(value).success,
              z
                .string()
                .min(42)
                .max(42)
                .regex(
                  new RegExp(
                    '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                  ),
                )
                .safeParse(value).success,
            ].filter(Boolean).length;
            if (matches !== 1)
              context.addIssue({
                code: 'custom',
                message: 'Value must match exactly one canonical variant',
              });
          })
          .safeParse(value).success,
        z.null().nullable().safeParse(value).success,
      ].filter(Boolean).length;
      if (matches !== 1)
        context.addIssue({
          code: 'custom',
          message: 'Value must match exactly one canonical variant',
        });
    }),
    payload: EventPayloadSchema,
  })
  .strict()
  .refine((value) => Object.hasOwn(value, 'schema_version'), {
    path: ['schema_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'event_id'), {
    path: ['event_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'sequence'), {
    path: ['sequence'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'event_type'), {
    path: ['event_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'occurred_at'), {
    path: ['occurred_at'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_type'), {
    path: ['object_type'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_id'), {
    path: ['object_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_version'), {
    path: ['object_version'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'object_revision'), {
    path: ['object_revision'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'request_id'), {
    path: ['request_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'job_id'), {
    path: ['job_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'agent_run_id'), {
    path: ['agent_run_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'tool_call_id'), {
    path: ['tool_call_id'],
    message: 'Required property is missing',
  })
  .refine((value) => Object.hasOwn(value, 'payload'), {
    path: ['payload'],
    message: 'Required property is missing',
  })
  .superRefine((value, context) => {
    for (const result of [
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('job') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^JOB-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^JOB-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('research') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^RSCH-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^RSCH-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('conclusion') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^CONC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^CONC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('experiment') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EXP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EXP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('factor') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^FAC-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^FAC-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('strategy_version') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.number().int().min(1),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_version'), {
                    path: ['object_version'],
                    message: 'Required property is missing',
                  })
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('validation') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^VAL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^VAL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('approval') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^APR-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^APR-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^PAPER-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^PAPER-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('paper_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^PRUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^PRUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('review') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^REV-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^REV-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('capability') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^CAP-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^CAP-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('snapshot') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(29)
                      .max(39)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(29)
                            .max(29)
                            .regex(new RegExp('^DS-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(39)
                            .max(39)
                            .regex(
                              new RegExp(
                                '^DS-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_run') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^ARUN-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^ARUN-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('tool_call') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^TCALL-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^TCALL-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('memo') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(31)
                      .max(41)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(31)
                            .max(31)
                            .regex(new RegExp('^MEMO-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(41)
                            .max(41)
                            .regex(
                              new RegExp(
                                '^MEMO-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('notification') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(32)
                      .max(42)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(32)
                            .max(32)
                            .regex(new RegExp('^NOTIF-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(42)
                            .max(42)
                            .regex(
                              new RegExp(
                                '^NOTIF-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('settings') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.literal('SETTINGS-DEFAULT').optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('provider_connection') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .regex(
                        new RegExp(
                          '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                        ),
                      )
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('agent_config') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .union([
                        z.literal('RESEARCH_DIRECTOR'),
                        z.literal('FACTOR_SCIENTIST'),
                        z.literal('STRATEGY_SCIENTIST'),
                        z.literal('PORTFOLIO_ANALYST'),
                        z.literal('RED_TEAM_RESEARCHER'),
                        z.literal('PERFORMANCE_ANALYST'),
                      ])
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.literal('event_stream') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z
                      .string()
                      .min(30)
                      .max(40)
                      .superRefine((value, context) => {
                        const matches = [
                          z
                            .string()
                            .min(30)
                            .max(30)
                            .regex(new RegExp('^EVT-[0-7][0-9A-HJKMNP-TV-Z]{25}$'))
                            .safeParse(value).success,
                          z
                            .string()
                            .min(40)
                            .max(40)
                            .regex(
                              new RegExp(
                                '^EVT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                              ),
                            )
                            .safeParse(value).success,
                        ].filter(Boolean).length;
                        if (matches !== 1)
                          context.addIssue({
                            code: 'custom',
                            message: 'Value must match exactly one canonical variant',
                          });
                      })
                      .optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.number().int().min(1).refine(Number.isSafeInteger, {
                      message: 'Integer must be exactly representable in JavaScript',
                    }),
                  })
                  .passthrough()
                  .refine((value) => Object.hasOwn(value, 'object_revision'), {
                    path: ['object_revision'],
                    message: 'Required property is missing',
                  })
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_type: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_type'), {
              path: ['object_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_id: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ object_id: z.null().nullable() })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'object_id'), {
              path: ['object_id'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z
                  .object({
                    object_type: z.null().nullable().optional(),
                    object_version: z.null().nullable().optional(),
                    object_revision: z.null().nullable().optional(),
                  })
                  .passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('job.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('job').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('research.created'), z.literal('research.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('research').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('research.conclusion.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('conclusion').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('experiment.created'),
                z.literal('experiment.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('experiment').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('factor.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('factor').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('strategy.created'), z.literal('strategy.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('strategy_version').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('validation.created'),
                z.literal('validation.updated'),
                z.literal('validation.holdout.updated'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('validation').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('approval.created'), z.literal('approval.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('approval').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('paper.created'), z.literal('paper.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('paper.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('paper_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([z.literal('review.created'), z.literal('review.updated')]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('review').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.provider.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.capability.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('capability').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('data.quality.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('snapshot').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('agent.run.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_run').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('tool.call.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('tool_call').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.union([z.literal('memo.created'), z.literal('memo.updated')]) })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('memo').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('setup.completed') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('configuration.updated'),
                z.literal('configuration.apply_failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('settings').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('database.connection.updated'),
                z.literal('database.connection.failed'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('provider_connection').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.created') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('notification').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({ event_type: z.literal('notification.updated') })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('agent_config').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
      z
        .unknown()
        .superRefine((value, context) => {
          const conditional = z
            .object({
              event_type: z.union([
                z.literal('system.health.updated'),
                z.literal('system.resync_required'),
              ]),
            })
            .passthrough()
            .refine((value) => Object.hasOwn(value, 'event_type'), {
              path: ['event_type'],
              message: 'Required property is missing',
            })
            .safeParse(value).success;
          const result = (
            conditional
              ? z.object({ object_type: z.literal('event_stream').optional() }).passthrough()
              : z.unknown()
          ).safeParse(value);
          if (!result.success)
            for (const issue of result.error.issues)
              context.addIssue({
                code: 'custom',
                path: issue.path as (string | number)[],
                message: issue.message,
              });
        })
        .safeParse(value),
    ]) {
      if (!result.success) {
        for (const issue of result.error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path as (string | number)[],
            message: issue.message,
          });
      }
    }
  })
  .superRefine((value, context) => {
    if (EventTypeObjectTypeMap[value.event_type] !== value.object_type)
      context.addIssue({
        code: 'custom',
        path: ['object_type'],
        message: 'Event type and object type must agree',
      });
    if (
      !EventObjectLocatorSchemas[
        value.object_type as keyof typeof EventObjectLocatorSchemas
      ].safeParse(value).success
    )
      context.addIssue({
        code: 'custom',
        path: ['object_id'],
        message: 'Event object locator is invalid',
      });
  });
