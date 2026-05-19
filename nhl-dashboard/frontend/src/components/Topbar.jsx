import { useState, useEffect } from 'react';

function PeakMark() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <rect width="28" height="28" rx="6" fill="var(--accent)" />
        <path d="M7 20 L14 8 L21 20" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <path d="M10 15.5 L18 15.5" stroke="white" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 15, letterSpacing: '-0.01em', color: 'var(--ink)' }}>Peak</span>
        <span style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 500 }}>NHL</span>
      </div>
    </div>
  );
}

function MoonIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M13.5 10A6 6 0 0 1 6 2.5a6 6 0 1 0 7.5 7.5z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.5 1.5M11.5 11.5L13 13M3 13l1.5-1.5M11.5 4.5L13 3" />
    </svg>
  );
}

const DENSITIES = ['Compact', 'Regular', 'Comfy'];

/**
 * App topbar: Peak logo, density toggle, and dark mode toggle.
 *
 * @param {{ density: string, onDensityChange: (d: string) => void }} props
 */
export default function Topbar({ density = 'regular', onDensityChange }) {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('theme') === 'dark'; } catch { return false; }
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch {}
  }, [dark]);

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '14px 32px',
      borderBottom: '1px solid var(--rule)',
      background: 'var(--paper)',
      position: 'sticky',
      top: 0,
      zIndex: 10,
    }}>
      <PeakMark />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Density toggle */}
        <div style={{ display: 'flex', gap: 2 }}>
          {DENSITIES.map((label) => {
            const value = label.toLowerCase();
            const active = density === value;
            return (
              <button
                key={value}
                aria-label={label}
                aria-pressed={active}
                onClick={() => onDensityChange?.(value)}
                style={{
                  background: active ? 'var(--accent-soft)' : 'transparent',
                  border: '1px solid',
                  borderColor: active
                    ? 'color-mix(in oklab, var(--accent) 40%, transparent)'
                    : 'var(--rule)',
                  borderRadius: 6,
                  padding: '4px 10px',
                  fontSize: 12,
                  fontWeight: active ? 600 : 500,
                  color: active ? 'var(--accent-deep)' : 'var(--muted)',
                  cursor: 'pointer',
                  letterSpacing: '0.01em',
                  transition: 'all .12s ease',
                }}
              >
                {label}
              </button>
            );
          })}
        </div>

        {/* Dark mode toggle */}
        <button
          className="icon-btn"
          aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={() => setDark(d => !d)}
        >
          {dark ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </header>
  );
}
