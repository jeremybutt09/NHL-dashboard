import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

import TeamGlyph from '../../nhl-dashboard/frontend/src/components/TeamGlyph.jsx';
import LiveDot from '../../nhl-dashboard/frontend/src/components/LiveDot.jsx';
import Sparkline from '../../nhl-dashboard/frontend/src/components/Sparkline.jsx';
import ImpliedBar from '../../nhl-dashboard/frontend/src/components/ImpliedBar.jsx';
import StatusCell from '../../nhl-dashboard/frontend/src/components/StatusCell.jsx';
import MatchupCell from '../../nhl-dashboard/frontend/src/components/MatchupCell.jsx';
import MoneylineCell from '../../nhl-dashboard/frontend/src/components/MoneylineCell.jsx';
import SparklineCell from '../../nhl-dashboard/frontend/src/components/SparklineCell.jsx';
import EdgeCell from '../../nhl-dashboard/frontend/src/components/EdgeCell.jsx';

const SERIES = [45, 46, 44, 47, 48, 46, 50, 49, 51, 50, 52, 51, 53, 52, 54, 53, 55, 54, 56, 55, 57, 56, 58, 57];

const MOCK_GAME = {
  away: 'TOR',
  home: 'MTL',
  awayName: 'Toronto Maple Leafs',
  homeName: 'Montreal Canadiens',
  awayRec: '30-20-5',
  homeRec: '25-25-5',
  awayL10: '6-4',
  homeL10: '5-5',
  start: '7:00 PM ET',
  tz: 'ET',
  ml: { a: '+120', h: '-140' },
  mlOpen: { a: '+110', h: '-130' },
  ip: { a: 45.5, h: 54.5 },
  edge: 2.3,
  live: null,
};

const MOCK_GAME_LIVE = {
  ...MOCK_GAME,
  live: { period: 'P2', clock: '12:34', as: 2, hs: 1 },
};

// ── TeamGlyph ────────────────────────────────────────────────────────────────
describe('TeamGlyph', () => {
  it('renders_logo_img_with_valid_code', () => {
    const { container } = render(<TeamGlyph code="TOR" />);
    const img = container.querySelector('img');
    expect(img).toBeTruthy();
    expect(img.src).toContain('TOR');
  });

  it('renders_chip_fallback_when_img_errors', () => {
    const { container } = render(<TeamGlyph code="TOR" />);
    const img = container.querySelector('img');
    fireEvent.error(img);
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).toContain('TOR');
  });
});

// ── LiveDot ──────────────────────────────────────────────────────────────────
describe('LiveDot', () => {
  it('renders_dot_element', () => {
    const { container } = render(<LiveDot />);
    expect(container.firstChild).toBeTruthy();
  });
});

// ── Sparkline ────────────────────────────────────────────────────────────────
describe('Sparkline', () => {
  it('renders_svg_with_24_data_points', () => {
    const { container } = render(<Sparkline data={SERIES} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    const path = container.querySelector('path');
    expect(path).toBeTruthy();
  });
});

// ── ImpliedBar ───────────────────────────────────────────────────────────────
describe('ImpliedBar', () => {
  it('renders_two_tone_bar', () => {
    const { container } = render(
      <ImpliedBar ipA={45} ipH={55} awayCode="TOR" homeCode="MTL" live={false} />
    );
    expect(container.firstChild).toBeTruthy();
  });

  it('adds_shimmer_class_when_live', () => {
    const { container } = render(
      <ImpliedBar ipA={45} ipH={55} awayCode="TOR" homeCode="MTL" live={true} />
    );
    expect(container.innerHTML).toContain('bar-shimmer');
  });

  it('omits_shimmer_class_when_not_live', () => {
    const { container } = render(
      <ImpliedBar ipA={45} ipH={55} awayCode="TOR" homeCode="MTL" live={false} />
    );
    expect(container.innerHTML).not.toContain('bar-shimmer');
  });
});

// ── StatusCell ───────────────────────────────────────────────────────────────
describe('StatusCell', () => {
  it('renders_scheduled_time_when_not_live', () => {
    render(<StatusCell g={MOCK_GAME} state="scheduled" />);
    expect(screen.getByText('7:00 PM ET')).toBeTruthy();
  });

  it('renders_live_indicator_when_live', () => {
    render(<StatusCell g={MOCK_GAME_LIVE} state="live" />);
    expect(screen.getByText('LIVE')).toBeTruthy();
    expect(screen.getByText('P2 · 12:34')).toBeTruthy();
  });

  it('livedot_not_rendered_when_status_not_live', () => {
    const { container } = render(<StatusCell g={MOCK_GAME} state="scheduled" />);
    expect(container.querySelector('.live-dot')).toBeNull();
  });
});

// ── MatchupCell ───────────────────────────────────────────────────────────────
describe('MatchupCell', () => {
  it('renders_both_team_codes', () => {
    render(<MatchupCell g={MOCK_GAME} state="scheduled" density="regular" />);
    expect(screen.getAllByText('TOR').length).toBeGreaterThan(0);
    expect(screen.getAllByText('MTL').length).toBeGreaterThan(0);
  });

  it('renders_records_for_both_teams', () => {
    render(<MatchupCell g={MOCK_GAME} state="scheduled" density="regular" />);
    expect(screen.getByText('30-20-5')).toBeTruthy();
    expect(screen.getByText('25-25-5')).toBeTruthy();
  });
});

// ── MoneylineCell ─────────────────────────────────────────────────────────────
describe('MoneylineCell', () => {
  it('renders_away_and_home_odds', () => {
    render(<MoneylineCell g={MOCK_GAME} state="scheduled" />);
    expect(screen.getByText('+120')).toBeTruthy();
    expect(screen.getByText('-140')).toBeTruthy();
  });

  it('applies_positive_class_to_plus_odds', () => {
    const { container } = render(<MoneylineCell g={MOCK_GAME} state="scheduled" />);
    const positiveEl = container.querySelector('.positive');
    expect(positiveEl).toBeTruthy();
    expect(positiveEl.textContent).toContain('+120');
  });

  it('applies_negative_class_to_minus_odds', () => {
    const { container } = render(<MoneylineCell g={MOCK_GAME} state="scheduled" />);
    const negativeEl = container.querySelector('.negative');
    expect(negativeEl).toBeTruthy();
    expect(negativeEl.textContent).toContain('-140');
  });
});

// ── SparklineCell ─────────────────────────────────────────────────────────────
describe('SparklineCell', () => {
  it('renders_with_series_data', () => {
    const { container } = render(<SparklineCell series={SERIES} delta={1.2} />);
    expect(container.firstChild).toBeTruthy();
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('shows_delta_label', () => {
    render(<SparklineCell series={SERIES} delta={1.2} />);
    expect(screen.getByText('24H · IMPLIED %')).toBeTruthy();
  });
});

// ── EdgeCell ──────────────────────────────────────────────────────────────────
describe('EdgeCell', () => {
  it('renders_edge_value_with_sign', () => {
    render(<EdgeCell edge={2.3} />);
    expect(screen.getByText('+2.3%')).toBeTruthy();
  });

  it('applies_positive_class_when_edge_positive', () => {
    const { container } = render(<EdgeCell edge={2.3} />);
    expect(container.querySelector('.positive')).toBeTruthy();
  });

  it('applies_negative_class_when_edge_negative', () => {
    const { container } = render(<EdgeCell edge={-1.5} />);
    expect(container.querySelector('.negative')).toBeTruthy();
  });

  it('renders_negative_edge_value', () => {
    render(<EdgeCell edge={-1.5} />);
    expect(screen.getByText('-1.5%')).toBeTruthy();
  });
});
