# Peak · NHL Dashboard — Developer Handoff

A live NHL games dashboard showing scores, moneyline odds, implied probabilities, and model "edge" calculations. Designed for desktop (1280px+).

This document describes the **target architecture** for a from-scratch implementation. The visual source of truth is `reference-dashboard.png` and the working prototype in `Dashboard.html` (React + custom CSS, all inline).

---

## 1. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | **Flask** (Python 3.11+) | Serves API, polls NHL, runs calculations |
| ORM | **Flask-SQLAlchemy** | Persists line history for sparklines |
| Database | **SQLite** | Zero-config, file-based, plenty for a single-user dashboard |
| Background jobs | **APScheduler** (in-process) | Polls NHL API every 15s for live games, every 5 min for slate |
| Frontend | **React 18 + Vite** | Matches the prototype; Vite dev server proxies to Flask |
| Styling | **Plain CSS** with CSS variables | Lifted directly from the prototype — no Tailwind, no UI library |
| Fonts | **Geist + Geist Mono** (Google Fonts) | Already in the prototype |
| HTTP client (frontend) | **Native `fetch`** + a small `useSWR`-like polling hook | Don't add axios |
| HTTP client (backend) | **`httpx`** | Async-friendly NHL API client |

**Deliberate non-choices:** No Tailwind, no shadcn/ui, no Next.js, no Redux, no TanStack Query, no websockets. Keep dependency surface small.

---

## 2. Folder layout

```
src/
├── app/                        # Flask application
│   ├── app.py                  # Flask app factory + route registration
│   ├── config.py               # Env-driven config (DB URL, poll intervals)
│   ├── models.py               # SQLAlchemy models
│   ├── nhl_client.py           # Wrapper around NHL API
│   ├── odds_client.py          # Wrapper around odds provider (TBD)
│   ├── services/
│   │   ├── slate.py            # Build today's game list + odds + edges
│   │   ├── live.py             # Live score/period/clock for in-progress games
│   │   └── implied.py          # Moneyline → implied probability + edge calc
│   ├── scheduler.py            # APScheduler: poll jobs
│   └── routes/
│       ├── games.py            # GET /api/games/today
│       ├── game_detail.py      # GET /api/games/<id>
│       └── health.py           # GET /api/health
└── components/
    └── dashboard/
        ├── index.html
        ├── vite.config.js      # Proxy /api → http://localhost:5000
        ├── package.json
        ├── src/
        │   ├── main.jsx
        │   ├── App.jsx
        │   ├── styles/
        │   │   ├── tokens.css  # CSS vars (lifted from prototype)
        │   │   └── app.css     # Component styles (lifted from prototype)
        │   ├── hooks/
        │   │   └── usePolling.js
        │   └── components/
        │       ├── Topbar.jsx
        │       ├── SlateTable.jsx
        │       ├── GameRow.jsx
        │       ├── MatchupCell.jsx
        │       ├── MoneylineCell.jsx
        │       ├── ImpliedBar.jsx
        │       ├── Sparkline.jsx
        │       ├── StatusCell.jsx
        │       ├── EdgeCell.jsx
        │       ├── TeamGlyph.jsx
        │       └── LiveDot.jsx
        └── public/
```

---

## 3. Data model (SQLAlchemy)

```python
class Team(db.Model):
    code = db.Column(db.String(3), primary_key=True)   # 'TOR'
    name = db.Column(db.String(64))                    # 'Maple Leafs'
    # record/L10 are derived from Game rows — don't denormalize here

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)       # NHL gamePk
    start_utc = db.Column(db.DateTime, index=True)
    venue = db.Column(db.String(120))
    away_code = db.Column(db.String(3), db.ForeignKey('team.code'))
    home_code = db.Column(db.String(3), db.ForeignKey('team.code'))
    status = db.Column(db.String(16))                  # 'scheduled' | 'live' | 'final'
    period = db.Column(db.String(8), nullable=True)    # '1st', '2nd', 'OT', 'SO'
    clock = db.Column(db.String(8), nullable=True)     # '12:34'
    away_score = db.Column(db.Integer, default=0)
    home_score = db.Column(db.Integer, default=0)
    away_sog = db.Column(db.Integer, default=0)
    home_sog = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime)

class OddsSnapshot(db.Model):
    """One row per (game, fetch_time). Powers the 24h sparkline."""
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), index=True)
    fetched_at = db.Column(db.DateTime, index=True)
    book = db.Column(db.String(32))                    # 'consensus' for v1
    away_ml = db.Column(db.Integer)                    # American odds, e.g. +120
    home_ml = db.Column(db.Integer)
    away_implied = db.Column(db.Float)                 # 0-100
    home_implied = db.Column(db.Float)

class ModelFair(db.Model):
    """The dashboard's "fair" probability — your own model output."""
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), primary_key=True)
    away_fair = db.Column(db.Float)                    # 0-100
    home_fair = db.Column(db.Float)
    computed_at = db.Column(db.DateTime)
```

**Sparkline data** comes from the last 24h of `OddsSnapshot` rows for a given game, downsampled to ~24 points server-side.

---

## 4. API endpoints

All return JSON. All under `/api/`.

### `GET /api/games/today`

Returns the slate for the current date in US Eastern time. **Polled by the frontend every 15s.**

```json
{
  "updated_at": "2026-05-16T19:42:11Z",
  "games": [
    {
      "id": 2026020812,
      "away": { "code": "TOR", "name": "Maple Leafs", "record": "24-18-4", "l10": "6-3-1" },
      "home": { "code": "BOS", "name": "Bruins",      "record": "30-15-6", "l10": "7-2-1" },
      "start": "2026-05-17T00:00:00Z",
      "venue": "TD Garden",
      "status": "live",
      "live": { "period": "2nd", "clock": "12:34", "away_score": 3, "home_score": 2, "away_sog": 18, "home_sog": 22 },
      "ml":     { "away": 120,  "home": -140 },
      "ml_open":{ "away": 115,  "home": -135 },
      "implied":{ "away": 45.0, "home": 55.0 },
      "fair":   { "away": 47.5, "home": 52.5 },
      "edge":   2.1,
      "movement_24h": [46.38, 44.95, 44.14, /* 24 points, away implied % */]
    }
  ]
}
```

### `GET /api/games/<id>`

Same shape as one row above, plus richer detail (goal scorers, period-by-period score) — not needed for v1 but stub the endpoint.

### `GET /api/health`

`{ "ok": true, "db": "connected", "last_poll": "..." }`

---

## 5. Background jobs (APScheduler)

Run inside the Flask process via `flask_apscheduler` or plain `BackgroundScheduler`.

| Job | Interval | What it does |
|---|---|---|
| `poll_slate` | every 5 min | Hits NHL schedule endpoint, upserts `Game` rows for today |
| `poll_live` | every 15 sec | For each `Game.status == 'live'`, hits NHL game-detail, updates score/clock/period/sog |
| `poll_odds` | every 5 min | Hits odds source (placeholder for now — see §7), inserts `OddsSnapshot` rows |
| `compute_fair` | every 5 min | Runs your fair-value model, upserts `ModelFair` |
| `prune_snapshots` | hourly | Deletes `OddsSnapshot` rows older than 7 days |

Start the scheduler in `app.py` only when `app.config['ENV'] != 'testing'`.

---

## 6. NHL API

Use the **public NHL Stats API** at `https://api-web.nhle.com/v1/`. No key required.

- Today's schedule: `GET /v1/schedule/now`
- Game detail (boxscore): `GET /v1/gamecenter/{gameId}/boxscore`
- Live play-by-play (if needed later): `GET /v1/gamecenter/{gameId}/play-by-play`
- Team logos: `https://assets.nhle.com/logos/nhl/svg/{CODE}_light.svg` — already used by the prototype's `TeamGlyph`

Cache successful responses for the polling interval in memory (`cachetools.TTLCache`) so a reload doesn't hammer the API.

---

## 7. Odds source

**Not part of v1 scope** — leave the `odds_client.py` as a stub that returns the same values every call. The frontend will render perfectly.

When ready, options:
- **The Odds API** (`the-odds-api.com`) — free tier, 500 req/month
- **OddsJam / Pinnacle** — paid

Document the chosen provider's response shape in `odds_client.py` and map to the `OddsSnapshot` row shape.

---

## 8. Implied probability + edge math

In `services/implied.py`:

```python
def american_to_implied(odds: int) -> float:
    """+120 → 45.45, -140 → 58.33"""
    if odds > 0:
        return 100 / (odds + 100) * 100
    return -odds / (-odds + 100) * 100

def devig_two_way(p_away: float, p_home: float) -> tuple[float, float]:
    """Both sides usually sum > 100 (vig). Normalize."""
    total = p_away + p_home
    return p_away / total * 100, p_home / total * 100

def edge(fair_pct: float, market_pct: float) -> float:
    """Positive edge = model thinks side is more likely than market prices."""
    return fair_pct - market_pct
```

For v1, the "fair" probability can simply be `de-vigged market implied ± a small adjustment` until you build a real model.

---

## 9. Frontend conventions

- **Polling hook** (`usePolling.js`): wraps `fetch`, accepts `{ url, interval }`, returns `{ data, error, loading }`. Pauses when the tab is hidden (`document.visibilityState`).
- **No global state library.** `App.jsx` calls `usePolling('/api/games/today', 15000)` and passes `games` down via props.
- **Density / dark mode** can stay client-side (localStorage) — they don't need a server round-trip.
- **CSS variables** in `styles/tokens.css` drive both light and dark themes (toggle a `.dark` class on `<html>`).
- All number formatting goes through one helper (`formatAmerican`, `formatPct`) so the prototype's `mono tnum` look stays consistent.

### Components to lift verbatim from the prototype

These render exactly as-is. Copy the JSX and styles:

- `PeakMark`, `TeamGlyph`, `LiveDot`
- `Sparkline` (SVG, no library)
- `ImpliedBar` (the headline two-tone bar)
- `StatusCell`, `MatchupCell`, `MoneylineCell`, `SparklineCell`, `EdgeCell`
- The table row layout (CSS Grid with named columns)

---

## 10. Out of scope for v1

- Auth / multi-user
- Mobile / responsive layout (desktop-only, 1280px+)
- Player props, totals, puck-line — moneyline only
- Bet tracking / bankroll
- Push notifications / websockets
- Production deployment (run with `flask run` + `npm run dev` locally)

---

## 11. Definition of done

- [ ] `flask run` starts backend on :5000, scheduler kicks off polling
- [ ] `npm run dev` starts Vite on :5173, proxies `/api` to :5000
- [ ] Opening localhost:5173 shows today's NHL slate, matching `reference-dashboard.png`
- [ ] Live games show animated score updates within 15s of the real-world play
- [ ] Sparklines render 24h of `OddsSnapshot` data per game
- [ ] Dark mode toggle in topbar works
- [ ] `flask db upgrade` (or `db.create_all()`) bootstraps SQLite
