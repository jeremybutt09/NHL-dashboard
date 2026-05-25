"""Tests for NhlHistoricalGame model and ingest_historical_games() (Issue #121)."""
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import NhlHistoricalGame


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
