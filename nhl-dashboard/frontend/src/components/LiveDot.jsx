export default function LiveDot({ small = false }) {
  return (
    <span className="live-dot" style={{
      display: 'inline-block', width: small ? 6 : 8, height: small ? 6 : 8,
      borderRadius: '50%', background: 'var(--hot)',
    }} />
  );
}
