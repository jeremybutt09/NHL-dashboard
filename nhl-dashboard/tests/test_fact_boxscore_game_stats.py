"""Tests for FactBoxscoreGameStats model and persist_fact_boxscore_game_stats()
function (Issue #170).

Acceptance criteria covered:
  Scenario — Game-level stats are persisted to the new fact table:
    Given a completed NHL game available from /v1/gamecenter/{id}/boxscore,
    when persist_fact_boxscore_game_stats() runs, one row per game_id is
    upserted into fact_boxscore_game_stats with all fields populated,
    including away_team_id and home_team_id.
"""
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import FactBoxscoreGameStats, Game


# ── Shared fixtures ────────────────────────────────────────────────────────────

_TODAY = date.today().isoformat()
_GAME_ID = 2026030247

_BOXSCORE_API = {
    "id": _GAME_ID,
    "season": 20252026,
    "gameType": 3,
    "gameDate": _TODAY,
    "gameState": "FINAL",
    "venue": {"default": "Scotiabank Arena"},
    "startTimeUTC": f"{_TODAY}T23:00:00Z",
    "awayTeam": {
        "id": 10,
        "name": {"default": "Toronto Maple Leafs"},
        "abbrev": "TOR",
        "score": 3,
        "sog": 28,
    },
    "homeTeam": {
        "id": 6,
        "name": {"default": "Boston Bruins"},
        "abbrev": "BOS",
        "score": 2,
        "sog": 30,
    },
    "periodDescriptor": {"number": 3, "periodType": "REG"},
    "clock": {"timeRemaining": "00:00"},
}

_BOXSCORE_API_LIVE = dict(
    _BOXSCORE_API,
    gameState="LIVE",
    periodDescriptor={"number": 2, "periodType": "REG"},
    clock={"timeRemaining": "12:34"},
)

_BOXSCORE_API_OT = dict(
    _BOXSCORE_API,
    gameState="FINAL",
    periodDescriptor={"number": 4, "periodType": "OT"},
    clock={"timeRemaining": "00:00"},
)


# ── FactBoxscoreGameStats model ────────────────────────────────────────────────


class TestFactBoxscoreGameStatsModel:
    def test_fact_boxscore_game_stats_table_name(self, db):
        """SQLAlchemy model maps to the 'fact_boxscore_game_stats' table."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert "fact_boxscore_game_stats" in inspector.get_table_names()

    def test_fact_boxscore_game_stats_stores_all_columns(self, db):
        """FactBoxscoreGameStats row persists all expected columns."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        row = FactBoxscoreGameStats(
            game_id=_GAME_ID,
            season_id=20252026,
            game_type=3,
            game_date=_TODAY,
            venue="Scotiabank Arena",
            start_time_est=now,
            game_state="FINAL",
            away_team_id=10,
            away_abbrev="TOR",
            away_name="Toronto Maple Leafs",
            away_score=3,
            away_sog=28,
            home_team_id=6,
            home_abbrev="BOS",
            home_name="Boston Bruins",
            home_score=2,
            home_sog=30,
            clock="00:00",
            period="3rd",
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert retrieved is not None
        assert retrieved.game_id == _GAME_ID
        assert retrieved.season_id == 20252026
        assert retrieved.game_type == 3
        assert retrieved.game_date == _TODAY
        assert retrieved.venue == "Scotiabank Arena"
        assert retrieved.start_time_est is not None
        assert retrieved.game_state == "FINAL"
        assert retrieved.away_team_id == 10
        assert retrieved.away_abbrev == "TOR"
        assert retrieved.away_name == "Toronto Maple Leafs"
        assert retrieved.away_score == 3
        assert retrieved.away_sog == 28
        assert retrieved.home_team_id == 6
        assert retrieved.home_abbrev == "BOS"
        assert retrieved.home_name == "Boston Bruins"
        assert retrieved.home_score == 2
        assert retrieved.home_sog == 30
        assert retrieved.clock == "00:00"
        assert retrieved.period == "3rd"

    def test_fact_boxscore_game_stats_game_id_is_pk(self, db):
        """game_id is the sole integer primary key."""
        row = FactBoxscoreGameStats(game_id=9999)
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(FactBoxscoreGameStats, 9999)
        assert retrieved is not None
        assert retrieved.game_id == 9999

    def test_fact_boxscore_game_stats_upsert_idempotent(self, db):
        """Merging the same game_id twice leaves exactly one row."""
        db.session.add(FactBoxscoreGameStats(game_id=_GAME_ID, away_score=0))
        db.session.commit()

        db.session.merge(FactBoxscoreGameStats(game_id=_GAME_ID, away_score=3))
        db.session.commit()

        rows = db.session.scalars(
            select(FactBoxscoreGameStats).where(
                FactBoxscoreGameStats.game_id == _GAME_ID
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].away_score == 3

    def test_fact_boxscore_game_stats_has_away_team_id(self, db):
        """FactBoxscoreGameStats has away_team_id column (absent from boxscore table)."""
        assert hasattr(FactBoxscoreGameStats, "away_team_id")

    def test_fact_boxscore_game_stats_has_home_team_id(self, db):
        """FactBoxscoreGameStats has home_team_id column (absent from boxscore table)."""
        assert hasattr(FactBoxscoreGameStats, "home_team_id")


# ── persist_fact_boxscore_game_stats ───────────────────────────────────────────


class TestPersistFactBoxscoreGameStats:
    def test_persist_fact_boxscore_game_stats_inserts_one_row(self, db):
        """persist_fact_boxscore_game_stats() upserts one row into fact_boxscore_game_stats."""
        from services.boxscore import persist_fact_boxscore_game_stats
        count = persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)

        assert count == 1
        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert row is not None

    def test_persist_fact_boxscore_game_stats_maps_team_ids(self, db):
        """persist_fact_boxscore_game_stats() maps awayTeam.id and homeTeam.id."""
        from services.boxscore import persist_fact_boxscore_game_stats
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)

        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert row.away_team_id == 10
        assert row.home_team_id == 6

    def test_persist_fact_boxscore_game_stats_maps_all_fields(self, db):
        """persist_fact_boxscore_game_stats() maps every API field to the correct DB column."""
        from services.boxscore import persist_fact_boxscore_game_stats
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)

        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert row.season_id == 20252026
        assert row.game_type == 3
        assert row.game_date == _TODAY
        assert row.venue == "Scotiabank Arena"
        assert row.start_time_est is not None
        assert row.game_state == "FINAL"
        assert row.away_abbrev == "TOR"
        assert row.away_name == "Toronto Maple Leafs"
        assert row.away_score == 3
        assert row.away_sog == 28
        assert row.home_abbrev == "BOS"
        assert row.home_name == "Boston Bruins"
        assert row.home_score == 2
        assert row.home_sog == 30
        assert row.clock == "00:00"
        assert row.period == "3rd"

    def test_persist_fact_boxscore_game_stats_converts_utc_to_eastern(self, db):
        """persist_fact_boxscore_game_stats() stores start_time_est converted from UTC to ET."""
        from services.boxscore import persist_fact_boxscore_game_stats
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)

        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        # 23:00 UTC = 19:00 ET (UTC-4 in EDT)
        assert row.start_time_est is not None
        assert row.start_time_est.hour == 19

    def test_persist_fact_boxscore_game_stats_upserts_not_appends(self, db):
        """Running persist_fact_boxscore_game_stats() twice leaves exactly one row."""
        from services.boxscore import persist_fact_boxscore_game_stats
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)

        rows = db.session.scalars(
            select(FactBoxscoreGameStats).where(
                FactBoxscoreGameStats.game_id == _GAME_ID
            )
        ).all()
        assert len(rows) == 1

    def test_persist_fact_boxscore_game_stats_overwrites_on_update(self, db):
        """Second call overwrites changed live fields (score, game_state)."""
        from services.boxscore import persist_fact_boxscore_game_stats
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API_LIVE)

        updated = dict(_BOXSCORE_API_LIVE)
        updated["awayTeam"] = dict(updated["awayTeam"], score=4)
        updated["gameState"] = "FINAL"
        persist_fact_boxscore_game_stats(_GAME_ID, updated)

        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert row.away_score == 4
        assert row.game_state == "FINAL"

    def test_persist_fact_boxscore_game_stats_returns_count(self, db):
        """persist_fact_boxscore_game_stats() returns 1 on success."""
        from services.boxscore import persist_fact_boxscore_game_stats
        count = persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API)
        assert count == 1

    def test_persist_fact_boxscore_game_stats_parses_ot_period(self, db):
        """persist_fact_boxscore_game_stats() stores 'OT' for overtime periodType."""
        from services.boxscore import persist_fact_boxscore_game_stats
        persist_fact_boxscore_game_stats(_GAME_ID, _BOXSCORE_API_OT)

        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert row.period == "OT"

    def test_persist_fact_boxscore_game_stats_skips_empty_response(self, db):
        """persist_fact_boxscore_game_stats() returns 0 when raw is empty or lacks 'id'."""
        from services.boxscore import persist_fact_boxscore_game_stats
        count = persist_fact_boxscore_game_stats(_GAME_ID, {})
        assert count == 0
        assert db.session.get(FactBoxscoreGameStats, _GAME_ID) is None


# ── refresh_boxscores integration ─────────────────────────────────────────────


class TestRefreshBoxscoresWritesFactTable:
    def _seed_game(self, db, game_id=_GAME_ID):
        db.session.add(Game(game_id=game_id, game_date=_TODAY))
        db.session.commit()

    def test_refresh_boxscores_also_writes_fact_boxscore_game_stats(self, db):
        """refresh_boxscores() upserts a row into fact_boxscore_game_stats alongside boxscore."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(FactBoxscoreGameStats, _GAME_ID)
        assert row is not None
        assert row.away_team_id == 10
        assert row.home_team_id == 6

    def test_refresh_boxscores_fact_table_has_same_game_id_as_boxscore(self, db):
        """refresh_boxscores() writes matching game_id to both boxscore and fact_boxscore_game_stats."""
        from models import Boxscore
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        assert db.session.get(Boxscore, _GAME_ID) is not None
        assert db.session.get(FactBoxscoreGameStats, _GAME_ID) is not None

    def test_refresh_boxscores_fact_table_skipped_on_api_failure(self, db):
        """refresh_boxscores() does not write fact_boxscore_game_stats when API call fails."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", side_effect=RuntimeError("timeout")):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        assert db.session.get(FactBoxscoreGameStats, _GAME_ID) is None
