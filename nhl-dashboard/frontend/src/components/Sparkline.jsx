export default function Sparkline({ data, width = 140, height = 40, color }) {
  const padX = 2, padY = 4;
  const min = Math.min(...data) - 1;
  const max = Math.max(...data) + 1;
  const range = max - min || 1;
  const stepX = (width - padX * 2) / (data.length - 1);
  const pts = data.map((v, i) => [
    padX + i * stepX,
    padY + (height - padY * 2) * (1 - (v - min) / range),
  ]);
  const path = pts
    .map((p, i) => (i === 0 ? `M${p[0].toFixed(1)},${p[1].toFixed(1)}` : `L${p[0].toFixed(1)},${p[1].toFixed(1)}`))
    .join(' ');
  const areaPath = `${path} L${pts[pts.length - 1][0].toFixed(1)},${height - padY} L${pts[0][0].toFixed(1)},${height - padY} Z`;
  const first = data[0], last = data[data.length - 1];
  const delta = last - first;
  const upish = delta >= 0;
  const stroke = color || (upish ? 'var(--up)' : 'var(--down)');
  const gradId = `g-${Math.abs(stroke.length + data[0] * 7) | 0}`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={stroke} stopOpacity="0.18" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2.5" fill={stroke} />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="5" fill={stroke} opacity="0.18" />
    </svg>
  );
}
