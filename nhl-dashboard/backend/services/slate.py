"""
Slate service: build today's game list, upsert from NHL API, return API response.
"""
from datetime import datetime, timezone

from extensions import db
from models import Game, OddsSnapshot, ModelFair
from services.implied import american_to_implied, devig_two_way, edge as calc_edge


# NHL schedule API odds provider IDs that give American moneyline format
_AMERICAN_PROVIDER_IDS = {9, 7, 8}


def _team_name(team_obj: dict) -> str:
    """Parse full team name from NHL API team object."""
    place = team_obj.get('placeName', {})
    place_str = place.get('default', '') if isinstance(place, dict) else ''
    common = team_obj.get('commonName', {})
    common_str = common.get('default', '') if isinstance(common, dict) else ''
    abbrev = team_obj.get('abbrev', '')
    if place_str and common_str:
        return f'{place_str} {common_str}'
    return abbrev


def _parse_american_odds(team_obj: dict) -> int | None:
    """Extract American moneyline from the NHL API odds array."""
    for o in team_obj.get('odds', []):
        if o.get('providerId') in _AMERICAN_PROVIDER_IDS:
            val = o.get('value', '')
            try:
                return int(str(val).replace('+', '').strip())
            except (ValueError, TypeError):
                pass
    return None


def refresh_slate():
    """Pull today's schedule from NHL API and upsert Game rows."""
    from nhl_client import get_schedule_now
    from models import Team

    try:
        data = get_schedule_now()
    except Exception as e:
        print(f'[slate] NHL API error: {e}')
        return

    game_weeks = data.get('gameWeek', [])
    if not game_weeks:
        return

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    # Find today's block; fall back to first block
    today_block = next((w for w in game_weeks if w.get('date') == today_str), None)
    if not today_block:
        today_block = game_weeks[0] if game_weeks else None
    if not today_block:
        return

    games = today_block.get('games', [])
    now = datetime.now(timezone.utc)

    for g in games:
        game_id = g.get('id')
        if not game_id:
            continue

        away_obj = g.get('awayTeam', {})
        home_obj = g.get('homeTeam', {})
        away_abbrev = away_obj.get('abbrev', '???')
        home_abbrev = home_obj.get('abbrev', '???')

        # Upsert teams
        for abbrev, obj in [(away_abbrev, away_obj), (home_abbrev, home_obj)]:
            team = db.session.get(Team, abbrev)
            if team is None:
                team = Team(tri_code=abbrev, name=_team_name(obj))
                db.session.add(team)
            elif team.name == abbrev:
                # Backfill name if it was stored as the code
                team.name = _team_name(obj)

        # Parse start time
        start_raw = g.get('startTimeUTC', '')
        try:
            start_utc = datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
        except Exception:
            start_utc = now

        # Game status
        game_state = g.get('gameState', 'FUT')
        if game_state in ('LIVE', 'CRIT'):
            status = 'live'
        elif game_state in ('FINAL', 'OFF'):
            status = 'final'
        else:
            status = 'scheduled'

        row = db.session.get(Game, game_id)
        if row is None:
            row = Game(id=game_id)
            db.session.add(row)

        row.start_utc  = start_utc
        row.venue      = g.get('venue', {}).get('default', '') if isinstance(g.get('venue'), dict) else g.get('venue', '')
        row.away_code  = away_abbrev
        row.home_code  = home_abbrev
        row.status     = status
        row.away_score = away_obj.get('score', 0) or 0
        row.home_score = home_obj.get('score', 0) or 0
        row.updated_at = now

        # Inline odds from NHL schedule API — insert snapshot if present
        away_ml = _parse_american_odds(away_obj)
        home_ml = _parse_american_odds(home_obj)
        if away_ml and home_ml:
            # Check if we already have a recent snapshot for this game
            from sqlalchemy import select
            recent = db.session.scalars(
                select(OddsSnapshot)
                .where(OddsSnapshot.game_id == game_id)
                .order_by(OddsSnapshot.fetched_at.desc())
                .limit(1)
            ).first()
            # Insert a new snapshot at most once per poll cycle (avoid duplicates)
            if recent is None or (now - recent.fetched_at.replace(tzinfo=timezone.utc)).total_seconds() > 180:
                snap = OddsSnapshot(
                    game_id      = game_id,
                    fetched_at   = now,
                    book         = 'consensus',
                    away_ml      = away_ml,
                    home_ml      = home_ml,
                    away_implied = american_to_implied(away_ml),
                    home_implied = american_to_implied(home_ml),
                )
                db.session.add(snap)

    db.session.commit()
    print(f'[slate] Upserted {len(games)} games for {today_str}')


def refresh_odds():
    """
    Fetch odds (stub) and insert OddsSnapshot rows.
    Real game IDs are handled by refresh_slate() via inline NHL API odds.
    The stub odds_client covers the hardcoded demo IDs.
    """
    from sqlalchemy import select
    from odds_client import fetch_odds, _MOCK

    # Only fetch for demo game IDs (the mock covers 1001–1008)
    demo_ids = list(_MOCK.keys())
    rows = fetch_odds(demo_ids)
    now = datetime.now(timezone.utc)

    for r in rows:
        snap = OddsSnapshot(
            game_id      = r['game_id'],
            fetched_at   = now,
            book         = r.get('book', 'consensus'),
            away_ml      = r['away_ml'],
            home_ml      = r['home_ml'],
            away_implied = american_to_implied(r['away_ml']),
            home_implied = american_to_implied(r['home_ml']),
        )
        db.session.add(snap)

    if rows:
        db.session.commit()
        print(f'[slate] Inserted {len(rows)} demo OddsSnapshot rows')


def prune_old_snapshots():
    """Delete OddsSnapshot rows older than 7 days."""
    from sqlalchemy import delete
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = db.session.execute(
        delete(OddsSnapshot).where(OddsSnapshot.fetched_at < cutoff)
    )
    db.session.commit()
    print(f'[slate] Pruned {result.rowcount} old snapshots')


def build_today_response() -> dict:
    """Return the JSON shape for GET /api/games/today."""
    from sqlalchemy import select

    now = datetime.now(timezone.utc)

    today_games = db.session.scalars(
        select(Game).order_by(Game.start_utc)
    ).all()

    return _build_from_db(today_games, now)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_sparkline(game_id: int) -> list[float]:
    """Return up to 24 OddsSnapshot away_implied values for this game, chronological."""
    from sqlalchemy import select

    snaps = db.session.scalars(
        select(OddsSnapshot)
        .where(OddsSnapshot.game_id == game_id)
        .order_by(OddsSnapshot.fetched_at.desc())
        .limit(24)
    ).all()

    return [s.away_implied for s in reversed(snaps)]


def _build_from_db(games: list, now: datetime) -> dict:
    from sqlalchemy import select

    result = []
    for g in games:
        snap = db.session.scalars(
            select(OddsSnapshot)
            .where(OddsSnapshot.game_id == g.id)
            .order_by(OddsSnapshot.fetched_at.desc())
        ).first()

        snap_open = db.session.scalars(
            select(OddsSnapshot)
            .where(OddsSnapshot.game_id == g.id)
            .order_by(OddsSnapshot.fetched_at)
        ).first()

        mf = db.session.get(ModelFair, g.id)

        if snap:
            raw_a = american_to_implied(snap.away_ml)
            raw_h = american_to_implied(snap.home_ml)
            imp_a, imp_h = devig_two_way(raw_a, raw_h)
        else:
            imp_a, imp_h = 50.0, 50.0

        fair_a = mf.away_fair if mf else imp_a
        fair_h = mf.home_fair if mf else imp_h
        edge_val = calc_edge(fair_a, imp_a) if snap else None

        live_block = None
        if g.status == 'live':
            live_block = {
                'period':     g.period or '1st',
                'clock':      g.clock or '20:00',
                'away_score': g.away_score,
                'home_score': g.home_score,
                'away_sog':   g.away_sog,
                'home_sog':   g.home_sog,
            }

        away_name = g.away_team.name if g.away_team else g.away_code
        home_name = g.home_team.name if g.home_team else g.home_code

        # Venue may be a dict or string
        venue = g.venue or ''

        start_iso = None
        if g.start_utc:
            dt = g.start_utc
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            start_iso = dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        row = {
            'id':    g.id,
            'away':  {'code': g.away_code, 'name': away_name, 'record': '', 'l10': ''},
            'home':  {'code': g.home_code, 'name': home_name, 'record': '', 'l10': ''},
            'start':  start_iso,
            'venue':  venue,
            'status': g.status,
            'live':   live_block,
            'ml':     {'away': snap.away_ml, 'home': snap.home_ml}           if snap      else None,
            'ml_open':{'away': snap_open.away_ml, 'home': snap_open.home_ml} if snap_open else None,
            'implied':{'away': round(imp_a, 2), 'home': round(imp_h, 2)},
            'fair':   {'away': round(fair_a, 2),  'home': round(fair_h, 2)},
            'edge':   round(edge_val, 2) if edge_val is not None else None,
            'movement_24h': _get_sparkline(g.id),
        }
        result.append(row)

    return {'updated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'games': result}


def _build_mock(now: datetime) -> dict:
    """Return the SLATE fixture as the API response when the DB has no games."""
    MOCK_SLATE = [
        {'id': 1001, 'away': {'code': 'TOR', 'name': 'Toronto Maple Leafs', 'record': '24-18-4', 'l10': '6-3-1'},
         'home': {'code': 'BOS', 'name': 'Boston Bruins', 'record': '30-15-6', 'l10': '7-2-1'},
         'start': '2026-05-17T00:00:00Z', 'venue': 'TD Garden', 'status': 'live',
         'live': {'period': '2nd', 'clock': '12:34', 'away_score': 3, 'home_score': 2, 'away_sog': 18, 'home_sog': 22},
         'ml': {'away': 120, 'home': -140}, 'ml_open': {'away': 115, 'home': -135},
         'implied': {'away': 45.0, 'home': 55.0}, 'fair': {'away': 47.5, 'home': 52.5},
         'edge': 2.1,
         'movement_24h': [46.38,44.95,44.14,45.07,44.14,43.78,44.91,44.44,44.9,45.95,47.13,46.81,45.87,45.58,45.31,45.5,44.68,45.68,44.41,45.36,43.91,43.55,43.64,45]},
        {'id': 1002, 'away': {'code': 'NYR', 'name': 'New York Rangers', 'record': '28-16-3', 'l10': '5-4-1'},
         'home': {'code': 'FLA', 'name': 'Florida Panthers', 'record': '29-14-5', 'l10': '6-3-1'},
         'start': '2026-05-17T00:00:00Z', 'venue': 'Amerant Bank Arena', 'status': 'live',
         'live': {'period': '1st', 'clock': '04:12', 'away_score': 1, 'home_score': 1, 'away_sog': 5, 'home_sog': 6},
         'ml': {'away': -105, 'home': -115}, 'ml_open': {'away': -110, 'home': -110},
         'implied': {'away': 51.0, 'home': 49.0}, 'fair': {'away': 49.5, 'home': 50.5},
         'edge': 1.5,
         'movement_24h': [54.17,54.16,53.84,53.38,53.08,53.23,52.65,51.22,51.55,50.03,51.22,52.22,52.59,51.13,51.89,52.82,52.03,52.71,53.72,54.65,53.51,52.61,52.03,51]},
        {'id': 1003, 'away': {'code': 'EDM', 'name': 'Edmonton Oilers', 'record': '26-19-3', 'l10': '7-3-0'},
         'home': {'code': 'VAN', 'name': 'Vancouver Canucks', 'record': '24-17-7', 'l10': '5-4-1'},
         'start': '2026-05-17T03:00:00Z', 'venue': 'Rogers Arena', 'status': 'live',
         'live': {'period': '3rd', 'clock': '08:55', 'away_score': 4, 'home_score': 3, 'away_sog': 28, 'home_sog': 25},
         'ml': {'away': -160, 'home': 135}, 'ml_open': {'away': -145, 'home': 125},
         'implied': {'away': 62.0, 'home': 38.0}, 'fair': {'away': 58.0, 'home': 42.0},
         'edge': -1.2,
         'movement_24h': [61.73,61.49,60.54,59.38,60.68,61.13,62.39,63.75,62.81,61.62,61.48,62.26,61.6,61.8,61.26,62.04,62.75,62.43,63.32,62.88,62.84,61.32,60.06,62]},
        {'id': 1004, 'away': {'code': 'COL', 'name': 'Colorado Avalanche', 'record': '32-12-4', 'l10': '8-1-1'},
         'home': {'code': 'DAL', 'name': 'Dallas Stars', 'record': '29-14-5', 'l10': '6-3-1'},
         'start': '2026-05-17T01:00:00Z', 'venue': 'American Airlines Center', 'status': 'live',
         'live': {'period': '1st', 'clock': '18:22', 'away_score': 0, 'home_score': 2, 'away_sog': 3, 'home_sog': 8},
         'ml': {'away': 130, 'home': -150}, 'ml_open': {'away': 120, 'home': -140},
         'implied': {'away': 43.0, 'home': 57.0}, 'fair': {'away': 45.5, 'home': 54.5},
         'edge': 2.5,
         'movement_24h': [42.15,41.53,41.63,41.89,40.83,42.35,42.74,42.52,41.96,42.99,43.46,42.11,42.27,41.6,42.37,41.46,41.92,42.07,41.27,40.23,42.05,43.63,42.38,43]},
        {'id': 1005, 'away': {'code': 'CHI', 'name': 'Chicago Blackhawks', 'record': '14-30-3', 'l10': '3-6-1'},
         'home': {'code': 'PIT', 'name': 'Pittsburgh Penguins', 'record': '22-21-5', 'l10': '4-5-1'},
         'start': '2026-05-17T00:30:00Z', 'venue': 'PPG Paints Arena', 'status': 'scheduled', 'live': None,
         'ml': {'away': 175, 'home': -210}, 'ml_open': {'away': 185, 'home': -220},
         'implied': {'away': 36.0, 'home': 64.0}, 'fair': {'away': 34.5, 'home': 65.5},
         'edge': -1.5,
         'movement_24h': [37.36,37.28,37.4,37.62,36.03,35.1,36.46,37.27,35.92,35.36,34.47,35.76,35.18,35.6,36.39,35.65,35.66,34.97,35.69,35.02,36.06,37.28,36.57,36]},
        {'id': 1006, 'away': {'code': 'MTL', 'name': 'Montréal Canadiens', 'record': '19-22-6', 'l10': '4-4-2'},
         'home': {'code': 'OTT', 'name': 'Ottawa Senators', 'record': '21-23-3', 'l10': '5-4-1'},
         'start': '2026-05-17T00:30:00Z', 'venue': 'Canadian Tire Centre', 'status': 'scheduled', 'live': None,
         'ml': {'away': 145, 'home': -170}, 'ml_open': {'away': 135, 'home': -160},
         'implied': {'away': 41.0, 'home': 59.0}, 'fair': {'away': 43.0, 'home': 57.0},
         'edge': 2.0,
         'movement_24h': [41.78,41.32,42.48,41.13,40.72,40.77,41.17,40.34,39.32,40.93,40.63,39.74,39.96,39.49,38.57,39.68,39.32,39.02,37.97,39.64,38.95,40.32,40.21,41]},
        {'id': 1007, 'away': {'code': 'CGY', 'name': 'Calgary Flames', 'record': '22-21-4', 'l10': '5-4-1'},
         'home': {'code': 'SEA', 'name': 'Seattle Kraken', 'record': '20-22-6', 'l10': '4-5-1'},
         'start': '2026-05-17T03:00:00Z', 'venue': 'Climate Pledge Arena', 'status': 'scheduled', 'live': None,
         'ml': {'away': 120, 'home': -140}, 'ml_open': {'away': 125, 'home': -145},
         'implied': {'away': 45.0, 'home': 55.0}, 'fair': {'away': 44.0, 'home': 56.0},
         'edge': -1.0,
         'movement_24h': [47.57,48.53,47.18,47.98,48.1,48.58,47.22,45.36,44.17,43.18,42.85,43.27,44.77,46.11,45.68,44.06,43.9,43.42,44.77,43.51,43.75,45.09,44.71,45]},
        {'id': 1008, 'away': {'code': 'LAK', 'name': 'Los Angeles Kings', 'record': '27-15-6', 'l10': '7-2-1'},
         'home': {'code': 'SJS', 'name': 'San Jose Sharks', 'record': '13-30-4', 'l10': '2-7-1'},
         'start': '2026-05-17T03:30:00Z', 'venue': 'SAP Center', 'status': 'scheduled', 'live': None,
         'ml': {'away': -180, 'home': 155}, 'ml_open': {'away': -170, 'home': 148},
         'implied': {'away': 64.0, 'home': 36.0}, 'fair': {'away': 66.0, 'home': 34.0},
         'edge': 2.0,
         'movement_24h': [65.99,66.57,66.26,65.49,63.79,62.79,64.45,64.21,63.03,63.95,63.99,65.06,63.66,64.1,64.94,64.61,63.63,63.17,62.44,63.27,64.57,65.36,65,64]},
    ]
    return {'updated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'games': MOCK_SLATE}
