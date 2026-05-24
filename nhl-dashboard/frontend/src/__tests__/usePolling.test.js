import { renderHook, act } from '@testing-library/react'
import { usePolling } from '../hooks/usePolling'

const TEST_URL = '/api/games/today'
const INTERVAL = 30000

beforeEach(() => {
  vi.useFakeTimers()
  Object.defineProperty(document, 'visibilityState', {
    value: 'visible',
    writable: true,
    configurable: true,
  })
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ games: [] }),
    })
  )
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

test('usePolling_fetch_called_exactly_once_on_mount', async () => {
  renderHook(() => usePolling(TEST_URL, INTERVAL))

  await act(async () => {})

  expect(global.fetch).toHaveBeenCalledTimes(1)
  expect(global.fetch).toHaveBeenCalledWith(TEST_URL)
})

test('usePolling_fetch_called_second_time_after_interval_elapses', async () => {
  renderHook(() => usePolling(TEST_URL, INTERVAL))

  await act(async () => {})
  expect(global.fetch).toHaveBeenCalledTimes(1)

  await act(async () => {
    vi.advanceTimersByTime(INTERVAL)
  })

  expect(global.fetch).toHaveBeenCalledTimes(2)
})

test('usePolling_no_timer_fires_after_unmount', async () => {
  const { unmount } = renderHook(() => usePolling(TEST_URL, INTERVAL))

  await act(async () => {})
  expect(global.fetch).toHaveBeenCalledTimes(1)

  unmount()

  await act(async () => {
    vi.advanceTimersByTime(60000)
  })

  expect(global.fetch).toHaveBeenCalledTimes(1)
})

test('usePolling_exposes_error_state_on_fetch_failure', async () => {
  global.fetch = vi.fn(() => Promise.reject(new Error('Network error')))

  const { result } = renderHook(() => usePolling(TEST_URL, INTERVAL))

  await act(async () => {})

  expect(result.current.error).toBe('Network error')
  expect(result.current.loading).toBe(false)
})
