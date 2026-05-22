import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import EdgeCell from '../components/EdgeCell';

describe('EdgeCell', () => {
  it('renders with edge-positive class when edge > 0', () => {
    const { container } = render(<EdgeCell edge={2.5} />);
    expect(container.querySelector('.edge-positive')).toBeTruthy();
  });

  it('does not render edge-positive class when edge is negative', () => {
    const { container } = render(<EdgeCell edge={-1.5} />);
    expect(container.querySelector('.edge-positive')).toBeNull();
  });

  it('renders the formatted edge value with + prefix for positive edge', () => {
    const { container } = render(<EdgeCell edge={2.5} />);
    expect(container.textContent).toContain('+2.5%');
  });

  it('renders dash when edge is null', () => {
    const { container } = render(<EdgeCell edge={null} />);
    expect(container.textContent).toContain('—');
  });
});
