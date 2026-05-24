import { render } from '@testing-library/react'
import App from '../App.jsx'

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ games: [], updated_at: null }),
    })
  )
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('App_renders_without_crashing', () => {
  render(<App />)
})
