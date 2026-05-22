import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatStrip from '../components/StatStrip';

describe('StatStrip', () => {
  it('renders correct +EV opportunities count', () => {
    const games = [
      { edge: 2.5, status: 'scheduled', implied: { away: 50 } },
      { edge: -1.0, status: 'scheduled', implied: { away: 50 } },
      { edge: 3.0, status: 'scheduled', implied: { away: 50 } },
    ];
    render(<StatStrip games={games} />);
    // 2 games have positive edge (2.5 and 3.0)
    const label = screen.getByText('+EV opportunities');
    expect(label.parentElement.textContent).toContain('2');
  });

  it('renders zero +EV opportunities when no games have positive edge', () => {
    const games = [
      { edge: -1.0, status: 'scheduled', implied: { away: 50 } },
      { edge: -0.5, status: 'scheduled', implied: { away: 50 } },
    ];
    render(<StatStrip games={games} />);
    const label = screen.getByText('+EV opportunities');
    expect(label.parentElement.textContent).toContain('0');
  });
});
