"""Tests for NhlHistoricalGame model, ingest_historical_games(),
refresh_recent_historical_games(), and backfill-historical CLI command
(Issues #121, #122, #127)."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import NhlHistoricalGame

# Dynamic dates so tests remain valid over time
_RECENT_DATE = (date.today() - timedelta(days=5)).isoformat()   # within 30-day window
_OLD_DATE = (date.today() - timedelta(days=40)).isoformat()     # outside 30-day window

_RECENT_GAME = {
    "id": 2026020100,
    "easternStartTime": "07:30 PM",
    "gameDate": _RECENT_DATE,
    "gameNumber": 100,
    "gameScheduleStateId": 1,
    "gameStateId": 7,
    "gameType": 2,
    "homeScore": 3,
    "homeTeamId": 10,
    "period": 3,
    "season": 20252026,
    "visitingScore": 2,
    "visitingTeamId": 15,
}

_OLD_GAME = {
    "id": 2025010001,
    "easternStartTime": "07:00 PM",
    "gameDate": _OLD_DATE,
    "gameNumber": 1,
    "gameScheduleStateId": 1,
    "gameStateId": 7,
    "gameType": 2,
    "homeScore": 2,
    "homeTeamId": 5,
    "period": 3,
    "season": 20242025,
    "visitingScore": 1,
    "visitingTeamId": 8,
}


# ── Sample API data ───────────────────────────────────────────────────────────

_GAME_1 = {
    "id": 2026020001,
    "easternStartTime": "07:30 PM",
    "gameDate": "2026-01-10",
    "gameNumber": 1,
    "gameScheduleStateId": 1,
    "gameStateId": 4,
    "gameType": 2,
    "homeScore": 3,
    "homeTeamId": 10,
    "period": 3,
    "season": 20252026,
    "visitingScore": 2,
    "visitingTeamId": 15,
}

_GAME_2 = {
    "id": 2026020002,
    "easternStartTime": "09:00 PM",
    "gameDate": "2026-01-11",
    "gameNumber": 2,
    "gameScheduleStateId": 1,
    "gameStateId": 4,
    "gameType": 2,
    "homeScore": 1,
    "homeTeamId": 20,
    "period": 3,
    "season": 20252026,
    "visitingScore": 4,
    "visitingTeamId": 25,
}


# ── NhlHistoricalGame model ───────────────────────────────────────────────────

class TestNhlHistoricalGameModel:
    def test_nhl_historical_game_model_stores_all_columns(self, db):
        """NhlHistoricalGame row persists all 13 columns from the NHL API game shape."""
        row = NhlHistoricalGame(
            game_id=2026020001,
            eastern_start_time="07:30 PM",
            game_date="2026-01-10",
            game_number=1,
            game_schedule_state_id=1,
            game_state_id=4,
            game_type=2,
            home_score=3,
            home_team_id=10,
            period=3,
            season=20252026,
            visiting_score=2,
            visiting_team_id=15,
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(NhlHistoricalGame, 2026020001)
        assert retrieved is not None
        assert retrieved.game_id == 2026020001
        assert retrieved.eastern_start_time == "07:30 PM"
        assert retrieved.game_date == "2026-01-10"
        assert retrieved.game_number == 1
        assert retrieved.game_schedule_state_id == 1
        assert retrieved.game_state_id == 4
        assert retrieved.game_type == 2
        assert retrieved.home_score == 3
        assert retrieved.home_team_id == 10
        assert retrieved.period == 3
        assert retrieved.season == 20252026
        assert retrieved.visiting_score == 2
        assert retrieved.visiting_team_id == 15

    def test_nhl_historical_game_game_id_is_integer_pk(self, db):
        """game_id is the integer primary key (not auto-generated)."""
        row = NhlHistoricalGame(game_id=9999, season=20252026)
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(NhlHistoricalGame, 9999)
        assert retrieved is not None
        assert retrieved.game_id == 9999

    def test_nhl_historical_game_nullable_fields_allowed(self, db):
        """All non-PK columns are nullable — a minimal row (only game_id) is valid."""
        row = NhlHistoricalGame(game_id=1)
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(NhlHistoricalGame, 1)
        assert retrieved is not None
        assert retrieved.eastern_start_time is None
        assert retrieved.season is None

    def test_nhl_historical_game_upsert_idempotent(self, db):
        """Merging the same game_id twice leaves exactly one row."""
        db.session.add(NhlHistoricalGame(game_id=1, season=20252026))
        db.session.commit()

        db.session.merge(NhlHistoricalGame(game_id=1, season=20252026))
        db.session.commit()

        rows = db.session.scalars(
            select(NhlHistoricalGame).where(NhlHistoricalGame.game_id == 1)
        ).all()
        assert len(rows) == 1

    def test_nhl_historical_game_upsert_overwrites_changed_field(self, db):
        """Merging with a changed home_score overwrites the existing value."""
        db.session.add(NhlHistoricalGame(game_id=1, home_score=2))
        db.session.commit()

        db.session.merge(NhlHistoricalGame(game_id=1, home_score=5))
        db.session.commit()

        row = db.session.get(NhlHistoricalGame, 1)
        assert row.home_score == 5


# ── ingest_historical_games ───────────────────────────────────────────────────

class TestIngestHistoricalGames:
    def test_ingest_historical_games_inserts_rows(self, db):
        """ingest_historical_games() inserts one row per game returned by the API."""
        with patch("nhl_client.get_all_games", return_value=[_GAME_1, _GAME_2]):
            from services.historical import ingest_historical_games
            count = ingest_historical_games()

        assert count == 2
        rows = db.session.scalars(select(NhlHistoricalGame)).all()
        assert len(rows) == 2

    def test_ingest_historical_games_maps_fields_correctly(self, db):
        """ingest_historical_games() maps every API field to the correct DB column."""
        with patch("nhl_client.get_all_games", return_value=[_GAME_1]):
            from services.historical import ingest_historical_games
            ingest_historical_games()

        row = db.session.get(NhlHistoricalGame, 2026020001)
        assert row is not None
        assert row.eastern_start_time == "07:30 PM"
        assert row.game_date == "2026-01-10"
        assert row.game_number == 1
        assert row.game_schedule_state_id == 1
        assert row.game_state_id == 4
        assert row.game_type == 2
        assert row.home_score == 3
        assert row.home_team_id == 10
        assert row.period == 3
        assert row.season == 20252026
        assert row.visiting_score == 2
        assert row.visiting_team_id == 15

    def test_ingest_historical_games_idempotent(self, db):
        """Running ingest_historical_games() twice results in no duplicate rows."""
        with patch("nhl_client.get_all_games", return_value=[_GAME_1, _GAME_2]):
            from services.historical import ingest_historical_games
            ingest_historical_games()
            ingest_historical_games()

        rows = db.session.scalars(select(NhlHistoricalGame)).all()
        assert len(rows) == 2

    def test_ingest_historical_games_empty_response(self, db):
        """ingest_historical_games() with an empty API response raises no error."""
        with patch("nhl_client.get_all_games", return_value=[]):
            from services.historical import ingest_historical_games
            count = ingest_historical_games()

        assert count == 0
        rows = db.session.scalars(select(NhlHistoricalGame)).all()
        assert rows == []

    def test_ingest_historical_games_returns_count(self, db):
        """ingest_historical_games() returns the number of rows processed."""
        with patch("nhl_client.get_all_games", return_value=[_GAME_1]):
            from services.historical import ingest_historical_games
            count = ingest_historical_games()

        assert count == 1

    def test_ingest_historical_games_updates_existing_row(self, db):
        """ingest_historical_games() overwrites a changed field on a repeated run."""
        with patch("nhl_client.get_all_games", return_value=[_GAME_1]):
            from services.historical import ingest_historical_games
            ingest_historical_games()

        updated = dict(_GAME_1, homeScore=99)
        with patch("nhl_client.get_all_games", return_value=[updated]):
            ingest_historical_games()

        row = db.session.get(NhlHistoricalGame, 2026020001)
        assert row.home_score == 99
        all_rows = db.session.scalars(select(NhlHistoricalGame)).all()
        assert len(all_rows) == 1


# ── refresh_recent_historical_games ──────────────────────────────────────────

class TestRefreshRecentHistoricalGames:
    def test_refresh_recent_returns_count_of_recent_games_only(self, db):
        """refresh_recent_historical_games() returns count of games within the 30-day window."""
        with patch("nhl_client.get_all_games", return_value=[_RECENT_GAME, _OLD_GAME]):
            from services.historical import refresh_recent_historical_games
            count = refresh_recent_historical_games()

        assert count == 1  # only the recent game qualifies

    def test_refresh_recent_inserts_new_game_within_window(self, db):
        """refresh_recent_historical_games() inserts a game whose date is within 30 days."""
        with patch("nhl_client.get_all_games", return_value=[_RECENT_GAME]):
            from services.historical import refresh_recent_historical_games
            refresh_recent_historical_games()

        row = db.session.get(NhlHistoricalGame, _RECENT_GAME["id"])
        assert row is not None
        assert row.game_date == _RECENT_DATE
        assert row.home_score == 3

    def test_refresh_recent_updates_changed_field_within_window(self, db):
        """refresh_recent_historical_games() updates a changed field for a game in the window."""
        db.session.add(NhlHistoricalGame(
            game_id=_RECENT_GAME["id"],
            game_date=_RECENT_DATE,
            home_score=0,
        ))
        db.session.commit()

        with patch("nhl_client.get_all_games", return_value=[_RECENT_GAME]):
            from services.historical import refresh_recent_historical_games
            refresh_recent_historical_games()

        row = db.session.get(NhlHistoricalGame, _RECENT_GAME["id"])
        assert row.home_score == 3

    def test_refresh_recent_does_not_touch_game_outside_window(self, db):
        """refresh_recent_historical_games() leaves a game outside 30 days unchanged."""
        db.session.add(NhlHistoricalGame(
            game_id=_OLD_GAME["id"],
            game_date=_OLD_DATE,
            home_score=2,
        ))
        db.session.commit()

        # API returns old game with a changed home_score
        changed_old = dict(_OLD_GAME, homeScore=99)
        with patch("nhl_client.get_all_games", return_value=[changed_old]):
            from services.historical import refresh_recent_historical_games
            refresh_recent_historical_games()

        row = db.session.get(NhlHistoricalGame, _OLD_GAME["id"])
        assert row.home_score == 2  # untouched

    def test_refresh_recent_idempotent_no_duplicates(self, db):
        """Running refresh_recent_historical_games() twice produces exactly one row per game."""
        with patch("nhl_client.get_all_games", return_value=[_RECENT_GAME]):
            from services.historical import refresh_recent_historical_games
            refresh_recent_historical_games()
            refresh_recent_historical_games()

        rows = db.session.scalars(
            select(NhlHistoricalGame).where(
                NhlHistoricalGame.game_id == _RECENT_GAME["id"]
            )
        ).all()
        assert len(rows) == 1

    def test_refresh_recent_empty_api_response_returns_zero(self, db):
        """refresh_recent_historical_games() with an empty API response returns 0."""
        with patch("nhl_client.get_all_games", return_value=[]):
            from services.historical import refresh_recent_historical_games
            count = refresh_recent_historical_games()

        assert count == 0

    def test_refresh_recent_unchanged_row_retains_original_value(self, db):
        """refresh_recent_historical_games() leaves a row untouched when API data matches DB."""
        db.session.add(NhlHistoricalGame(
            game_id=_RECENT_GAME["id"],
            game_date=_RECENT_DATE,
            home_score=3,
            season=20252026,
        ))
        db.session.commit()

        with patch("nhl_client.get_all_games", return_value=[_RECENT_GAME]):
            from services.historical import refresh_recent_historical_games
            refresh_recent_historical_games()

        row = db.session.get(NhlHistoricalGame, _RECENT_GAME["id"])
        assert row.home_score == 3
        assert row.season == 20252026


# ── backfill-historical CLI command ──────────────────────────────────────────

class TestBackfillHistoricalCommand:
    def test_backfill_historical_command_inserts_rows_when_table_empty(self, app, db):
        """backfill-historical CLI command populates nhl_historical_game from an empty table."""
        assert db.session.scalars(select(NhlHistoricalGame)).all() == []

        with patch("nhl_client.get_all_games", return_value=[_GAME_1, _GAME_2]):
            result = app.test_cli_runner().invoke(args=["backfill-historical"])

        assert result.exit_code == 0
        rows = db.session.scalars(select(NhlHistoricalGame)).all()
        assert len(rows) == 2

    def test_backfill_historical_command_idempotent_no_duplicates(self, app, db):
        """Running backfill-historical twice leaves exactly one row per game."""
        runner = app.test_cli_runner()

        with patch("nhl_client.get_all_games", return_value=[_GAME_1]):
            runner.invoke(args=["backfill-historical"])
            runner.invoke(args=["backfill-historical"])

        rows = db.session.scalars(select(NhlHistoricalGame)).all()
        assert len(rows) == 1

    def test_backfill_historical_command_echoes_count(self, app, db):
        """backfill-historical prints the number of rows backfilled to stdout."""
        with patch("nhl_client.get_all_games", return_value=[_GAME_1, _GAME_2]):
            result = app.test_cli_runner().invoke(args=["backfill-historical"])

        assert "2" in result.output
