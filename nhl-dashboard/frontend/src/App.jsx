import { useState, useEffect, useCallback, useRef } from 'react'
import { Topbar }     from './components/Topbar.jsx'
import { FilterBar }  from './components/FilterBar.jsx'
import { StatStrip }  from './components/StatStrip.jsx'
import { SlateTable } from './components/SlateTable.jsx'

// ── Date helpers ──────────────────────────────────────────────────────────────
// en-CA locale produces YYYY-MM-DD, which is what game_date keys use.
function todayKey() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' })
}
function addDays(key, n) {
  const d = new Date(key + 'T12:00:00')
  d.setDate(d.getDate() + n)
  return d.toLocaleDateString('en-CA', { timeZone: 'America/New_York' })
}

export default function App() {
  // ── Dark mode ─────────────────────────────────────────────────────────────
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('peak-dark') === '1' } catch { return false }
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem('peak-dark', dark ? '1' : '0') } catch {}
  }, [dark])

  // ── Density ───────────────────────────────────────────────────────────────
  const [density, setDensity] = useState(() => {
    try { return localStorage.getItem('peak-density') || 'regular' } catch { return 'regular' }
  })
  useEffect(() => {
    try { localStorage.setItem('peak-density', density) } catch {}
  }, [density])

  // ── Market ────────────────────────────────────────────────────────────────
  const [market, setMarket] = useState('h2h')

  // ── Sportsbook partner selection ──────────────────────────────────────────
  const [partners, setPartners] = useState([])
  const [partnerId, setPartnerId] = useState(null)

  useEffect(() => {
    fetch('/api/partners')
      .then(r => r.ok ? r.json() : [])
      .then(list => {
        setPartners(list)
        if (list.length > 0 && partnerId === null) {
          setPartnerId(list[0].partner_id)
        }
      })
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Day navigation ────────────────────────────────────────────────────────
  const [day, setDay] = useState('today')

  // ── Data polling ──────────────────────────────────────────────────────────
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const timerRef = useRef(null)

  const fetchGames = useCallback(async () => {
    if (document.visibilityState === 'hidden') return
    try {
      // Resolve the day nav state to a YYYY-MM-DD string for the backend filter
      let targetDate = null
      if (day === 'today') {
        targetDate = null  // let the backend use its own today_et()
      } else if (day === 'tomorrow') {
        targetDate = addDays(todayKey(), 1)
      } else {
        targetDate = day  // already a YYYY-MM-DD key from the calendar picker
      }

      const params = new URLSearchParams()
      if (partnerId != null) params.set('partner_id', String(partnerId))
      if (targetDate != null) params.set('date', targetDate)
      const qs = params.toString()
      const url = qs ? `/api/games/today?${qs}` : '/api/games/today'

      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setUpdatedAt(json.updated_at ? new Date(json.updated_at).getTime() : Date.now())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [partnerId, day])

  useEffect(() => {
    fetchGames()
    timerRef.current = setInterval(fetchGames, 15000)
    const onVis = () => { if (document.visibilityState === 'visible') fetchGames() }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      clearInterval(timerRef.current)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [fetchGames])

  // ── Derived state ─────────────────────────────────────────────────────────
  const allGames = data?.games ?? []

  const games = allGames

  // Game counts per day key (for the nav badges)
  const todayK = todayKey()
  const resolvedKey = day === 'today' ? todayK : day === 'tomorrow' ? addDays(todayK, 1) : (day || todayK)
  const gameCounts = { [resolvedKey]: games.length }
  const liveCount  = games.filter(g => g.status === 'live').length

  // ── Error toast ───────────────────────────────────────────────────────────
  const [showToast, setShowToast] = useState(false)
  useEffect(() => {
    if (error) {
      setShowToast(true)
      const t = setTimeout(() => setShowToast(false), 6000)
      return () => clearTimeout(t)
    } else {
      setShowToast(false)
    }
  }, [error])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', minWidth: 1280 }}>

      {/* ── Top navigation bar ─────────────────────────────────────────── */}
      <Topbar
        dark={dark}
        onDarkToggle={() => setDark(d => !d)}
        density={density}
        onDensityChange={setDensity}
        liveCount={liveCount}
        loading={loading}
        error={error}
        updatedAt={updatedAt}
        onRefresh={fetchGames}
        day={day}
        onDayChange={setDay}
        gameCounts={gameCounts}
      />

      {/* ── "Tonight's slate" heading + market tabs ────────────────────── */}
      <FilterBar
        numGames={games.length}
        totalGames={allGames.length}
        liveCount={liveCount}
        market={market}
        onMarketChange={setMarket}
        day={day}
        partners={partners}
        partnerId={partnerId}
        onPartnerChange={setPartnerId}
      />

      {/* ── Inline error banner ────────────────────────────────────────── */}
      {error && (
        <div style={{
          margin: '0 32px 8px', padding: '12px 16px',
          background: 'var(--hot-soft)', color: 'var(--hot)',
          border: '1px solid color-mix(in oklab, var(--hot) 35%, transparent)',
          borderRadius: 10, fontSize: 12, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <strong>API error.</strong>
          <span style={{ fontWeight: 400 }}>{error}</span>
          <button onClick={fetchGames} style={{
            marginLeft: 'auto', background: 'var(--hot)', color: 'white',
            border: 'none', borderRadius: 6, padding: '5px 12px',
            fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}>Retry</button>
        </div>
      )}

      {/* ── Aggregate stat cards ───────────────────────────────────────── */}
      {games.length > 0 && <StatStrip games={games} />}

      {/* ── Slate table ────────────────────────────────────────────────── */}
      <div style={{ padding: '0 32px 48px' }}>
        <SlateTable games={games} loading={loading} density={density} />

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          padding: '14px 4px',
          fontSize: 11, color: 'var(--faint)', letterSpacing: '0.04em',
        }}>
          <span>
            Showing {games.length} of {allGames.length} game{allGames.length !== 1 ? 's' : ''} ·
            {' '}NHL API · polling every 15s
          </span>
          {updatedAt && (
            <span className="mono">
              Last updated {new Date(updatedAt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}
            </span>
          )}
        </div>
      </div>

      {/* ── Error toast ────────────────────────────────────────────────── */}
      {showToast && (
        <div className="toast">
          <strong>Connection error</strong>
          <span style={{ fontWeight: 400, fontSize: 12 }}>{error}</span>
          <button
            onClick={fetchGames}
            style={{
              background: 'var(--hot)', color: 'white',
              border: 'none', borderRadius: 6,
              padding: '4px 10px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Retry
          </button>
          <button onClick={() => setShowToast(false)} style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: 'var(--hot)', fontWeight: 700, fontSize: 14, padding: 0,
          }}>✕</button>
        </div>
      )}
    </div>
  )
}
