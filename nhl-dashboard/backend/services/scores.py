"""
Score service: upserts all of today's games from /v1/score/now in a single API call.

Acts as the single source of truth for the game table: new game rows are created
here when they first appear in /v1/score/now, rather than waiting for
refresh_schedule() to seed them from /v1/schedule/now.

Pre-game (scheduled) rows have period, clock, and sog set to NULL; scores default
to 0.  Live and final rows are updated from the API fields present in those states.
"""
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from extensions import db
from models import LiveGame, NhlOddsLine, NhlOddsPartner
from services.time_utils import now_et

_EASTERN = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)


def _map_game_state(game_state: str) -> str:
    """Map an NHL gameState string to our internal status value.

    Args:
        game_state: Raw NHL API gameState (e.g. 'LIVE', 'FINAL', 'FUT').

    Returns:
        One of 'live', 'final', or 'scheduled'.
    """
    if game_state in ('FINAL', 'OFF'):
        return 'final'
    if game_state in ('LIVE', 'CRIT'):
        return 'live'
    return 'scheduled'


def _parse_period(period_descriptor: dict) -> str:
    """Convert a periodDescriptor dict to a human-readable period string.

    Args:
        period_descriptor: NHL API periodDescriptor dict with 'number' and 'periodType'.

    Returns:
        One of 'OT', 'SO', or an ordinal like '1st', '2nd', '3rd'.
    """
    period_type = period_descriptor.get('periodType', 'REG')
    period_num = period_descriptor.get('number', 1)
    if period_type == 'OT':
        return 'OT'
    if period_type == 'SO':
        return 'SO'
    ordinals = {1: '1st', 2: '2nd', 3: '3rd'}
    return ordinals.get(period_num, f'{period_num}th')


def _update_game_from_score_data(game: LiveGame, game_data: dict, now: datetime) -> None:
    """Write score, period, clock, and state from one /v1/score/now game entry to the DB row.

    Handles three states:
    - scheduled: period/clock/sog set to None; scores default to 0.
    - live: all live fields populated from API; existing values kept as fallback.
    - final: scores stored; clock defaults to '00:00' when absent from API.

    Args:
        game: SQLAlchemy Game instance to update.
        game_data: Single game dict from the /v1/score/now 'games' list.
        now: Current UTC datetime to stamp updated_at.
    """
    status = _map_game_state(game_data.get('gameState', ''))
    game.status = status

    if status == 'scheduled':
        # Pre-game: live fields are absent from the API — null them out explicitly
        game.period = None
        game.clock = None
        game.away_sog = None
        game.home_sog = None
        away_info = game_data.get('awayTeam', {})
        home_info = game_data.get('homeTeam', {})
        game.away_score = away_info.get('score', 0) or 0
        game.home_score = home_info.get('score', 0) or 0
    else:
        pd = game_data.get('periodDescriptor') or {}
        game.period = _parse_period(pd)

        clock_data = game_data.get('clock') or {}
        if status == 'final':
            # Clock may be absent for final games; always emit '00:00'
            game.clock = clock_data.get('timeRemaining', '00:00')
        else:
            game.clock = clock_data.get('timeRemaining', game.clock)

        away_info = game_data.get('awayTeam', {})
        home_info = game_data.get('homeTeam', {})
        game.away_score = away_info.get('score', game.away_score)
        game.home_score = home_info.get('score', game.home_score)
        game.away_sog = away_info.get('sog', game.away_sog)
        game.home_sog = home_info.get('sog', game.home_sog)

    game.updated_at = now


def _set_game_metadata_from_score_data(
    game: LiveGame, game_data: dict, all_teams: list, now: datetime
) -> None:
    """Populate metadata fields on a newly inserted Game row from /v1/score/now data.

    Sets away_code, home_code, start_est, game_date, and venue.  Ensures Team rows
    exist (via _ensure_team from services.slate) before writing the FK columns.

    Args:
        game: Newly created Game instance (not yet committed).
        game_data: Single game dict from the /v1/score/now 'games' list.
        all_teams: Pre-fetched list from get_all_teams(); may be empty on API failure.
        now: Current UTC datetime used as fallback for start_est.
    """
    from services.slate import _ensure_team

    away_obj = game_data.get('awayTeam', {})
    home_obj = game_data.get('homeTeam', {})
    away_abbrev = away_obj.get('abbrev', '???')
    home_abbrev = home_obj.get('abbrev', '???')

    for abbrev, obj in [(away_abbrev, away_obj), (home_abbrev, home_obj)]:
        _ensure_team(abbrev, obj, all_teams)

    game.away_code = away_abbrev
    game.home_code = home_abbrev

    start_raw = game_data.get('startTimeUTC', '')
    try:
        start_utc_dt = datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
        game.start_est = start_utc_dt.astimezone(_EASTERN)
    except Exception:
        game.start_est = now.astimezone(_EASTERN)

    game.game_date = game_data.get('gameDate')

    venue = game_data.get('venue', '')
    if isinstance(venue, dict):
        game.venue = venue.get('default', '')
    else:
        game.venue = venue or ''


def _upsert_partners(partners_list: list) -> None:
    """Upsert each entry from the oddsPartners array into nhl_odds_partner.

    Args:
        partners_list: List of partner dicts from the /v1/score/now response.
            Each dict must contain 'partnerId' and 'name' at minimum.
    """
    for p in partners_list:
        db.session.merge(NhlOddsPartner(
            partner_id=p['partnerId'],
            country=p.get('country'),
            name=p['name'],
            image_url=p.get('imageUrl'),
            site_url=p.get('siteUrl'),
            bg_color=p.get('bgColor'),
            text_color=p.get('textColor'),
            accent_color=p.get('accentColor'),
        ))
    if partners_list:
        db.session.commit()


_ODDS_COOLDOWN_SECONDS = 180  # 3-minute duplicate-suppression window


def _insert_odds_lines(game_id: int, away_odds: list, home_odds: list, now: datetime) -> None:
    """Insert NhlOddsLine rows for a single game, pairing odds by providerId.

    Args:
        game_id: The game's primary key (FK → game.game_id).
        away_odds: List of ``{"providerId": int, "value": str}`` dicts for the away team.
        home_odds: List of ``{"providerId": int, "value": str}`` dicts for the home team.
        now: Current UTC datetime used for fetched_at and cooldown checks.

    Only partners present in *both* away and home arrays produce a row.  Unknown
    partner IDs (not in nhl_odds_partner) are skipped with a WARNING.  A 3-minute
    cooldown prevents duplicate rows within the same poll window.
    """
    from sqlalchemy import select

    if not away_odds and not home_odds:
        return

    away_map = {o['providerId']: o['value'] for o in (away_odds or [])}
    home_map = {o['providerId']: o['value'] for o in (home_odds or [])}
    paired_ids = set(away_map) & set(home_map)

    for pid in sorted(paired_ids):
        partner = db.session.get(NhlOddsPartner, pid)
        if partner is None:
            logger.warning('[scores] Unknown partner_id %s, skipping odds line', pid)
            continue

        # Cooldown: skip if a row for this (game, partner) was inserted < 3 min ago
        latest = db.session.scalars(
            select(NhlOddsLine)
            .where(NhlOddsLine.game_id == game_id, NhlOddsLine.partner_id == pid)
            .order_by(NhlOddsLine.fetched_at.desc())
            .limit(1)
        ).first()
        if latest is not None:
            last_ts = latest.fetched_at
            if (now - last_ts).total_seconds() < _ODDS_COOLDOWN_SECONDS:
                continue

        db.session.add(NhlOddsLine(
            game_id=game_id,
            partner_id=pid,
            fetched_at=now,
            away_value=away_map[pid],
            home_value=home_map[pid],
        ))


def refresh_scores() -> None:
    """Fetch /v1/score/now and upsert all game rows in a single DB commit.

    Acts as the single source of truth for live_game table population: live_game rows absent
    from the DB are inserted using metadata from the /v1/score/now payload
    (startTimeUTC, venue, awayTeam, homeTeam).  get_all_teams() is called only when
    new rows need to be created, keeping the hot-path free of extra API calls.

    On API failure the error is logged and no writes are committed.
    """
    from nhl_client import get_score_now, get_all_teams

    try:
        data = get_score_now()
    except Exception as exc:
        logger.error('[scores] API call to /v1/score/now failed: %s', exc)
        return

    _upsert_partners(data.get('oddsPartners', []))

    api_games = data.get('games', [])
    if not api_games:
        return

    api_game_map = {g['id']: g for g in api_games}
    api_ids = list(api_game_map.keys())

    db_games = db.session.scalars(
        select(LiveGame).where(LiveGame.game_id.in_(api_ids))
    ).all()
    db_game_map = {g.game_id: g for g in db_games}

    now = now_et()

    new_ids = [gid for gid in api_ids if gid not in db_game_map]
    if new_ids:
        try:
            all_teams = get_all_teams()
        except Exception as exc:
            logger.warning('[scores] Could not fetch teams for new game rows: %s', exc)
            all_teams = []

        for gid in new_ids:
            logger.info('[scores] Inserting new game row %s from /v1/score/now', gid)
            game = LiveGame(game_id=gid)
            # Populate metadata before add() so autoflush does not fire on a row
            # that still has start_est=None (which is NOT NULL in the schema).
            _set_game_metadata_from_score_data(game, api_game_map[gid], all_teams, now)
            db.session.add(game)
            db_game_map[gid] = game

    for game in db_game_map.values():
        game_data = api_game_map[game.game_id]
        _update_game_from_score_data(game, game_data, now)
        away_odds = game_data.get('awayTeam', {}).get('odds', [])
        home_odds = game_data.get('homeTeam', {}).get('odds', [])
        _insert_odds_lines(game.game_id, away_odds, home_odds, now)

    db.session.commit()
