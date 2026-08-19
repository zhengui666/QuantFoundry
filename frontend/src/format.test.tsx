import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import {
  formatCanonicalDecimal,
  formatCanonicalPercent,
  formatServerDateTime,
  safeTimeZone,
  ServerTime,
} from './format';

describe('canonical decimal display formatter', () => {
  it('scales canonical return decimals to exact percentages', () => {
    expect(formatCanonicalPercent('0.0100', 'en')).toBe('1.00');
    expect(formatCanonicalPercent('-0.125', 'de-DE')).toBe('-12,5');
  });
  it.each([
    [0, '-9,007,199,254,740,993'],
    [1, '-9,007,199,254,740,993.1'],
    [2, '-9,007,199,254,740,993.12'],
    [3, '-9,007,199,254,740,993.123'],
    [4, '-9,007,199,254,740,993.1235'],
    [5, '-9,007,199,254,740,993.12346'],
    [6, '-9,007,199,254,740,993.123457'],
    [7, '-9,007,199,254,740,993.1234568'],
    [8, '-9,007,199,254,740,993.12345679'],
    [9, '-9,007,199,254,740,993.123456789'],
    [10, '-9,007,199,254,740,993.1234567890'],
    [11, '-9,007,199,254,740,993.12345678901'],
    [12, '-9,007,199,254,740,993.123456789012'],
    [13, '-9,007,199,254,740,993.1234567890123'],
    [14, '-9,007,199,254,740,993.12345678901235'],
    [15, '-9,007,199,254,740,993.123456789012346'],
    [16, '-9,007,199,254,740,993.1234567890123457'],
    [17, '-9,007,199,254,740,993.12345678901234568'],
    [18, '-9,007,199,254,740,993.123456789012345679'],
  ] as const)('exactly applies precision metadata %i', (precision, expected) => {
    expect(formatCanonicalDecimal('-9007199254740993.1234567890123456789', 'en', precision)).toBe(
      expected,
    );
  });

  it('never rounds unsafe integers through binary floating point', () => {
    expect(formatCanonicalDecimal('9007199254740993', 'en')).toBe('9,007,199,254,740,993');
  });

  it('preserves sign and source trailing precision when metadata is absent', () => {
    expect(formatCanonicalDecimal('-12345678901234567890.12345678901234567800', 'en')).toBe(
      '-12,345,678,901,234,567,890.12345678901234567800',
    );
  });

  it('pads and exactly rounds to precision metadata without losing trailing zeroes', () => {
    expect(formatCanonicalDecimal('9007199254740993.12', 'en', 18)).toBe(
      '9,007,199,254,740,993.120000000000000000',
    );
    expect(formatCanonicalDecimal('-999.995', 'en', 2)).toBe('-1,000.00');
  });

  it('expands scientific notation without binary floating point', () => {
    expect(formatCanonicalDecimal('1.234567890123456789e-3', 'en')).toBe('0.001234567890123456789');
    expect(formatCanonicalDecimal('-9.007199254740993e15', 'en')).toBe('-9,007,199,254,740,993');
  });

  it('uses locale grouping and decimal separators', () => {
    expect(formatCanonicalDecimal('1234567.8900', 'de-DE')).toBe('1.234.567,8900');
  });

  it('formats canonical decimal strings exactly for zh-CN', () => {
    expect(formatCanonicalDecimal('9007199254740993.1200', 'zh-CN')).toBe(
      '9,007,199,254,740,993.1200',
    );
    expect(formatCanonicalDecimal('-1.234567890123456789e-3', 'zh-CN', 18)).toBe(
      '-0.001234567890123457',
    );
  });

  it('fails closed for non-canonical or unbounded input', () => {
    for (const value of ['NaN', 'Infinity', '1,000', '1.2.3', ' 1', '1e10001'])
      expect(formatCanonicalDecimal(value, 'en')).toBeNull();
  });
});

describe('server UTC display formatter', () => {
  it('renders the same UTC instant in multiple Settings timezones', () => {
    const utc = '2026-08-11T00:00:00Z';
    expect(formatServerDateTime(utc, { language: 'zh-CN', timezone: 'Asia/Shanghai' })).toContain(
      '2026-08-11 08:00:00',
    );
    expect(formatServerDateTime(utc, { language: 'en', timezone: 'America/New_York' })).toContain(
      '2026-08-10 20:00:00',
    );
  });

  it('fails closed to UTC for an invalid server Settings timezone', () => {
    expect(safeTimeZone('Not/A_Real_Zone')).toBe('UTC');
    expect(
      formatServerDateTime('2026-08-11T00:00:00Z', {
        language: 'en',
        timezone: 'Not/A_Real_Zone',
      }),
    ).toContain('2026-08-11 00:00:00 UTC');
  });

  it('exposes the canonical UTC value through semantic time markup', () => {
    render(<ServerTime value="2026-08-11T00:00:00Z" />);
    expect(screen.getByText(/2026-08-11/).closest('time')).toHaveAttribute(
      'datetime',
      '2026-08-11T00:00:00Z',
    );
  });
});
