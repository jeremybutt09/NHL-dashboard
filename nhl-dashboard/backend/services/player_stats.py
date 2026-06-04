"""Per-game player statistics ingestion from the NHL boxscore API.

Source: GET https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore
        → playerByGameStats.{awayTeam,homeTeam}.{forwards,defense,goalies}

Tables: fact_skater_stats (FactSkaterStats), fact_goalie_stats (FactGoalieStats)

Both tables use (game_id, player_id) as their composite primary key so that
db.session.merge() provides idempotent upserts on live or re-processed games.

dim_player existence is checked before writing any fact row.  When a player_id
is absent from dim_player (e.g. a call-up or emergency recall), a biographical
backfill is triggered via nhl_client.get_player_landing() before the fact row
is written.  If that backfill fails the fact row is skipped to prevent orphaned
foreign keys.
"""
import logging
from datetime import datetime, timezone

import nhl_client
from extensions import db
from models import Boxscore, DimPlayer, FactGoalieStats, FactSkaterStats

logger = logging.getLogger(__name__)


def _ensure_dim_player(player_id: int) -> bool:
    """Return True if dim_player has a row for player_id; trigger backfill if not.

    Args:
        player_id: NHL numeric player identifier.

    Returns:
        True when the player exists in dim_player after any backfill attempt.
        False when the player is missing and the backfill failed.
    """
    if db.session.get(DimPlayer, player_id):
        return True

    try:
        raw = nhl_client.get_player_landing(player_id)
        first = raw.get('firstName', {})
        last = raw.get('lastName', {})
        first_name = first.get('default', '') if isinstance(first, dict) else (first or '')
        last_name = last.get('default', '') if isinstance(last, dict) else (last or '')

        player = DimPlayer(
            player_id=player_id,
            first_name=first_name,
            last_name=last_name,
            sweater_number=raw.get('sweaterNumber'),
            position=raw.get('position'),
            shoots_catches=raw.get('shootsCatches'),
            height_in_inches=raw.get('heightInInches'),
            weight_in_pounds=raw.get('weightInPounds'),
            birth_date=raw.get('birthDate'),
            birth_country=raw.get('birthCountry'),
            headshot_url=raw.get('headshot'),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.merge(player)
        db.session.commit()
        logger.info('[player_stats] Backfilled dim_player for player_id=%s (%s %s)', player_id, first_name, last_name)
        return True
    except Exception as exc:
        logger.warning('[player_stats] dim_player backfill failed for player_id=%s: %s', player_id, exc)
        return False


def _parse_save_shots(save_shots_against: str | None) -> tuple[int | None, int | None]:
    """Parse the API 'saves/shots' composite string into separate integers.

    Args:
        save_shots_against: String in 'saves/shots' format (e.g. '29/30'),
            or None / empty when the goalie faced no shots.

    Returns:
        Tuple of (saves, shots_against) as ints, or (None, None) on failure.
    """
    if not save_shots_against:
        return None, None
    try:
        parts = save_shots_against.split('/')
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None, None


def persist_skater_stats(game_id: int, raw: dict) -> int:
    """Upsert FactSkaterStats rows for all forwards and defensemen in a boxscore.

    For each player in playerByGameStats.*.forwards and *.defense, checks that
    a dim_player row exists (backfilling via the player landing endpoint if not),
    then upserts the per-game stat row.  Players whose dim_player backfill fails
    are logged and skipped.

    Args:
        game_id: NHL game identifier matching an existing boxscore row.
        raw: Full /v1/gamecenter/{id}/boxscore API response dict.

    Returns:
        Number of FactSkaterStats rows successfully upserted.
    """
    pbgs = raw.get('playerByGameStats', {})
    away_team_id = raw.get('awayTeam', {}).get('id')
    home_team_id = raw.get('homeTeam', {}).get('id')

    sides = [
        ('away', away_team_id, pbgs.get('awayTeam', {})),
        ('home', home_team_id, pbgs.get('homeTeam', {})),
    ]

    count = 0
    for side, team_id, side_data in sides:
        for group in ('forwards', 'defense'):
            for p in side_data.get(group, []):
                player_id = p.get('playerId')
                if player_id is None:
                    continue

                if not _ensure_dim_player(player_id):
                    continue

                row = FactSkaterStats(
                    game_id=game_id,
                    player_id=player_id,
                    team_id=team_id,
                    side=side,
                    position_group=group,
                    position=p.get('position'),
                    goals=p.get('goals'),
                    assists=p.get('assists'),
                    points=p.get('points'),
                    plus_minus=p.get('plusMinus'),
                    pim=p.get('pim'),
                    toi=p.get('toi'),
                    hits=p.get('hits'),
                    blocked_shots=p.get('blockedShots'),
                    pp_goals=p.get('powerPlayGoals'),
                    pp_points=p.get('powerPlayPoints'),
                    sh_goals=p.get('shorthandedGoals'),
                    faceoff_win_pct=p.get('faceoffWinningPctg'),
                    giveaways=p.get('giveaways'),
                    takeaways=p.get('takeaways'),
                    shifts=p.get('shifts'),
                )
                db.session.merge(row)
                count += 1

    if count:
        db.session.commit()
    return count


def persist_goalie_stats(game_id: int, raw: dict) -> int:
    """Upsert FactGoalieStats rows for all goalies in a boxscore.

    Parses the 'saves/shots' saveShotsAgainst composite string into separate
    saves and shots_against integer columns.  decision is stored as TEXT
    (W/L/OTL) or NULL for backup goalies who received no decision.

    Args:
        game_id: NHL game identifier matching an existing boxscore row.
        raw: Full /v1/gamecenter/{id}/boxscore API response dict.

    Returns:
        Number of FactGoalieStats rows successfully upserted.
    """
    pbgs = raw.get('playerByGameStats', {})
    away_team_id = raw.get('awayTeam', {}).get('id')
    home_team_id = raw.get('homeTeam', {}).get('id')

    sides = [
        ('away', away_team_id, pbgs.get('awayTeam', {})),
        ('home', home_team_id, pbgs.get('homeTeam', {})),
    ]

    count = 0
    for side, team_id, side_data in sides:
        for p in side_data.get('goalies', []):
            player_id = p.get('playerId')
            if player_id is None:
                continue

            if not _ensure_dim_player(player_id):
                continue

            saves, shots_against = _parse_save_shots(p.get('saveShotsAgainst'))

            row = FactGoalieStats(
                game_id=game_id,
                player_id=player_id,
                team_id=team_id,
                side=side,
                starter=p.get('starter'),
                toi=p.get('toi'),
                goals_against=p.get('goalsAgainst'),
                saves=saves,
                shots_against=shots_against,
                save_pct=p.get('savePctg'),
                es_shots_against=p.get('evenStrengthShotsAgainst'),
                pp_shots_against=p.get('powerPlayShotsAgainst'),
                sh_shots_against=p.get('shorthandedShotsAgainst'),
                pim=p.get('pim'),
                decision=p.get('decision'),
            )
            db.session.merge(row)
            count += 1

    if count:
        db.session.commit()
    return count


def refresh_boxscore_player_stats() -> tuple[int, int]:
    """Fetch per-player stats for all boxscore rows and upsert fact tables.

    Iterates every row in the boxscore table, calls get_boxscore() for each
    game_id, and calls persist_skater_stats() + persist_goalie_stats().
    Individual game API failures are logged and skipped so one bad game does
    not block the rest.

    Intended to run as an APScheduler job after refresh_boxscores() so that
    player stats stay current during live games.

    Returns:
        Tuple of (total_skaters_upserted, total_goalies_upserted).
    """
    game_ids = db.session.scalars(db.select(Boxscore.game_id)).all()

    if not game_ids:
        return 0, 0

    total_skaters = 0
    total_goalies = 0

    for game_id in game_ids:
        try:
            raw = nhl_client.get_boxscore(game_id)
        except Exception as exc:
            logger.warning('[player_stats] Failed to fetch boxscore for game %s: %s', game_id, exc)
            continue

        if not raw or 'id' not in raw:
            logger.warning('[player_stats] Empty boxscore response for game %s, skipping', game_id)
            continue

        try:
            skaters = persist_skater_stats(game_id, raw)
            goalies = persist_goalie_stats(game_id, raw)
            total_skaters += skaters
            total_goalies += goalies
        except Exception as exc:
            logger.warning('[player_stats] Failed to persist player stats for game %s: %s', game_id, exc)

    logger.info('[player_stats] refresh complete: %d skater rows, %d goalie rows', total_skaters, total_goalies)
    return total_skaters, total_goalies
