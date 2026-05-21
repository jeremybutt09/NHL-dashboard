import { useState } from 'react';

export default function TeamGlyph({ code, size = 32, dim = false }) {
  const [failed, setFailed] = useState(false);
  const hash = [...code].reduce((a, c) => a * 31 + c.charCodeAt(0), 7) >>> 0;
  const hue = hash % 360;
  const logoUrl = `https://assets.nhle.com/logos/nhl/svg/${code}_light.svg`;

  if (failed) {
    return (
      <div style={{
        width: size, height: size, borderRadius: 8,
        background: `oklch(0.92 0.04 ${hue})`,
        border: '1px solid var(--rule)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Geist Mono', monospace", fontWeight: 600,
        fontSize: size * 0.32, color: `oklch(0.30 0.10 ${hue})`,
        flexShrink: 0,
        opacity: dim ? 0.5 : 1,
      }}>
        {code}
      </div>
    );
  }
  return (
    <div style={{
      width: size, height: size,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
      opacity: dim ? 0.55 : 1,
      filter: dim ? 'saturate(0.6)' : 'none',
      transition: 'opacity .2s, filter .2s',
    }}>
      <img
        src={logoUrl}
        alt={code}
        onError={() => setFailed(true)}
        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
      />
    </div>
  );
}
