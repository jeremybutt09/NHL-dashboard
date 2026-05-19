import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import usePolling from '../../nhl-dashboard/frontend/src/hooks/usePolling.js';

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    });
  });

  it('usePolling_returns_loading_true_data_null_error_null_on_first_render', () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ games: [] }),
    });

    const { result } = renderHook(() => usePolling('/api/games/today', 15000));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('usePolling_returns_loading_false_with_data_after_successful_fetch', async () => {
    const mockData = { games: [{ id: 1 }] };
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const { result } = renderHook(() => usePolling('/api/games/today', 15000));

    // Flush the mocked fetch promise chain (microtasks) without advancing fake timers
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('usePolling_does_not_call_fetch_while_visibility_is_hidden', async () => {
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });

    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });

    renderHook(() => usePolling('/api/games/today', 15000));

    await act(async () => {
      vi.advanceTimersByTime(60000);
    });

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('usePolling_calls_fetch_after_visibilitychange_to_visible', async () => {
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });

    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });

    renderHook(() => usePolling('/api/games/today', 15000));

    expect(fetchSpy).not.toHaveBeenCalled();

    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    });

    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(fetchSpy).toHaveBeenCalledOnce();
  });
});
