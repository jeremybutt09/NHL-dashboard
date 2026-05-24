import { render, screen } from '@testing-library/react'
import { SlateTable } from '../components/SlateTable.jsx'

const mockGame = {
  id: 'game-1',
  status: 'live',
  start: '2026-05-23T19:00:00Z',
  live: {
    period: '2nd',
    clock: '14:00',
    away_score: 2,
    home_score: 1,
  },
  away: {
    code: 'BOS',
    name: 'Boston Bruins',
    record: '40-25-5',
    l10: '7-3-0',
  },
  home: {
    code: 'TOR',
    name: 'Toronto Maple Leafs',
    record: '38-26-6',
    l10: '6-4-0',
  },
  ml: {
    away: 110,
    home: -110,
  },
  ml_open: {
    away: 100,
    home: -120,
  },
  implied: {
    away: 47.6,
    home: 52.4,
  },
  edge: 3,
  movement_24h: [47, 48, 47.6],
}

test('SlateTable_live_game_renders_all_key_fields', () => {
  render(<SlateTable games={[mockGame]} loading={false} />)

  expect(screen.getByText('BOS')).toBeInTheDocument()
  expect(screen.getByText('TOR')).toBeInTheDocument()
  expect(screen.getAllByText('2').length).toBeGreaterThan(0)
  expect(screen.getAllByText('1').length).toBeGreaterThan(0)
  expect(screen.getByText(/2nd/)).toBeInTheDocument()
  expect(screen.getByText(/14:00/)).toBeInTheDocument()
  expect(screen.getByText('-110')).toBeInTheDocument()
  expect(screen.getByText('+3.0%')).toBeInTheDocument()
})

test('SlateTable_final_game_shows_FINAL_status_not_clock', () => {
  const finalGame = { ...mockGame, id: 'game-2', status: 'final' }
  render(<SlateTable games={[finalGame]} loading={false} />)

  expect(screen.getByText('FINAL')).toBeInTheDocument()
  expect(screen.queryByText(/14:00/)).not.toBeInTheDocument()
})

test('SlateTable_empty_array_shows_placeholder_message', () => {
  render(<SlateTable games={[]} loading={false} />)

  expect(screen.getByText('No NHL games today')).toBeInTheDocument()
  expect(document.querySelector('.game-row')).not.toBeInTheDocument()
})
