import { useEffect, useRef } from 'react';
import { LineChart } from 'echarts/charts';
import { AriaComponent, GridComponent, MarkAreaComponent } from 'echarts/components';
import { init, use as registerChartComponents } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useTranslation } from 'react-i18next';
import type { Schema } from './api/client';
import { formatCanonicalDecimal } from './format';
import { Provenance } from './ui';

registerChartComponents([
  LineChart,
  AriaComponent,
  GridComponent,
  MarkAreaComponent,
  CanvasRenderer,
]);

export default function CanonicalChart({ chart }: { chart: Schema<'ChartAggregate'> }) {
  const { i18n, t } = useTranslation();
  const target = useRef<HTMLDivElement>(null);
  const locale = i18n.resolvedLanguage === 'en' ? 'en' : 'zh-CN';
  const unavailable = t('chart.unavailable');
  const formatDecimal = (value: string, precision?: number | null) =>
    formatCanonicalDecimal(value, locale, precision) ?? unavailable;
  const formatCount = (value: number) => formatDecimal(String(value), 0);
  const ariaDescription = t('chart.ariaDescription', {
    seriesCount: formatCount(chart.series.length),
    pointCount: formatCount(chart.downsampling.returned_points),
  });
  useEffect(() => {
    if (!target.current) return;
    const instance = init(target.current);
    instance.setOption({
      animation: false,
      aria: { enabled: true, description: ariaDescription, decal: { show: true } },
      xAxis: {
        type:
          chart.x_axis.kind === 'TIME'
            ? 'time'
            : chart.x_axis.kind === 'NUMERIC'
              ? 'value'
              : 'category',
      },
      yAxis: { type: 'value' },
      series: chart.series.map((series, index) => ({
        name: series.display_label,
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        data: series.points.map((point) => [point.x, point.y]),
        markArea:
          index === 0
            ? {
                silent: true,
                data: chart.period_markers.map((marker) => [
                  {
                    name: t('chart.periodLabel', {
                      period: t(`chart.period.${marker.period_type}`),
                      state: t(`status.${marker.state}`, { defaultValue: marker.state }),
                    }),
                    xAxis: marker.start,
                    label: {
                      position: marker.period_type === 'HOLDOUT' ? 'insideTop' : 'insideTopLeft',
                      fontSize: 10,
                    },
                  },
                  { xAxis: marker.end },
                ]),
              }
            : undefined,
      })),
    });
    return () => instance.dispose();
  }, [ariaDescription, chart, t]);
  const summary = `${t('chart.summary', {
    endingNav:
      chart.summary.params.ending_nav === null
        ? unavailable
        : formatDecimal(chart.summary.params.ending_nav),
    benchmarkNav:
      chart.summary.params.benchmark_ending_nav === null
        ? unavailable
        : formatDecimal(chart.summary.params.benchmark_ending_nav),
  })} ${t(
    chart.downsampling.applied ? 'chart.downsamplingApplied' : 'chart.downsamplingNotApplied',
    {
      returned: formatCount(chart.downsampling.returned_points),
      source: formatCount(chart.downsampling.source_points),
      method: chart.downsampling.method ?? unavailable,
    },
  )}`;
  return (
    <figure>
      <div ref={target} className="chart" role="img" aria-label={t('chart.ariaLabel')} />
      <figcaption aria-live="polite">{summary}</figcaption>
      <dl className="definition">
        {chart.assumptions.map((assumption) => (
          <div key={assumption.key} className="definition-pair">
            <dt>{t('chart.assumption', { key: assumption.key })}</dt>
            <dd>
              {formatDecimal(assumption.value)} {assumption.unit ?? ''}
            </dd>
          </div>
        ))}
      </dl>
      <Provenance value={chart.provenance} />
      <details>
        <summary>{t('chart.dataTable')}</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">{t('chart.series')}</th>
                <th scope="col">{t('chart.x')}</th>
                <th scope="col">{t('chart.y')}</th>
                <th scope="col">{t('chart.unit')}</th>
              </tr>
            </thead>
            <tbody>
              {chart.series.flatMap((series) =>
                series.points.map((point) => (
                  <tr key={`${series.series_id}:${point.x}`}>
                    <td>{series.display_label}</td>
                    <td>{point.x}</td>
                    <td>
                      {point.y === null
                        ? t('chart.gap')
                        : formatDecimal(point.y, series.value_format.precision)}
                    </td>
                    <td>{series.unit}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
