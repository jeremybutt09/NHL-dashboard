import Sparkline from './Sparkline';

export default function SparklineCell({ series }) {
  if (!series || series.length < 2) {
    return (
      <div className="sparkline">
        <span className="mono tnum" style={{ fontSize: 13, fontWeight: 600, color: 'var(--faint)' }}>—</span>
        <div style={{ height: 32, width: 140, display: 'flex', alignItems: 'center', color: 'var(--faint)', fontSize: 10, letterSpacing: '0.04em' }}>
          {series && series.length === 1 ? 'tracking…' : 'no history yet'}
        </div>
        <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.04em' }}>IMPLIED % HISTORY</span>
      </div>
    );
  }
  const last = series[series.length - 1];
  const first = series[0];
  const totalDelta = last - first;
  const up = totalDelta >= 0;
  return (
    <div className="sparkline">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span className="mono tnum" style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
          {last.toFixed(0)}%
        </span>
        <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: up ? 'var(--up)' : 'var(--down)' }}>
          {up ? '+' : ''}{totalDelta.toFixed(1)}
        </span>
      </div>
      <Sparkline data={series} width={140} height={32} />
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.04em' }}>24H · IMPLIED %</span>
    </div>
  );
}
