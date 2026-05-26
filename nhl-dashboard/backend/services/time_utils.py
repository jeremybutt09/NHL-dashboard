"""Shared time utilities for freshness timestamp standardization (Issue #136).

Convention: all data-freshness columns (fetched_at, updated_at, computed_at)
store Eastern Time as tz-naive datetimes. Call now_et() at every write site
instead of datetime.now(timezone.utc).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")


def now_et() -> datetime:
    """Return the current Eastern Time as a tz-naive datetime for SQLite storage."""
    return datetime.now(_EASTERN).replace(tzinfo=None)


def migrate_timestamps_to_et() -> dict:
    """Convert existing UTC-naive freshness timestamps to Eastern Time (one-time migration).

    Reads all rows whose freshness-timestamp column (fetched_at, updated_at, or
    computed_at) is not NULL, interprets the stored tz-naive value as UTC, converts
    to Eastern Time, and writes back as a tz-naive ET value.

    Returns:
        Dict mapping each table name to the number of rows updated.
    """
    from extensions import db
    from models import NhlOddsLine, OddsSnapshot, LiveGame, ModelFair, Boxscore, DashboardGame
    from sqlalchemy import select

    columns = [
        (NhlOddsLine,    "fetched_at"),
        (OddsSnapshot,   "fetched_at"),
        (LiveGame,       "updated_at"),
        (ModelFair,      "computed_at"),
        (Boxscore,       "updated_at"),
        (DashboardGame,  "updated_at"),
    ]

    results = {}
    for model, col_name in columns:
        col = getattr(model, col_name)
        rows = db.session.scalars(
            select(model).where(col.isnot(None))
        ).all()
        count = 0
        for row in rows:
            utc_naive = getattr(row, col_name)
            et_naive = utc_naive.replace(tzinfo=timezone.utc).astimezone(_EASTERN).replace(tzinfo=None)
            setattr(row, col_name, et_naive)
            count += 1
        results[model.__tablename__] = count

    db.session.commit()
    return results
