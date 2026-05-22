"""Standings service — fetches NHL standings and upserts Team rows."""

import logging

from extensions import db
from models import Team

logger = logging.getLogger(__name__)


def build_standings(client=None) -> None:
    """Fetch current NHL standings and upsert standings columns on Team rows.

    Safe to call repeatedly — uses db.session.merge() so rows are not
    duplicated across multiple poll cycles. Preserves existing team name.

    Args:
        client: NhlClient instance. Defaults to the module-level singleton.
    """
    if client is None:
        from nhl_client import nhl_client as _default
        client = _default

    standings = client.get_standings()
    if not standings:
        logger.warning("build_standings: no standings returned by NHL client")
        return

    for abbrev, stats in standings.items():
        existing = db.session.get(Team, abbrev)
        name = existing.name if existing else ""
        db.session.merge(Team(
            code=abbrev,
            name=name,
            wins=stats["wins"],
            losses=stats["losses"],
            ot_losses=stats["ot_losses"],
            l10_wins=stats["l10_wins"],
            l10_losses=stats["l10_losses"],
            l10_ot_losses=stats["l10_ot_losses"],
        ))

    db.session.commit()
