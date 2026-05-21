import { useState, useEffect } from 'react';

const DENSITIES = ['compact', 'regular', 'comfy'];

function PeakMark() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{
        width: 28, height: 28, borderRadius: 6,
        background: 'var(--accent)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 14,
      }}>P</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 15, letterSpacing: '-0.01em' }}>Peak</span>
        <span style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 500 }}>NHL</span>
      </div>
    </div>
  );
}

/**
 * Top navigation bar with dark mode toggle and density toggle.
 *
 * @param {{ density: string, onDensityChange: function }} props
 */
export default function Topbar({ density, onDensityChange }) {
  const [dark, setDark] = useState(() => localStorage.getItem('theme') === 'dark');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    const saved = localStorage.getItem('density');
    if (saved && DENSITIES.includes(saved) && onDensityChange) {
      onDensityChange(saved);
    }
  }, []);

  function handleDensity(next) {
    localStorage.setItem('density', next);
    if (onDensityChange) onDensityChange(next);
    document.documentElement.setAttribute('data-density', next);
  }

  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 32px',
      borderBottom: '1px solid var(--rule)',
      background: 'var(--paper)',
      position: 'sticky', top: 0, zIndex: 10,
    }}>
      <PeakMark />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Density toggle */}
        {DENSITIES.map((d) => (
          <button
            key={d}
            className="icon-btn"
            title={d.charAt(0).toUpperCase() + d.slice(1)}
            onClick={() => handleDensity(d)}
            style={{
              width: 'auto', padding: '0 10px', fontSize: 11, fontWeight: 600,
              letterSpacing: '0.04em',
              background: density === d ? 'var(--accent-soft)' : undefined,
              color: density === d ? 'var(--accent-deep)' : undefined,
              borderColor: density === d
                ? 'color-mix(in oklab, var(--accent) 40%, transparent)'
                : undefined,
            }}
          >
            {d[0].toUpperCase()}
          </button>
        ))}

        {/* Dark mode toggle */}
        <button
          className="icon-btn"
          title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={() => setDark((d) => !d)}
          aria-pressed={dark}
        >
          {dark ? '☀' : '☾'}
        </button>
      </div>
    </header>
  );
}
