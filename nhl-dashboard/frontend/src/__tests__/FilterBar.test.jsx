import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import FilterBar from '../components/FilterBar';

describe('FilterBar', () => {
  it('renders game count from games prop', () => {
    const games = [
      { id: 1, status: 'scheduled' },
      { id: 2, status: 'scheduled' },
      { id: 3, status: 'final' },
    ];
    const { container } = render(<FilterBar games={games} />);
    expect(container.textContent).toContain('3 games');
  });

  it('renders live count when games have status live', () => {
    const games = [
      { id: 1, status: 'live' },
      { id: 2, status: 'live' },
      { id: 3, status: 'live' },
    ];
    const { container } = render(<FilterBar games={games} />);
    expect(container.textContent).toContain('3 in progress');
  });

  it('omits live count when no games are live', () => {
    const games = [{ id: 1, status: 'scheduled' }, { id: 2, status: 'final' }];
    const { container } = render(<FilterBar games={games} />);
    expect(container.textContent).not.toContain('in progress');
  });
});
