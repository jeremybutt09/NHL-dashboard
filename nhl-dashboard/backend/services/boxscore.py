"""Boxscore ingestion from the NHL Web API.

Source: GET https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore
Table:  boxscore (see models.Boxscore — Issue #133)

Refresh cadence: every POLL_BOXSCORE_INTERVAL seconds (default 60 s) via
APScheduler, so live score/SOG/period data stays current during games.

Today's game IDs are resolved by querying the `game` table, which is
populated by the historical ingest pipeline (models.Game).

backfill_boxscores() (Issue #135) is a one-time (but re-runnable) operation
that fetches a boxscore for every game_id in the `game` table, not just today.
Issue #157 added month-partitioned parallel execution via ThreadPoolExecutor.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import nhl_client
from extensions import db
from models import Boxscore, Game, Team
from services.time_utils import now_et

logger = logging.getLogger(__name__)

_EASTERN = ZoneInfo("America/New_York")


def _load_team_lookup() -> dict[str, str]:
    """Build a tri_code → display_name mapping from the team table.

    Returns:
        Dict of ``{tri_code: display_name}`` where display_name is
        ``full_name`` when set, falling back to ``name``.
    """
    rows = db.session.scalars(db.select(Team)).all()
    return {t.tri_code: (t.full_name or t.name or '') for t in rows}


def _parse_period(period_descriptor: dict) -> str | None:
    """Convert a periodDescriptor dict to a human-readable period string.

    Args:
        period_descriptor: NHL API periodDescriptor dict with 'number' and
            'periodType' keys.

    Returns:
        One of 'OT', 'SO', an ordinal like '1st'/'2nd'/'3rd', or None when
        the descriptor is absent.
    """
    if not period_descriptor:
        return None
    period_type = period_descriptor.get('periodType', 'REG')
    period_num = period_descriptor.get('number', 1)
    if period_type == 'OT':
        return 'OT'
    if period_type == 'SO':
        return 'SO'
    ordinals = {1: '1st', 2: '2nd', 3: '3rd'}
    return ordinals.get(period_num, f'{period_num}th')


def _build_boxscore(
    raw: dict,
    now: datetime,
    team_lookup: dict | None = None,
) -> Boxscore:
    """Map a /v1/gamecenter/{id}/boxscore response to a Boxscore instance.

    Args:
        raw: Full API response dict for a single game boxscore.
        now: Current UTC datetime used for updated_at and as a fallback for
            start_time_est when startTimeUTC is missing or unparseable.
        team_lookup: Optional dict mapping tri_code → display_name.  When
            provided, an empty API team name is replaced with the value from
            this lookup so no row is ever persisted with a blank name.

    Returns:
        An unsaved Boxscore instance ready for db.session.merge().
    """
    # Venue
    venue_raw = raw.get('venue', '')
    venue = venue_raw.get('default', '') if isinstance(venue_raw, dict) else (venue_raw or '')

    # Start time: convert UTC → Eastern
    start_raw = raw.get('startTimeUTC', '')
    try:
        start_utc = datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
        start_est = start_utc.astimezone(_EASTERN)
    except Exception:
        start_est = now.astimezone(_EASTERN)

    # Team names — fall back to team_lookup when API returns empty string
    away = raw.get('awayTeam', {})
    home = raw.get('homeTeam', {})
    away_name_raw = away.get('name', {})
    home_name_raw = home.get('name', {})
    away_name = away_name_raw.get('default', '') if isinstance(away_name_raw, dict) else (away_name_raw or '')
    home_name = home_name_raw.get('default', '') if isinstance(home_name_raw, dict) else (home_name_raw or '')

    if team_lookup:
        if not away_name:
            away_name = team_lookup.get(away.get('abbrev', ''), '')
        if not home_name:
            home_name = team_lookup.get(home.get('abbrev', ''), '')

    # Period and clock
    period = _parse_period(raw.get('periodDescriptor') or {})
    clock_raw = raw.get('clock') or {}
    clock = clock_raw.get('timeRemaining')

    return Boxscore(
        game_id=raw['id'],
        season_id=raw.get('season'),
        game_type=raw.get('gameType'),
        game_date=raw.get('gameDate'),
        venue=venue,
        start_time_est=start_est,
        away_name=away_name,
        away_abbrev=away.get('abbrev'),
        home_name=home_name,
        home_abbrev=home.get('abbrev'),
        away_score=away.get('score'),
        home_score=home.get('score'),
        away_sog=away.get('sog'),
        home_sog=home.get('sog'),
        period=period,
        clock=clock,
        game_state=raw.get('gameState'),
        updated_at=now,
    )


def refresh_boxscores() -> int:
    """Fetch boxscore data for today's games and upsert into the boxscore table.

    Resolves today's game IDs by querying the `game` table filtered to
    game_date == today.  For each game_id, calls
    nhl_client.get_boxscore() and upserts the result.  API failures for
    individual games are logged and skipped so a single bad game does not
    block the rest.

    Returns:
        Number of boxscores successfully upserted.
    """
    today = date.today().isoformat()
    game_ids = db.session.scalars(
        db.select(Game.game_id).where(Game.game_date == today)
    ).all()

    if not game_ids:
        return 0

    now = now_et()
    team_lookup = _load_team_lookup()
    count = 0

    for game_id in game_ids:
        try:
            raw = nhl_client.get_boxscore(game_id)
        except Exception as exc:
            logger.warning('[boxscore] Failed to fetch game %s: %s', game_id, exc)
            continue

        record = _build_boxscore(raw, now, team_lookup=team_lookup)
        db.session.merge(record)
        count += 1

    db.session.commit()
    logger.info('[boxscore] Upserted %d boxscores for %s', count, today)
    return count


def prune_stale_boxscores(date_str: str | None = None) -> int:
    """Delete boxscore rows for today whose game_id the NHL schedule API no longer returns.

    Fetches today's schedule from /v1/schedule/now.  If today's date block is
    found in the API response, removes any boxscore rows for that date whose
    game_id is absent from the API's games list.  When today's block is absent
    from the API response (e.g. the API is showing a different week), no rows
    are pruned.

    API failures are caught and logged; 0 is returned and no rows are deleted.

    Args:
        date_str: YYYY-MM-DD string to prune; defaults to today's Eastern Time
            date.

    Returns:
        Number of boxscore rows deleted.
    """
    from sqlalchemy import delete as sa_delete
    from services.time_utils import today_et

    target_date = date_str or today_et()

    try:
        data = nhl_client.get_schedule_now()
    except Exception as exc:
        logger.warning('[boxscore] prune_stale_boxscores: schedule API error: %s', exc)
        return 0

    # Only prune when today's block is explicitly present in the API response.
    today_block = next(
        (w for w in data.get('gameWeek', []) if w.get('date') == target_date),
        None,
    )
    if today_block is None:
        logger.debug(
            '[boxscore] prune_stale_boxscores: no block for %s in API response; skipping',
            target_date,
        )
        return 0

    api_game_ids = {g['id'] for g in today_block.get('games', []) if g.get('id')}

    stmt = sa_delete(Boxscore).where(Boxscore.game_date == target_date)
    if api_game_ids:
        # Keep rows whose game_id appears in the API; delete the rest.
        stmt = stmt.where(Boxscore.game_id.not_in(api_game_ids))
    # When api_game_ids is empty, the WHERE on game_date alone removes all today's rows.

    result = db.session.execute(stmt)
    db.session.commit()

    if result.rowcount:
        logger.info(
            '[boxscore] prune_stale_boxscores: removed %d stale rows for %s',
            result.rowcount,
            target_date,
        )
    return result.rowcount


# 300 ms between requests — polite rate-limiting for long backfill runs.
_BACKFILL_DELAY_SECONDS: float = 0.3


def _fetch_month_partition(
    game_ids: list[int],
    delay: float,
    team_lookup: dict,
    now: datetime,
) -> tuple[list[Boxscore], int]:
    """Fetch API boxscore data for one month's games. Does not access the database.

    Designed to run inside a ThreadPoolExecutor worker alongside other month
    partitions.  Returns built Boxscore instances for the caller to persist.
    Individual game failures are logged and skipped without raising.

    Args:
        game_ids: Ordered list of game IDs to fetch for this month.
        delay: Seconds to sleep between successive API calls (rate limiting).
        team_lookup: tri_code → display_name mapping for name fallback.
        now: Timestamp used for ``updated_at`` on each Boxscore instance.

    Returns:
        Tuple of ``(records, skipped)`` where ``records`` is a list of
        unsaved Boxscore instances and ``skipped`` is the count of failures.
    """
    records: list[Boxscore] = []
    skipped = 0

    for game_id in game_ids:
        try:
            raw = nhl_client.get_boxscore(game_id)
        except Exception as exc:
            logger.warning(
                '[backfill_boxscores] Failed to fetch game %s: %s', game_id, exc
            )
            skipped += 1
            time.sleep(delay)
            continue

        if not raw or 'id' not in raw:
            logger.warning(
                '[backfill_boxscores] No data for game_id %s, skipping', game_id
            )
            skipped += 1
            time.sleep(delay)
            continue

        records.append(_build_boxscore(raw, now, team_lookup=team_lookup))
        time.sleep(delay)

    return records, skipped


def backfill_boxscores(
    delay: float = _BACKFILL_DELAY_SECONDS,
    season: int | None = None,
    max_workers: int = 4,
    force: bool = False,
) -> int:
    """Fetch and upsert boxscore data for every game in the game table.

    One-time (but re-runnable) backfill.  Groups game IDs from the ``game``
    table by year-month and fans the partitions out across up to
    ``max_workers`` concurrent threads, each fetching one month's games
    sequentially with the configured ``delay`` between requests.  Results are
    collected in the calling thread and committed in batches of 100 rows.

    API failures for individual games are logged and skipped; a failed
    partition does not abort the remaining partitions.  The ``season``
    filter restricts processing to a single season's month-buckets.

    When ``force`` is ``False`` (the default), game IDs that already have a
    row in the ``boxscore`` table are skipped before partitioning so that an
    interrupted backfill can be resumed without re-fetching already-loaded
    data.  Pass ``force=True`` to re-fetch all games regardless.

    Args:
        delay: Seconds to sleep between successive API calls within each
            worker.  Defaults to ``_BACKFILL_DELAY_SECONDS`` (0.3 s).
            Pass ``0`` in tests to keep runs fast.
        season: Optional season integer (e.g. ``20252026``).  When set, only
            games whose ``season`` column matches are processed.
        max_workers: Maximum number of concurrent worker threads (default 4).
            Low values avoid NHL API throttling; pass ``1`` for a fully
            sequential single-worker run.
        force: When ``True``, skip the already-loaded check and re-fetch every
            game.  Defaults to ``False``.

    Returns:
        Number of boxscores successfully upserted (skipped games are not
        counted).
    """
    query = db.select(Game.game_id, Game.game_date)
    if season is not None:
        query = query.where(Game.season == season)
    rows = db.session.execute(query).all()

    if not rows:
        return 0

    # Determine which game IDs already have a boxscore row so we can skip them.
    if not force:
        loaded_ids: set[int] = set(
            db.session.scalars(db.select(Boxscore.game_id)).all()
        )
        pending_rows = [(gid, gdate) for gid, gdate in rows if gid not in loaded_ids]
        skipped_count = len(rows) - len(pending_rows)
        if skipped_count:
            logger.info(
                '[backfill_boxscores] Skipping %d already-loaded game IDs', skipped_count
            )
        rows = pending_rows

    if not rows:
        return 0

    # Group game IDs by year-month for parallel fan-out.
    month_buckets: dict[str, list[int]] = {}
    for game_id, game_date in rows:
        ym = game_date[:7] if game_date else 'unknown'
        month_buckets.setdefault(ym, []).append(game_id)

    now = now_et()
    team_lookup = _load_team_lookup()
    all_records: list[Boxscore] = []
    total_skipped = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ym = {
            executor.submit(_fetch_month_partition, game_ids, delay, team_lookup, now): ym
            for ym, game_ids in sorted(month_buckets.items())
        }
        for future in as_completed(future_to_ym):
            ym = future_to_ym[future]
            try:
                records, skipped = future.result()
                all_records.extend(records)
                total_skipped += skipped
                logger.info('[backfill_boxscores] Partition %s: fetched %d', ym, len(records))
            except Exception as exc:
                logger.error('[backfill_boxscores] Partition %s failed: %s', ym, exc)

    # Write all fetched records to the DB in the calling thread,
    # committing every 100 rows to bound transaction size.
    count = 0
    for i, record in enumerate(all_records):
        db.session.merge(record)
        count += 1
        if (i + 1) % 100 == 0:
            db.session.commit()
            logger.info('[backfill_boxscores] Progress: committed %d rows', i + 1)

    db.session.commit()

    season_label = str(season) if season is not None else 'all'
    logger.info(
        '[backfill_boxscores] Season %s: %d upserted, %d skipped',
        season_label, count, total_skipped,
    )
    return count


def backfill_team_names() -> int:
    """Update boxscore rows with empty or NULL team names from the team table.

    Queries the team table to build a tri_code → display_name mapping, then
    finds any boxscore row whose away_name or home_name is NULL or empty and
    fills it from the mapping.  Idempotent: rows already populated are never
    touched.

    Returns:
        Number of boxscore rows updated.
    """
    from sqlalchemy import or_

    lookup = _load_team_lookup()
    if not lookup:
        return 0

    rows = db.session.scalars(
        db.select(Boxscore).where(
            or_(
                Boxscore.away_name.is_(None),
                Boxscore.away_name == '',
                Boxscore.home_name.is_(None),
                Boxscore.home_name == '',
            )
        )
    ).all()

    count = 0
    for row in rows:
        updated = False
        if not row.away_name and row.away_abbrev:
            resolved = lookup.get(row.away_abbrev, '')
            if resolved:
                row.away_name = resolved
                updated = True
        if not row.home_name and row.home_abbrev:
            resolved = lookup.get(row.home_abbrev, '')
            if resolved:
                row.home_name = resolved
                updated = True
        if updated:
            count += 1

    if count:
        db.session.commit()

    logger.info('[boxscore] backfill_team_names: updated %d rows', count)
    return count
