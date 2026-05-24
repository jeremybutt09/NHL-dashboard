# Frontend Architecture

React 18 single-page application built with Vite. Entry point: `nhl-dashboard/frontend/src/main.jsx`. All source lives under `nhl-dashboard/frontend/src/`.

---

## Component Tree

```
App                          (src/App.jsx)
├── Topbar                   (src/components/Topbar.jsx)
│   ├── PeakMark             (internal — brand wordmark)
│   ├── ApiStatusPill        (internal — live/updating/error pill)
│   ├── DensityToggle        (internal — compact/regular/comfy row selector)
│   └── CalendarPopover      (internal — date picker popover)
├── FilterBar                (src/components/FilterBar.jsx)
│   ├── OddsPartnerSelector  (internal — book selector stub)
│   └── SegmentButton        (internal — sort control)
├── StatStrip                (src/components/StatStrip.jsx)
└── SlateTable               (src/components/SlateTable.jsx)
    ├── ColumnHeader         (internal — sticky header row)
    ├── SkeletonRows         (internal — loading placeholder)
    ├── EmptyState           (internal — no games message)
    └── GameRow              (src/components/GameRow.jsx)
        ├── StatusCell       (src/components/StatusCell.jsx)
        │   └── LiveDot      (src/components/LiveDot.jsx)
        ├── MatchupCell      (src/components/MatchupCell.jsx)
        │   └── TeamGlyph    (src/components/TeamGlyph.jsx)
        ├── MoneylineCell    (src/components/MoneylineCell.jsx)
        │   └── ImpliedBar   (src/components/ImpliedBar.jsx)
        ├── SparklineCell    (src/components/SparklineCell.jsx)
        │   └── Sparkline    (src/components/Sparkline.jsx)
        └── EdgeCell         (src/components/EdgeCell.jsx)
```

All state lives in `App`. Child components are purely presentational — they receive data via props and do not fetch or mutate state.

---

## Props Reference

### `App`

No external props. Owns all application state and passes slices down to children.

| State variable | Type | Description |
|---|---|---|
| `dark` | `boolean` | Dark mode active. Persisted to `localStorage` under key `peak-dark`. |
| `density` | `'compact' \| 'regular' \| 'comfy'` | Row height mode. Persisted under `peak-density`. |
| `market` | `'h2h' \| 'spreads' \| 'totals'` | Active odds market tab. |
| `day` | `'today' \| 'tomorrow' \| string` | Selected date key (`YYYY-MM-DD` or sentinel). |
| `data` | `object \| null` | Raw JSON from `/api/games/today`. |
| `loading` | `boolean` | True until the first fetch completes. |
| `error` | `string \| null` | Error message from the last failed fetch, or `null`. |
| `updatedAt` | `number \| null` | Timestamp (ms) of the last successful fetch. |

---

### `Topbar`

| Prop | Type | Description |
|---|---|---|
| `dark` | `boolean` | Current dark-mode state. |
| `onDarkToggle` | `() => void` | Toggle dark mode. |
| `density` | `string` | Current density value (`'compact'`, `'regular'`, `'comfy'`). |
| `onDensityChange` | `(value: string) => void` | Change row density. |
| `liveCount` | `number` | Number of games currently live. |
| `loading` | `boolean` | Whether a fetch is in flight. |
| `error` | `string \| null` | Most recent fetch error, or `null`. |
| `updatedAt` | `number \| null` | Timestamp of the last successful fetch. |
| `onRefresh` | `() => void` | Manually trigger a fetch. |
| `day` | `string` | Currently selected day key. |
| `onDayChange` | `(key: string) => void` | Change the selected day. |
| `gameCounts` | `Record<string, number>` | Map of `YYYY-MM-DD` → game count, used for date nav badges. |

---

### `FilterBar`

| Prop | Type | Description |
|---|---|---|
| `numGames` | `number` | Filtered game count (currently equals `totalGames`). |
| `totalGames` | `number` | Total games returned by the API. |
| `liveCount` | `number` | Games currently in progress. |
| `market` | `string` | Active market tab id (`'h2h'`, `'spreads'`, `'totals'`). |
| `onMarketChange` | `(id: string) => void` | Change the active market. |
| `day` | `string` | Selected day key, used to compute the section heading. |

---

### `StatStrip`

| Prop | Type | Description |
|---|---|---|
| `games` | `Game[]` | Full array of game objects from the API response. |

Computes and displays four aggregate cards: total games, +EV opportunities, sharp action (stub), and average away implied probability.

---

### `SlateTable`

| Prop | Type | Description |
|---|---|---|
| `games` | `Game[]` | Array of game objects to render. |
| `loading` | `boolean` | Shows skeleton rows when `true` and `games` is empty. |
| `density` | `string` | Passed through to each `GameRow`. |

---

### `GameRow`

| Prop | Type | Description |
|---|---|---|
| `g` | `Game` | Single game object from the API. |
| `density` | `string` | Controls vertical padding (`compact` = 14px, `regular` = 18px, `comfy` = 22px). |

---

### `StatusCell`

| Prop | Type | Description |
|---|---|---|
| `g` | `Game` | Game object. Reads `g.status` (`'live'`, `'final'`, or scheduled) and `g.live` for score/period/clock. |

---

### `MatchupCell`

| Prop | Type | Description |
|---|---|---|
| `g` | `Game` | Game object. Reads `g.away`, `g.home`, `g.live`, and `g.status`. |
| `density` | `string` | Adjusts logo size and row gap. |

---

### `MoneylineCell`

| Prop | Type | Description |
|---|---|---|
| `g` | `Game` | Game object. Reads `g.ml` (current moneyline), `g.ml_open` (opening line), and `g.implied` (de-vigged probabilities). |

---

### `SparklineCell`

| Prop | Type | Description |
|---|---|---|
| `series` | `number[]` | Array of moneyline values over the past 24 hours, used to render the line-movement sparkline. |

---

### `EdgeCell`

| Prop | Type | Description |
|---|---|---|
| `edge` | `number \| null` | Edge percentage. Positive values are highlighted in green (`--up`), negative in red (`--down`). |

---

## Polling Behavior

`App` fetches `/api/games/today` on a 15-second interval using a `setInterval` loop (not the `usePolling` hook — `App` manages polling inline because it also tracks `updatedAt` and the error toast).

The standalone `usePolling` hook in `src/hooks/usePolling.js` extracts the same pattern for reuse:

```js
const { data, error, loading } = usePolling('/api/games/today', 15000)
```

**How it works:**

1. On mount, `fetchNow()` fires immediately.
2. `setInterval(fetchNow, interval)` schedules subsequent fetches every `interval` ms (default 15 000 ms = 15 s).
3. A `visibilitychange` listener pauses fetching when the tab is hidden — if `document.visibilityState === 'hidden'` the fetch is skipped. When the tab becomes visible again, an immediate fetch fires.
4. On unmount, `clearInterval` and `removeEventListener` clean up both the timer and the visibility listener.

**Return values** (from `usePolling`):

| Value | Type | Description |
|---|---|---|
| `data` | `object \| null` | Parsed JSON from the last successful response. |
| `error` | `string \| null` | Error message from the last failed fetch. Reset to `null` on next success. |
| `loading` | `boolean` | `true` until the first fetch completes (either success or error). |

**Re-render trigger:** Each successful fetch calls `setData(json)`, which causes React to re-render the component tree with fresh game data. An error calls `setError(message)` which triggers the error banner and toast in `App`.

---

## CSS Variables

All design tokens are defined in `src/styles/tokens.css` using CSS custom properties on `:root` (light mode) and `.dark` (dark mode). The `.dark` class is toggled on `<html>` by `App` when dark mode is active.

### Colors

| Variable | Light | Dark | Usage |
|---|---|---|---|
| `--paper` | `#ffffff` | `#131922` | Card and surface background |
| `--bg` | `#f4f6f9` | `#0c1119` | Page background |
| `--ink` | `#0c1726` | `#e8edf3` | Primary text |
| `--muted` | `#5a6878` | `#94a3b3` | Secondary / label text |
| `--faint` | `#94a1b2` | `#5a6878` | Placeholder, dimmed text |
| `--rule` | `#e3e8ee` | `#1f2733` | Dividers and borders |
| `--rule-strong` | `#cdd5df` | `#2c3644` | Emphasized borders |
| `--accent` | `#1ba1b8` | `#4dc6db` | Brand blue, active states |
| `--accent-deep` | `#0a7a8e` | `#2bb0c8` | Darker accent for text |
| `--accent-soft` | `#e3f4f7` | `#0e2c33` | Accent tint for backgrounds |
| `--hot` | `#e63946` | `#ff5d6c` | Error, live indicator |
| `--hot-soft` | `#fde8ea` | `#2e1418` | Error tint for backgrounds |
| `--up` | `#1a8b5f` | `#2dc585` | Positive edge, winning score |
| `--up-soft` | `#e1f3eb` | `#0e2a1f` | Positive tint |
| `--down` | `#c8362d` | `#ff6a6a` | Negative edge |
| `--warn` | `#c98a14` | `#e5b260` | Warning states |

### Shadows

| Variable | Description |
|---|---|
| `--shadow` | Subtle 1px card shadow for surfaces |
| `--shadow-lg` | Larger shadow for popovers and floating elements |

### Typography

Fonts are set in `src/styles/app.css`. The `.mono` utility class applies a monospace font for numeric data (scores, odds, timestamps). The `.tnum` class enables tabular number spacing so columns align without shifting.
