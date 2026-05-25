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
from models import Game, NhlOddsPartner

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
        _update_game_from_score_data(game, api_game_map[game.game_id], now)

    db.session.commit()
