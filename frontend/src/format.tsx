import { useTranslation } from 'react-i18next';
import i18n, { canonicalTimeZone, getRestoredServerLocale } from './i18n';

export const safeTimeZone = canonicalTimeZone;

const MAX_DECIMAL_DIGITS = 10_000;

type DecimalParts = { negative: boolean; integer: string; fraction: string };

function parseBoundedExponent(value: string | undefined): number | null {
  if (!value) return 0;
  const negative = value.startsWith('-');
  const digits = value.replace(/^[+-]/, '');
  let exponent = 0;
  for (const digit of digits) {
    exponent = exponent * 10 + digit.charCodeAt(0) - 48;
    if (exponent > MAX_DECIMAL_DIGITS) return null;
  }
  return negative ? -exponent : exponent;
}

function parseCanonicalDecimal(value: string): DecimalParts | null {
  if (value.length === 0 || value.length > MAX_DECIMAL_DIGITS) return null;
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return null;
  const exponent = parseBoundedExponent(match[4]);
  if (exponent === null) return null;
  const coefficientInteger = match[2];
  if (!coefficientInteger) return null;
  const coefficientFraction = match[3] ?? '';
  const digits = coefficientInteger + coefficientFraction;
  const decimalIndex = coefficientInteger.length + exponent;
  if (Math.abs(decimalIndex) + digits.length > MAX_DECIMAL_DIGITS) return null;
  const integer =
    decimalIndex <= 0
      ? '0'
      : decimalIndex >= digits.length
        ? digits + '0'.repeat(decimalIndex - digits.length)
        : digits.slice(0, decimalIndex);
  const fraction =
    decimalIndex <= 0
      ? '0'.repeat(-decimalIndex) + digits
      : decimalIndex >= digits.length
        ? ''
        : digits.slice(decimalIndex);
  return {
    negative: match[1] === '-',
    integer: integer.replace(/^0+(?=\d)/, ''),
    fraction,
  };
}

function withPrecision(
  parts: DecimalParts,
  precision: number | null | undefined,
): DecimalParts | null {
  if (precision === null || precision === undefined) return parts;
  if (!Number.isInteger(precision) || precision < 0 || precision > 18) return null;
  if (parts.fraction.length <= precision)
    return { ...parts, fraction: parts.fraction.padEnd(precision, '0') };
  const retained = parts.fraction.slice(0, precision);
  if (parts.fraction.charCodeAt(precision) < 53) return { ...parts, fraction: retained };
  const rounded = (parts.integer + retained).split('');
  let cursor = rounded.length - 1;
  while (cursor >= 0 && rounded[cursor] === '9') {
    rounded[cursor] = '0';
    cursor -= 1;
  }
  if (cursor < 0) rounded.unshift('1');
  else rounded[cursor] = String.fromCharCode((rounded[cursor] ?? '0').charCodeAt(0) + 1);
  const split = rounded.length - precision;
  return {
    ...parts,
    integer: rounded.slice(0, split).join(''),
    fraction: precision === 0 ? '' : rounded.slice(split).join(''),
  };
}

function localeNumberSyntax(locale: string) {
  const formatter = new Intl.NumberFormat(locale, { useGrouping: true });
  const groupingParts = formatter.formatToParts(1234567890123);
  const integerSegments = groupingParts
    .filter((part) => part.type === 'integer')
    .map((part) => part.value.length);
  return {
    group: groupingParts.find((part) => part.type === 'group')?.value ?? '',
    decimal:
      new Intl.NumberFormat(locale).formatToParts(1.1).find((part) => part.type === 'decimal')
        ?.value ?? '.',
    minus:
      new Intl.NumberFormat(locale).formatToParts(-1).find((part) => part.type === 'minusSign')
        ?.value ?? '-',
    primaryGroupSize: integerSegments.at(-1) ?? 0,
    secondaryGroupSize: integerSegments.at(-2) ?? integerSegments.at(-1) ?? 0,
  };
}

function groupInteger(
  integer: string,
  group: string,
  primarySize: number,
  secondarySize: number,
): string {
  if (!group || primarySize === 0 || integer.length <= primarySize) return integer;
  const segments: string[] = [];
  let cursor = integer.length;
  let size = primarySize;
  while (cursor > 0) {
    const start = Math.max(0, cursor - size);
    segments.unshift(integer.slice(start, cursor));
    cursor = start;
    size = secondarySize;
  }
  return segments.join(group);
}

export function formatCanonicalDecimal(
  value: string,
  locale: string,
  precision?: number | null,
): string | null {
  const parsed = parseCanonicalDecimal(value);
  const adjusted = parsed && withPrecision(parsed, precision);
  if (!adjusted) return null;
  try {
    const syntax = localeNumberSyntax(locale);
    const integer = groupInteger(
      adjusted.integer,
      syntax.group,
      syntax.primaryGroupSize,
      syntax.secondaryGroupSize,
    );
    return `${adjusted.negative ? syntax.minus : ''}${integer}${
      adjusted.fraction ? `${syntax.decimal}${adjusted.fraction}` : ''
    }`;
  } catch {
    return null;
  }
}

export function formatServerDateTime(
  value: string,
  settings: { language: 'zh-CN' | 'en'; timezone: string } = getRestoredServerLocale() ?? {
    language: 'zh-CN',
    timezone: 'UTC',
  },
): string {
  const utcPattern = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?Z$/;
  const match = value.match(utcPattern);
  const instant = new Date(value);
  if (!match || !Number.isFinite(instant.getTime())) return i18n.t('format.invalidUtc');
  const [
    ,
    yearPart = '',
    monthPart = '',
    dayPart = '',
    hourPart = '',
    minutePart = '',
    secondPart = '',
    fraction = '',
  ] = match;
  const year = Number(yearPart);
  const month = Number(monthPart);
  const day = Number(dayPart);
  const hour = Number(hourPart);
  const minute = Number(minutePart);
  const second = Number(secondPart);
  const roundTrip = new Date(
    Date.UTC(year, month - 1, day, hour, minute, second, Number((fraction + '000').slice(0, 3))),
  );
  if (
    roundTrip.getUTCFullYear() !== year ||
    roundTrip.getUTCMonth() !== month - 1 ||
    roundTrip.getUTCDate() !== day ||
    roundTrip.getUTCHours() !== hour ||
    roundTrip.getUTCMinutes() !== minute ||
    roundTrip.getUTCSeconds() !== second
  )
    return i18n.t('format.invalidUtc');
  const timeZone = safeTimeZone(settings.timezone);
  const parts = new Intl.DateTimeFormat(settings.language, {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
    timeZoneName: 'short',
  }).formatToParts(instant);
  const valueOf = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? '';
  return `${valueOf('year')}-${valueOf('month')}-${valueOf('day')} ${valueOf('hour')}:${valueOf('minute')}:${valueOf('second')} ${valueOf('timeZoneName')}`;
}

export function ServerTime({ value }: { value: string | null | undefined }) {
  useTranslation();
  if (!value) return <>—</>;
  return <time dateTime={value}>{formatServerDateTime(value)}</time>;
}
