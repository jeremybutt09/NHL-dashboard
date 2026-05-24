import { render, screen } from '@testing-library/react'
import { Topbar } from '../components/Topbar.jsx'

const defaultProps = {
  dark: false,
  onDarkToggle: vi.fn(),
  liveCount: 0,
  loading: false,
  error: null,
  updatedAt: null,
  onRefresh: vi.fn(),
  day: 'today',
  onDayChange: vi.fn(),
  gameCounts: {},
  density: 'regular',
  onDensityChange: vi.fn(),
}

test('Topbar_renders_app_branding', () => {
  render(<Topbar {...defaultProps} />)
  expect(screen.getByText('Peak')).toBeInTheDocument()
})
