import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FilterBar } from '../components/FilterBar.jsx'

const defaultProps = {
  numGames: 5,
  totalGames: 5,
  liveCount: 0,
  market: 'h2h',
  onMarketChange: vi.fn(),
  day: 'today',
}

test('FilterBar_renders_all_market_tab_labels', () => {
  render(<FilterBar {...defaultProps} />)
  expect(screen.getByText('Moneyline')).toBeInTheDocument()
  expect(screen.getByText('Puck Line')).toBeInTheDocument()
  expect(screen.getByText('Total (O/U)')).toBeInTheDocument()
})

test('FilterBar_calls_onMarketChange_when_tab_clicked', async () => {
  const onChange = vi.fn()
  render(<FilterBar {...defaultProps} onMarketChange={onChange} />)
  await userEvent.click(screen.getByText('Puck Line'))
  expect(onChange).toHaveBeenCalledWith('spreads')
})

test('FilterBar_highlights_active_market_tab', () => {
  render(<FilterBar {...defaultProps} market="spreads" />)
  expect(screen.getByRole('button', { name: 'Puck Line' })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByRole('button', { name: 'Moneyline' })).toHaveAttribute('aria-pressed', 'false')
  expect(screen.getByRole('button', { name: 'Total (O/U)' })).toHaveAttribute('aria-pressed', 'false')
})
