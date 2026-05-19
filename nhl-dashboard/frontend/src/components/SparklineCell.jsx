import Sparkline from './Sparkline.jsx';

export default function SparklineCell({ series, delta }) {
  const last = series[series.length - 1];
  const first = series[0];
  const totalDelta = last - first;
  const up = totalDelta >= 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 2 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span className="mono tnum" style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{last.toFixed(0)}%</span>
        <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: up ? 'var(--up)' : 'var(--down)' }}>
          {up ? '+' : ''}{totalDelta.toFixed(1)}
        </span>
      </div>
      <Sparkline data={series} width={140} height={32} />
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.04em' }}>24H · IMPLIED %</span>
    </div>
  );
}
