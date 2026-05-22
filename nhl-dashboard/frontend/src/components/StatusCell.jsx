import LiveDot from './LiveDot';

const ET_FORMATTER = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
});

const ET_DATE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  month: 'short',
  day: 'numeric',
});

function etDateParts(isoString) {
  const d = new Date(isoString);
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(d);
  const get = (t) => parts.find((p) => p.type === t)?.value;
  return { year: +get('year'), month: +get('month'), day: +get('day') };
}

function todayEtParts() {
  return etDateParts(new Date().toISOString());
}

function contextLabel(isoString) {
  const game = etDateParts(isoString);
  const today = todayEtParts();
  if (game.year === today.year && game.month === today.month && game.day === today.day) {
    return 'TONIGHT';
  }
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tmr = etDateParts(tomorrow.toISOString());
  if (game.year === tmr.year && game.month === tmr.month && game.day === tmr.day) {
    return 'TOMORROW';
  }
  return ET_DATE_FORMATTER.format(new Date(isoString));
}

export default function StatusCell({ g, state }) {
  if (g.status === "final") {
    return (
      <div className="status-cell">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--muted)', fontWeight: 600, fontSize: 12, letterSpacing: '0.06em' }}>
          FINAL
        </span>
      </div>
    );
  }
  const isLive = state === 'live' && !!g.live;
  if (isLive) {
    return (
      <div className="status-cell">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--hot)', fontWeight: 600, fontSize: 12, letterSpacing: '0.04em' }}>
          <LiveDot /> LIVE
        </span>
        <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>
          {g.live.period} · {g.live.clock}
        </span>
      </div>
    );
  }
  if (!g.start) {
    return (
      <div className="status-cell">
        <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>—</span>
      </div>
    );
  }
  const timeET = ET_FORMATTER.format(new Date(g.start)) + ' ET';
  const label = contextLabel(g.start);
  return (
    <div className="status-cell">
      <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>{timeET}</span>
      <span style={{ fontSize: 11, color: 'var(--faint)', letterSpacing: '0.04em' }}>{label}</span>
    </div>
  );
}
