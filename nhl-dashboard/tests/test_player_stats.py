"""Tests for FactSkaterStats, FactGoalieStats models, persist functions,
and the refresh_boxscore_player_stats() APScheduler job (Issue #169).

Acceptance criteria covered:
  Scenario 1 — Skater stats ingested for a completed game (one row per
               (game_id, player_id), all columns populated).
  Scenario 2 — Goalie stats include decision, saves, and shots_against
               as separate integers; no save_shots_against composite string.
  Scenario 3 — Missing dim_player triggers biographical backfill before
               the fact row is written.
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import select

from models import Boxscore, DimPlayer, FactSkaterStats, FactGoalieStats


# ── Shared fixtures ────────────────────────────────────────────────────────────

_GAME_ID = 2026030247
_SKATER_ID = 8478402
_GOALIE_ID = 8476945
_BACKUP_ID = 8477293

# Minimal boxscore API response with playerByGameStats populated.
_BOXSCORE_API = {
    "id": _GAME_ID,
    "season": 20252026,
    "gameType": 3,
    "gameDate": "2026-06-01",
    "gameState": "FINAL",
    "venue": {"default": "Scotiabank Arena"},
    "startTimeUTC": "2026-06-01T23:00:00Z",
    "awayTeam": {"id": 10, "name": {"default": "Toronto Maple Leafs"}, "abbrev": "TOR", "score": 2, "sog": 28},
    "homeTeam": {"id": 6, "name": {"default": "Boston Bruins"}, "abbrev": "BOS", "score": 1, "sog": 30},
    "periodDescriptor": {"number": 3, "periodType": "REG"},
    "clock": {"timeRemaining": "00:00"},
    "playerByGameStats": {
        "awayTeam": {
            "forwards": [
                {
                    "playerId": _SKATER_ID,
                    "sweaterNumber": 97,
                    "name": {"firstName": {"default": "Connor"}, "lastName": {"default": "McDavid"}},
                    "position": "C",
                    "goals": 1,
                    "assists": 2,
                    "points": 3,
                    "plusMinus": 1,
                    "pim": 0,
                    "toi": "22:34",
                    "hits": 2,
                    "blockedShots": 1,
                    "powerPlayGoals": 1,
                    "powerPlayPoints": 2,
                    "shorthandedGoals": 0,
                    "faceoffWinningPctg": 52.4,
                    "giveaways": 1,
                    "takeaways": 2,
                    "shifts": 26,
                }
            ],
            "defense": [],
            "goalies": [
                {
                    "playerId": _GOALIE_ID,
                    "sweaterNumber": 35,
                    "name": {"firstName": {"default": "Ilya"}, "lastName": {"default": "Samsonov"}},
                    "toi": "60:00",
                    "goalsAgainst": 1,
                    "saveShotsAgainst": "29/30",
                    "savePctg": 0.9667,
                    "evenStrengthShotsAgainst": 22,
                    "powerPlayShotsAgainst": 5,
                    "shorthandedShotsAgainst": 3,
                    "pim": 0,
                    "starter": 1,
                    "decision": "W",
                }
            ],
        },
        "homeTeam": {
            "forwards": [],
            "defense": [],
            "goalies": [
                {
                    "playerId": _BACKUP_ID,
                    "sweaterNumber": 40,
                    "name": {"firstName": {"default": "Tuukka"}, "lastName": {"default": "Rask"}},
                    "toi": "00:00",
                    "goalsAgainst": 0,
                    "saveShotsAgainst": "0/0",
                    "savePctg": 0.0,
                    "evenStrengthShotsAgainst": 0,
                    "powerPlayShotsAgainst": 0,
                    "shorthandedShotsAgainst": 0,
                    "pim": 0,
                    "starter": 0,
                    # No decision — backup who didn't play
                }
            ],
        },
    },
}

_PLAYER_LANDING = {
    "playerId": _SKATER_ID,
    "firstName": {"default": "Connor"},
    "lastName": {"default": "McDavid"},
    "sweaterNumber": 97,
    "position": "C",
    "shootsCatches": "L",
    "heightInInches": 73,
    "weightInPounds": 193,
    "birthDate": "1997-01-13",
    "birthCountry": "CAN",
    "headshot": "https://assets.nhle.com/mugs/nhl/20252026/EDM/8478402.png",
}


def _seed_boxscore(db, game_id=_GAME_ID):
    """Insert a minimal Boxscore row so FK checks pass."""
    row = Boxscore(
        game_id=game_id,
        game_date="2026-06-01",
        game_state="FINAL",
        updated_at=datetime.now(timezone.utc),
    )
    db.session.add(row)
    db.session.commit()


def _seed_dim_player(db, player_id, position="C"):
    """Insert a minimal DimPlayer row."""
    row = DimPlayer(
        player_id=player_id,
        first_name="Test",
        last_name="Player",
        position=position,
        updated_at=datetime.now(timezone.utc),
    )
    db.session.add(row)
    db.session.commit()


# ── FactSkaterStats model ─────────────────────────────────────────────────────


class TestFactSkaterStatsModel:
    def test_fact_skater_stats_stores_all_columns(self, db):
        """FactSkaterStats row persists all expected stat columns."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        row = FactSkaterStats(
            game_id=_GAME_ID,
            player_id=_SKATER_ID,
            team_id=10,
            side="away",
            position_group="forwards",
            position="C",
            goals=1,
            assists=2,
            points=3,
            plus_minus=1,
            pim=0,
            toi="22:34",
            hits=2,
            blocked_shots=1,
            pp_goals=1,
            pp_points=2,
            sh_goals=0,
            faceoff_win_pct=52.4,
            giveaways=1,
            takeaways=2,
            shifts=26,
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID))
        assert retrieved is not None
        assert retrieved.game_id == _GAME_ID
        assert retrieved.player_id == _SKATER_ID
        assert retrieved.team_id == 10
        assert retrieved.side == "away"
        assert retrieved.position_group == "forwards"
        assert retrieved.position == "C"
        assert retrieved.goals == 1
        assert retrieved.assists == 2
        assert retrieved.points == 3
        assert retrieved.plus_minus == 1
        assert retrieved.pim == 0
        assert retrieved.toi == "22:34"
        assert retrieved.hits == 2
        assert retrieved.blocked_shots == 1
        assert retrieved.pp_goals == 1
        assert retrieved.pp_points == 2
        assert retrieved.sh_goals == 0
        assert abs(retrieved.faceoff_win_pct - 52.4) < 0.01
        assert retrieved.giveaways == 1
        assert retrieved.takeaways == 2
        assert retrieved.shifts == 26

    def test_fact_skater_stats_composite_pk(self, db):
        """(game_id, player_id) is the composite primary key."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        db.session.add(FactSkaterStats(game_id=_GAME_ID, player_id=_SKATER_ID, team_id=10, side="away", position_group="forwards"))
        db.session.commit()

        retrieved = db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID))
        assert retrieved is not None

    def test_fact_skater_stats_upsert_idempotent(self, db):
        """Merging the same (game_id, player_id) twice leaves exactly one row."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        db.session.add(FactSkaterStats(game_id=_GAME_ID, player_id=_SKATER_ID, team_id=10, side="away", position_group="forwards", goals=0))
        db.session.commit()

        db.session.merge(FactSkaterStats(game_id=_GAME_ID, player_id=_SKATER_ID, team_id=10, side="away", position_group="forwards", goals=1))
        db.session.commit()

        rows = db.session.scalars(select(FactSkaterStats).where(FactSkaterStats.game_id == _GAME_ID)).all()
        assert len(rows) == 1
        assert rows[0].goals == 1

    def test_fact_skater_stats_table_name(self, db):
        """SQLAlchemy model maps to the 'fact_skater_stats' table."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert "fact_skater_stats" in inspector.get_table_names()


# ── FactGoalieStats model ─────────────────────────────────────────────────────


class TestFactGoalieStatsModel:
    def test_fact_goalie_stats_stores_saves_and_shots_against_as_integers(self, db):
        """saves and shots_against are stored as separate INTEGER columns (not a composite string)."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")

        row = FactGoalieStats(
            game_id=_GAME_ID,
            player_id=_GOALIE_ID,
            team_id=10,
            side="away",
            starter=1,
            toi="60:00",
            goals_against=1,
            saves=29,
            shots_against=30,
            save_pct=0.9667,
            es_shots_against=22,
            pp_shots_against=5,
            sh_shots_against=3,
            pim=0,
            decision="W",
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(FactGoalieStats, (_GAME_ID, _GOALIE_ID))
        assert retrieved is not None
        assert retrieved.saves == 29
        assert retrieved.shots_against == 30
        assert retrieved.decision == "W"
        assert isinstance(retrieved.saves, int)
        assert isinstance(retrieved.shots_against, int)

    def test_fact_goalie_stats_decision_null_for_backup(self, db):
        """decision is NULL for a backup goalie who received no decision."""
        _seed_boxscore(db)
        _seed_dim_player(db, _BACKUP_ID, position="G")

        row = FactGoalieStats(
            game_id=_GAME_ID,
            player_id=_BACKUP_ID,
            team_id=6,
            side="home",
            starter=0,
            toi="00:00",
            goals_against=0,
            saves=0,
            shots_against=0,
            decision=None,
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(FactGoalieStats, (_GAME_ID, _BACKUP_ID))
        assert retrieved.decision is None

    def test_fact_goalie_stats_no_save_shots_against_column(self, db):
        """FactGoalieStats has no save_shots_against composite string column."""
        assert not hasattr(FactGoalieStats, "save_shots_against")

    def test_fact_goalie_stats_table_name(self, db):
        """SQLAlchemy model maps to the 'fact_goalie_stats' table."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert "fact_goalie_stats" in inspector.get_table_names()

    def test_fact_goalie_stats_upsert_idempotent(self, db):
        """Merging the same (game_id, player_id) twice leaves exactly one row."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")

        db.session.add(FactGoalieStats(game_id=_GAME_ID, player_id=_GOALIE_ID, team_id=10, side="away", saves=28, shots_against=30))
        db.session.commit()

        db.session.merge(FactGoalieStats(game_id=_GAME_ID, player_id=_GOALIE_ID, team_id=10, side="away", saves=29, shots_against=30))
        db.session.commit()

        rows = db.session.scalars(select(FactGoalieStats).where(FactGoalieStats.game_id == _GAME_ID)).all()
        assert len(rows) == 1
        assert rows[0].saves == 29


# ── persist_skater_stats ───────────────────────────────────────────────────────


class TestPersistSkaterStats:
    def test_persist_skater_stats_inserts_one_row_per_player(self, db):
        """persist_skater_stats() upserts one FactSkaterStats row per skater."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        from services.player_stats import persist_skater_stats
        count = persist_skater_stats(_GAME_ID, _BOXSCORE_API)

        assert count == 1
        row = db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID))
        assert row is not None

    def test_persist_skater_stats_maps_all_columns(self, db):
        """persist_skater_stats() maps every API skater field to the correct DB column."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        from services.player_stats import persist_skater_stats
        persist_skater_stats(_GAME_ID, _BOXSCORE_API)

        row = db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID))
        assert row.goals == 1
        assert row.assists == 2
        assert row.points == 3
        assert row.plus_minus == 1
        assert row.pim == 0
        assert row.toi == "22:34"
        assert row.hits == 2
        assert row.blocked_shots == 1
        assert row.pp_goals == 1
        assert row.pp_points == 2
        assert row.sh_goals == 0
        assert abs(row.faceoff_win_pct - 52.4) < 0.01
        assert row.giveaways == 1
        assert row.takeaways == 2
        assert row.shifts == 26
        assert row.side == "away"
        assert row.position_group == "forwards"
        assert row.position == "C"

    def test_persist_skater_stats_upserts_not_appends(self, db):
        """Running persist_skater_stats() twice leaves exactly one row per (game, player)."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        from services.player_stats import persist_skater_stats
        persist_skater_stats(_GAME_ID, _BOXSCORE_API)
        persist_skater_stats(_GAME_ID, _BOXSCORE_API)

        rows = db.session.scalars(
            select(FactSkaterStats).where(FactSkaterStats.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_persist_skater_stats_returns_count(self, db):
        """persist_skater_stats() returns the number of rows upserted."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)

        from services.player_stats import persist_skater_stats
        count = persist_skater_stats(_GAME_ID, _BOXSCORE_API)
        assert count == 1


# ── persist_goalie_stats ───────────────────────────────────────────────────────


class TestPersistGoalieStats:
    def test_persist_goalie_stats_inserts_one_row_per_goalie(self, db):
        """persist_goalie_stats() upserts one FactGoalieStats row per goalie."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        from services.player_stats import persist_goalie_stats
        count = persist_goalie_stats(_GAME_ID, _BOXSCORE_API)

        assert count == 2

    def test_persist_goalie_stats_parses_saves_and_shots_against(self, db):
        """persist_goalie_stats() splits saveShotsAgainst '29/30' into saves=29, shots_against=30."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        from services.player_stats import persist_goalie_stats
        persist_goalie_stats(_GAME_ID, _BOXSCORE_API)

        row = db.session.get(FactGoalieStats, (_GAME_ID, _GOALIE_ID))
        assert row.saves == 29
        assert row.shots_against == 30

    def test_persist_goalie_stats_captures_decision(self, db):
        """persist_goalie_stats() stores 'W' decision for winning goalie."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        from services.player_stats import persist_goalie_stats
        persist_goalie_stats(_GAME_ID, _BOXSCORE_API)

        row = db.session.get(FactGoalieStats, (_GAME_ID, _GOALIE_ID))
        assert row.decision == "W"

    def test_persist_goalie_stats_null_decision_for_backup(self, db):
        """persist_goalie_stats() stores NULL decision for a backup goalie with no decision key."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        from services.player_stats import persist_goalie_stats
        persist_goalie_stats(_GAME_ID, _BOXSCORE_API)

        backup = db.session.get(FactGoalieStats, (_GAME_ID, _BACKUP_ID))
        assert backup.decision is None

    def test_persist_goalie_stats_upserts_not_appends(self, db):
        """Running persist_goalie_stats() twice leaves exactly one row per (game, goalie)."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        from services.player_stats import persist_goalie_stats
        persist_goalie_stats(_GAME_ID, _BOXSCORE_API)
        persist_goalie_stats(_GAME_ID, _BOXSCORE_API)

        rows = db.session.scalars(
            select(FactGoalieStats).where(FactGoalieStats.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 2

    def test_persist_goalie_stats_returns_count(self, db):
        """persist_goalie_stats() returns the number of rows upserted."""
        _seed_boxscore(db)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        from services.player_stats import persist_goalie_stats
        count = persist_goalie_stats(_GAME_ID, _BOXSCORE_API)
        assert count == 2


# ── Scenario 3: dim_player backfill on missing player ─────────────────────────


class TestDimPlayerBackfillOnMissingPlayer:
    def test_persist_skater_stats_triggers_backfill_for_missing_player(self, db):
        """persist_skater_stats() triggers dim_player backfill when player_id is absent."""
        _seed_boxscore(db)
        # Do NOT seed dim_player for _SKATER_ID

        assert db.session.get(DimPlayer, _SKATER_ID) is None

        with patch("nhl_client.get_player_landing", return_value=_PLAYER_LANDING):
            from services.player_stats import persist_skater_stats
            persist_skater_stats(_GAME_ID, _BOXSCORE_API)

        # dim_player must be created before the fact row is written
        assert db.session.get(DimPlayer, _SKATER_ID) is not None
        assert db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID)) is not None

    def test_persist_goalie_stats_triggers_backfill_for_missing_goalie(self, db):
        """persist_goalie_stats() triggers dim_player backfill when goalie player_id is absent."""
        _seed_boxscore(db)

        goalie_landing = {
            "playerId": _GOALIE_ID,
            "firstName": {"default": "Ilya"},
            "lastName": {"default": "Samsonov"},
            "sweaterNumber": 35,
            "position": "G",
            "shootsCatches": "L",
            "heightInInches": 74,
            "weightInPounds": 182,
            "birthDate": "1997-02-22",
            "birthCountry": "RUS",
            "headshot": "",
        }
        backup_landing = {
            "playerId": _BACKUP_ID,
            "firstName": {"default": "Tuukka"},
            "lastName": {"default": "Rask"},
            "sweaterNumber": 40,
            "position": "G",
            "shootsCatches": "L",
            "heightInInches": 74,
            "weightInPounds": 176,
            "birthDate": "1987-03-10",
            "birthCountry": "FIN",
            "headshot": "",
        }

        def fake_landing(player_id):
            return {_GOALIE_ID: goalie_landing, _BACKUP_ID: backup_landing}[player_id]

        with patch("nhl_client.get_player_landing", side_effect=fake_landing):
            from services.player_stats import persist_goalie_stats
            persist_goalie_stats(_GAME_ID, _BOXSCORE_API)

        assert db.session.get(DimPlayer, _GOALIE_ID) is not None
        assert db.session.get(DimPlayer, _BACKUP_ID) is not None

    def test_persist_skater_stats_skips_fact_row_when_backfill_fails(self, db):
        """When dim_player backfill fails, the fact row is not written (no orphaned FK)."""
        _seed_boxscore(db)

        with patch("nhl_client.get_player_landing", side_effect=RuntimeError("API down")):
            from services.player_stats import persist_skater_stats
            count = persist_skater_stats(_GAME_ID, _BOXSCORE_API)

        # No fact row should be written for the player whose backfill failed.
        assert db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID)) is None
        assert count == 0


# ── refresh_boxscore_player_stats ──────────────────────────────────────────────


class TestRefreshBoxscorePlayerStats:
    def test_refresh_boxscore_player_stats_processes_final_boxscores(self, db):
        """refresh_boxscore_player_stats() ingests stats for FINAL game boxscores."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.player_stats import refresh_boxscore_player_stats
            skaters, goalies = refresh_boxscore_player_stats()

        assert skaters >= 1
        assert goalies >= 1

    def test_refresh_boxscore_player_stats_is_idempotent(self, db):
        """Running refresh_boxscore_player_stats() twice leaves exactly one row per (game, player)."""
        _seed_boxscore(db)
        _seed_dim_player(db, _SKATER_ID)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.player_stats import refresh_boxscore_player_stats
            refresh_boxscore_player_stats()
            refresh_boxscore_player_stats()

        skater_rows = db.session.scalars(
            select(FactSkaterStats).where(FactSkaterStats.game_id == _GAME_ID)
        ).all()
        goalie_rows = db.session.scalars(
            select(FactGoalieStats).where(FactGoalieStats.game_id == _GAME_ID)
        ).all()
        assert len(skater_rows) == 1
        assert len(goalie_rows) == 2

    def test_refresh_boxscore_player_stats_skips_api_failure(self, db):
        """refresh_boxscore_player_stats() continues when one game's API call fails."""
        # Two boxscore rows
        db.session.add(Boxscore(game_id=_GAME_ID, game_date="2026-06-01", game_state="FINAL", updated_at=datetime.now(timezone.utc)))
        db.session.add(Boxscore(game_id=_GAME_ID + 1, game_date="2026-06-01", game_state="FINAL", updated_at=datetime.now(timezone.utc)))
        db.session.commit()
        _seed_dim_player(db, _SKATER_ID)
        _seed_dim_player(db, _GOALIE_ID, position="G")
        _seed_dim_player(db, _BACKUP_ID, position="G")

        def side_effect(game_id):
            if game_id == _GAME_ID:
                raise RuntimeError("API timeout")
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=side_effect):
            from services.player_stats import refresh_boxscore_player_stats
            skaters, goalies = refresh_boxscore_player_stats()

        # The failed game produces 0; the other game may produce rows
        assert db.session.get(FactSkaterStats, (_GAME_ID, _SKATER_ID)) is None

    def test_refresh_boxscore_player_stats_returns_zero_when_no_boxscores(self, db):
        """refresh_boxscore_player_stats() returns (0, 0) when boxscore table is empty."""
        from services.player_stats import refresh_boxscore_player_stats
        skaters, goalies = refresh_boxscore_player_stats()
        assert skaters == 0
        assert goalies == 0


# ── APScheduler job wiring ─────────────────────────────────────────────────────


class TestSchedulerJobWiring:
    def test_refresh_player_stats_job_exists_in_scheduler(self):
        """scheduler._refresh_player_stats is defined and callable."""
        import scheduler as sched
        assert callable(getattr(sched, "_refresh_player_stats", None))

    def test_refresh_player_stats_job_calls_service(self, app):
        """_refresh_player_stats() delegates to services.player_stats.refresh_boxscore_player_stats."""
        import scheduler as sched
        sched._app = app
        with patch("services.player_stats.refresh_boxscore_player_stats", return_value=(0, 0)) as mock_fn:
            sched._with_ctx(sched._refresh_player_stats)()
        mock_fn.assert_called_once()
