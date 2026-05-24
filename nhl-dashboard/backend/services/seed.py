"""
Startup seeding: populate the team table from the NHL Stats REST API.
https://api.nhle.com/stats/rest/en/team

Run once before the first slate-refresh job so every game's away_code/home_code
FK can be satisfied immediately.
"""
import logging

from nhl_client import get_all_teams
from extensions import db
from models import Team

logger = logging.getLogger(__name__)


def seed_teams() -> None:
    """Upsert all NHL franchises from the stats API into the team table.

    Fetches the full team list and merges each row by tri_code primary key,
    so re-running on restart is safe (idempotent). A fetch failure is logged
    as a warning and does not crash the application.
    """
    try:
        teams = get_all_teams()
    except Exception as exc:
        logger.warning("[seed] Could not fetch teams from stats API: %s", exc)
        return

    for raw in teams:
        tri_code = raw.get('triCode')
        if not tri_code:
            continue
        team = Team(
            tri_code=tri_code,
            name=raw.get('fullName', ''),
            team_id=raw.get('id'),
            franchise_id=raw.get('franchiseId'),
            full_name=raw.get('fullName'),
            league_id=raw.get('leagueId'),
            raw_tricode=raw.get('rawTricode'),
        )
        db.session.merge(team)

    db.session.commit()
    logger.info("[seed] Upserted %d teams", len(teams))
