"""
Score service: populates NhlOddsLine from /v1/score/now partner odds.
"""
import logging
from datetime import datetime

from extensions import db
from models import NhlOddsLine, NhlOddsPartner
from services.time_utils import now_et

logger = logging.getLogger(__name__)


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


def refresh_nhl_odds() -> None:
    """Fetch /v1/score/now and write NhlOddsLine rows for each game's partner odds.

    Also upserts NhlOddsPartner registry rows from the oddsPartners array.
    On API failure the error is logged and no writes are committed.
    """
    from nhl_client import get_score_now

    try:
        data = get_score_now()
    except Exception as exc:
        logger.error('[scores] API call to /v1/score/now failed: %s', exc)
        return

    _upsert_partners(data.get('oddsPartners', []))

    now = now_et()
    for game_data in data.get('games', []):
        game_id = game_data.get('id')
        if not game_id:
            continue
        away_odds = game_data.get('awayTeam', {}).get('odds', [])
        home_odds = game_data.get('homeTeam', {}).get('odds', [])
        _insert_odds_lines(game_id, away_odds, home_odds, now)

    db.session.commit()
