import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Schema } from './api/client';
import i18n from './i18n';

const setOption = vi.fn();
vi.mock('echarts/core', () => ({
  init: () => ({ setOption, dispose: vi.fn() }),
  use: vi.fn(),
}));

import CanonicalChart from './CanonicalChart';

const chart = {
  schema_version: 1,
  chart_id: 'chart-i18n',
  chart_type: 'EQUITY_CURVE',
  metric_key: 'nav',
  x_axis: { kind: 'TIME', timezone: 'UTC' },
  series: [
    {
      series_id: 'paper',
      series_key: 'paper',
      display_label: 'Portfolio NAV',
      unit: 'USD',
      value_format: { kind: 'CURRENCY', precision: 2 },
      points: [
        { x: '2026-08-01', y: '100000' },
        { x: '2026-08-02', y: null },
      ],
    },
  ],
  period_markers: [
    { period_type: 'PAPER', start: '2026-08-01', end: '2026-08-02', state: 'EXPOSED' },
  ],
  assumptions: [{ key: 'currency', value: '1', unit: 'USD' }],
  summary: {
    template_key: 'chart.equity_curve.summary',
    params: { ending_nav: '100000', benchmark_ending_nav: null },
  },
  downsampling: { applied: true, source_points: 2000, returned_points: 2, method: 'LTTB' },
  provenance: { provenance_id: 'PROV-70Z4DHXM4HQYPD84CTHRQT2T8N' },
  generated_at: '2026-08-10T02:00:00Z',
} satisfies Schema<'ChartAggregate'>;

afterEach(async () => {
  cleanup();
  setOption.mockClear();
  await i18n.changeLanguage('zh-CN');
});

describe('CanonicalChart localization', () => {
  it('renders all auxiliary and table copy in English through i18n', async () => {
    await i18n.changeLanguage('en');
    render(<CanonicalChart chart={chart} />);
    expect(screen.getByRole('img', { name: 'Paper performance chart' })).toBeVisible();
    expect(screen.getByText(/Ending NAV 100,000; benchmark unavailable/)).toBeVisible();
    expect(screen.getByText(/2 of 2,000 points shown using LTTB/)).toBeVisible();
    expect(screen.getByText('Calculated')).toBeVisible();
    fireEvent.click(screen.getByText('Chart data table'));
    expect(screen.getByRole('columnheader', { name: 'Series' })).toBeVisible();
    expect(screen.getByRole('cell', { name: 'Gap' })).toBeVisible();
    expect(setOption).toHaveBeenCalledWith(
      expect.objectContaining({
        aria: expect.objectContaining({ description: expect.stringContaining('1 series') }),
      }),
    );
  });

  it('renders all auxiliary and table copy in Chinese through i18n', async () => {
    await i18n.changeLanguage('zh-CN');
    render(<CanonicalChart chart={chart} />);
    expect(screen.getByRole('img', { name: '纸面业绩图表' })).toBeVisible();
    expect(screen.getByText(/期末净值 100,000；基准 不可用/)).toBeVisible();
    expect(screen.getByText(/显示 2,000 个数据点中的 2 个，方法为 LTTB/)).toBeVisible();
    expect(screen.getByText('已计算')).toBeVisible();
    fireEvent.click(screen.getByText('图表数据表'));
    expect(screen.getByRole('columnheader', { name: '序列' })).toBeVisible();
    expect(screen.getByRole('cell', { name: '缺口' })).toBeVisible();
    expect(setOption).toHaveBeenCalledWith(
      expect.objectContaining({
        aria: expect.objectContaining({ description: expect.stringContaining('1 个序列') }),
      }),
    );
  });
});
