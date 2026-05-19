import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import SlateTable from '../../nhl-dashboard/frontend/src/components/SlateTable.jsx';

// Mock usePolling before importing App so the factory is hoisted correctly.
vi.mock('../../nhl-dashboard/frontend/src/hooks/usePolling.js', () => ({
  default: vi.fn(() => ({ data: null, loading: false, error: null })),
}));

import usePolling from '../../nhl-dashboard/frontend/src/hooks/usePolling.js';
import App from '../../nhl-dashboard/frontend/src/App.jsx';

// ── SlateTable: empty state ───────────────────────────────────────────────────

describe('SlateTable empty state', () => {
  it('SlateTable_renders_empty_state_when_no_games_and_not_loading', () => {
    render(<SlateTable games={[]} loading={false} error={null} />);
    expect(screen.getByText('No games scheduled today.')).toBeTruthy();
  });

  it('SlateTable_does_not_render_empty_state_when_loading', () => {
    render(<SlateTable games={[]} loading={true} error={null} />);
    expect(screen.queryByText('No games scheduled today.')).toBeNull();
  });
});

// ── SlateTable: loading skeletons ─────────────────────────────────────────────

describe('SlateTable loading skeletons', () => {
  it('SlateTable_renders_3_skeleton_rows_when_loading', () => {
    const { container } = render(
      <SlateTable games={[]} loading={true} error={null} />,
    );
    const skeletons = container.querySelectorAll('.bar-shimmer');
    expect(skeletons.length).toBe(3);
  });

  it('SlateTable_does_not_render_skeletons_when_not_loading', () => {
    const { container } = render(
      <SlateTable games={[]} loading={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.bar-shimmer');
    expect(skeletons.length).toBe(0);
  });
});

// ── Error toast ───────────────────────────────────────────────────────────────

describe('Error toast', () => {
  beforeEach(() => {
    vi.mocked(usePolling).mockReturnValue({ data: null, loading: false, error: null });
    try { localStorage.clear(); } catch {}
  });

  it('App_renders_error_toast_when_error_is_non_null', () => {
    vi.mocked(usePolling).mockReturnValue({
      data: null,
      loading: false,
      error: new Error('Network error'),
    });
    render(<App />);
    expect(screen.getByText('Connection lost — retrying...')).toBeTruthy();
  });

  it('App_does_not_render_error_toast_when_error_is_null', () => {
    vi.mocked(usePolling).mockReturnValue({ data: null, loading: false, error: null });
    render(<App />);
    expect(screen.queryByText('Connection lost — retrying...')).toBeNull();
  });
});

// ── Density toggle ────────────────────────────────────────────────────────────

describe('Density toggle', () => {
  beforeEach(() => {
    vi.mocked(usePolling).mockReturnValue({ data: null, loading: false, error: null });
    try { localStorage.clear(); } catch {}
  });

  it('App_applies_density_compact_class_when_compact_button_clicked', () => {
    const { container } = render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /compact/i }));
    expect(container.querySelector('.density-compact')).toBeTruthy();
  });

  it('App_applies_density_regular_class_when_regular_button_clicked', () => {
    const { container } = render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /regular/i }));
    expect(container.querySelector('.density-regular')).toBeTruthy();
  });

  it('App_applies_density_comfy_class_when_comfy_button_clicked', () => {
    const { container } = render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /comfy/i }));
    expect(container.querySelector('.density-comfy')).toBeTruthy();
  });
});
