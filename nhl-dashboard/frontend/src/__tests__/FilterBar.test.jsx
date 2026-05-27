import { render, screen, fireEvent } from '@testing-library/react'
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

const PARTNERS = [
  { partner_id: 2, name: 'FanDuel',    bg_color: '#1493FF' },
  { partner_id: 3, name: 'DraftKings', bg_color: '#53d337' },
  { partner_id: 6, name: 'Unibet',     bg_color: '#007140' },
]

const partnerProps = {
  ...defaultProps,
  partners: PARTNERS,
  partnerId: 2,
  onPartnerChange: vi.fn(),
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

// ── OddsPartnerSelector (custom dropdown) ────────────────────────────────────

test('OddsPartnerSelector_renders_trigger_with_current_partner_name', () => {
  render(<FilterBar {...partnerProps} />)
  expect(screen.getByRole('button', { name: /FanDuel/i })).toBeInTheDocument()
})

test('OddsPartnerSelector_panel_is_hidden_before_trigger_click', () => {
  render(<FilterBar {...partnerProps} />)
  expect(screen.queryByText('ODDS SOURCE')).not.toBeInTheDocument()
})

test('OddsPartnerSelector_opens_panel_on_trigger_click', async () => {
  render(<FilterBar {...partnerProps} />)
  await userEvent.click(screen.getByRole('button', { name: /FanDuel/i }))
  expect(screen.getByText('ODDS SOURCE')).toBeInTheDocument()
})

test('OddsPartnerSelector_shows_all_partners_in_open_panel', async () => {
  render(<FilterBar {...partnerProps} />)
  await userEvent.click(screen.getByRole('button', { name: /FanDuel/i }))
  expect(screen.getByRole('option', { name: /FanDuel/i })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: /DraftKings/i })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: /Unibet/i })).toBeInTheDocument()
})

test('OddsPartnerSelector_calls_onChange_and_closes_panel_on_partner_select', async () => {
  const onChange = vi.fn()
  render(<FilterBar {...partnerProps} onPartnerChange={onChange} />)
  await userEvent.click(screen.getByRole('button', { name: /FanDuel/i }))
  await userEvent.click(screen.getByRole('option', { name: /DraftKings/i }))
  expect(onChange).toHaveBeenCalledWith(3)
  expect(screen.queryByText('ODDS SOURCE')).not.toBeInTheDocument()
})

test('OddsPartnerSelector_closes_panel_on_outside_click', async () => {
  render(<FilterBar {...partnerProps} />)
  await userEvent.click(screen.getByRole('button', { name: /FanDuel/i }))
  expect(screen.getByText('ODDS SOURCE')).toBeInTheDocument()
  fireEvent.mouseDown(document.body)
  expect(screen.queryByText('ODDS SOURCE')).not.toBeInTheDocument()
})
