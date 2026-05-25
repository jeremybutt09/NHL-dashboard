"""
Score service: updates all of today's games in a single /v1/score/now API call.

Replaces the per-game boxscore polling in services/live.py (one call per live game)
with a single bulk fetch that also picks up games that have started but are not yet
marked 'live' in the database.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from extensions import db
from models import Game, NhlOddsLine, NhlOddsPartner

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


def _update_game_from_score_data(game: Game, game_data: dict, now: datetime) -> None:
    """Write score, period, clock, and state from one /v1/score/now game entry to the DB row.

    Args:
        game: SQLAlchemy Game instance to update.
        game_data: Single game dict from the /v1/score/now 'games' list.
        now: Current UTC datetime to stamp updated_at.
    """
    game.status = _map_game_state(game_data.get('gameState', ''))

    pd = game_data.get('periodDescriptor') or {}
    game.period = _parse_period(pd)

    clock_data = game_data.get('clock') or {}
    game.clock = clock_data.get('timeRemaining', game.clock)

    away_info = game_data.get('awayTeam', {})
    home_info = game_data.get('homeTeam', {})
    game.away_score = away_info.get('score', game.away_score)
    game.home_score = home_info.get('score', game.home_score)
    game.away_sog = away_info.get('sog', game.away_sog)
    game.home_sog = home_info.get('sog', game.home_sog)
    game.updated_at = now


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
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
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
    """Fetch /v1/score/now and update all matched game rows in a single DB commit.

    One API call covers all of today's games regardless of their current status,
    eliminating the N+1 boxscore polling pattern and the bootstrap gap where newly
    started games were missed.

    Games whose game_id is not present in the database are skipped with a warning —
    inserting new rows is the responsibility of the schedule refresh job.

    On API failure the error is logged and no writes are committed.
    """
    from nhl_client import get_score_now

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
        select(Game).where(Game.game_id.in_(api_ids))
    ).all()
    db_game_map = {g.game_id: g for g in db_games}

    for gid in api_ids:
        if gid not in db_game_map:
            logger.warning(
                '[scores] game_id %s not in DB, skipping — schedule refresh pending', gid
            )

    now = datetime.now(timezone.utc)
    for game in db_games:
        game_data = api_game_map[game.game_id]
        _update_game_from_score_data(game, game_data, now)
        away_odds = game_data.get('awayTeam', {}).get('odds', [])
        home_odds = game_data.get('homeTeam', {}).get('odds', [])
        _insert_odds_lines(game.game_id, away_odds, home_odds, now)

    db.session.commit()
