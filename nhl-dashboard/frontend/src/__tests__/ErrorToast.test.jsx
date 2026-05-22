import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ErrorToast from '../components/ErrorToast';

describe('ErrorToast', () => {
  it('renders the error message', () => {
    render(<ErrorToast error={new Error('API timeout')} onDismiss={() => {}} />);
    expect(screen.getByText(/API timeout/)).toBeTruthy();
  });

  it('calls onDismiss callback when dismiss button is clicked', () => {
    const onDismiss = vi.fn();
    render(<ErrorToast error={new Error('fail')} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('shows fallback message when error has no message', () => {
    const { container } = render(
      <ErrorToast error={{}} onDismiss={() => {}} />,
    );
    expect(container.textContent).toContain('Network error');
  });
});
