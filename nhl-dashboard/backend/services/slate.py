"""Slate service — fetches today's NHL schedule and upserts Game/Team rows."""

import logging
from datetime import datetime, timezone

from extensions import db
from models import Game, Team

logger = logging.getLogger(__name__)


def build_slate(client=None) -> None:
    """Fetch today's schedule and upsert Game and Team rows.

    Safe to call repeatedly — uses db.session.merge() so rows are not
    duplicated when the same game appears across multiple poll cycles.

    Args:
        client: NhlClient instance. Defaults to the module-level singleton.
    """
    if client is None:
        from nhl_client import nhl_client as _default
        client = _default

    games = client.get_schedule_today()
    if not games:
        logger.warning("build_slate: no games returned by NHL client")
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for g in games:
        away_code = g["away_code"]
        home_code = g["home_code"]

        db.session.merge(Team(code=away_code, name=g.get("away_name", "")))
        db.session.merge(Team(code=home_code, name=g.get("home_name", "")))

        start_raw = g.get("start_utc")
        if isinstance(start_raw, str):
            start_utc = datetime.fromisoformat(
                start_raw.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        else:
            start_utc = now

        db.session.merge(Game(
            id=g["id"],
            start_utc=start_utc,
            venue=g.get("venue"),
            away_code=away_code,
            home_code=home_code,
            status=g.get("status", "scheduled"),
            updated_at=now,
        ))

    db.session.commit()
