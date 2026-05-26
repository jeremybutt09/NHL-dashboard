"""Tests for Boxscore model and refresh_boxscores() service (Issue #133).

Acceptance criteria:
  - boxscore table contains one row per game with game_id, season_id, gameType,
    gameDate, venue, start_time_est (UTC→ET), home/away team names, score, SOG,
    period, and clock.
  - Re-runs upsert existing rows rather than appending duplicates.
  - Background job fetches today's game IDs from the game table.
"""
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import Boxscore, Game


# ── Shared mock data ──────────────────────────────────────────────────────────

_TODAY = date.today().isoformat()
_GAME_ID = 2026030247

_BOXSCORE_API = {
    "id": _GAME_ID,
    "season": 20252026,
    "gameType": 3,
    "gameDate": _TODAY,
    "venue": {"default": "Scotiabank Arena"},
    "startTimeUTC": f"{_TODAY}T23:00:00Z",
    "awayTeam": {
        "id": 10,
        "name": {"default": "Toronto Maple Leafs"},
        "abbrev": "TOR",
        "score": 2,
        "sog": 14,
    },
    "homeTeam": {
        "id": 6,
        "name": {"default": "Boston Bruins"},
        "abbrev": "BOS",
        "score": 1,
        "sog": 18,
    },
    "periodDescriptor": {"number": 2, "periodType": "REG"},
    "clock": {"timeRemaining": "12:34", "inIntermission": False},
}

_BOXSCORE_API_OT = dict(
    _BOXSCORE_API,
    periodDescriptor={"number": 4, "periodType": "OT"},
    clock={"timeRemaining": "03:21"},
)

_GAME_ROW = Game(
    game_id=_GAME_ID,
    game_date=_TODAY,
    season=20252026,
    game_type=3,
)


# ── Boxscore model ────────────────────────────────────────────────────────────

class TestBoxscoreModel:
    def test_boxscore_model_stores_all_columns(self, db):
        """Boxscore row persists all expected columns."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        row = Boxscore(
            game_id=_GAME_ID,
            season_id=20252026,
            game_type=3,
            game_date=_TODAY,
            venue="Scotiabank Arena",
            start_time_est=now,
            away_name="Toronto Maple Leafs",
            home_name="Boston Bruins",
            away_score=2,
            home_score=1,
            away_sog=14,
            home_sog=18,
            period="2nd",
            clock="12:34",
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(Boxscore, _GAME_ID)
        assert retrieved is not None
        assert retrieved.game_id == _GAME_ID
        assert retrieved.season_id == 20252026
        assert retrieved.game_type == 3
        assert retrieved.game_date == _TODAY
        assert retrieved.venue == "Scotiabank Arena"
        assert retrieved.start_time_est is not None
        assert retrieved.away_name == "Toronto Maple Leafs"
        assert retrieved.home_name == "Boston Bruins"
        assert retrieved.away_score == 2
        assert retrieved.home_score == 1
        assert retrieved.away_sog == 14
        assert retrieved.home_sog == 18
        assert retrieved.period == "2nd"
        assert retrieved.clock == "12:34"

    def test_boxscore_game_id_is_integer_pk(self, db):
        """game_id is the integer primary key."""
        row = Boxscore(game_id=9999)
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(Boxscore, 9999)
        assert retrieved is not None
        assert retrieved.game_id == 9999

    def test_boxscore_upsert_idempotent(self, db):
        """Merging the same game_id twice leaves exactly one row."""
        db.session.add(Boxscore(game_id=_GAME_ID, away_score=0))
        db.session.commit()

        db.session.merge(Boxscore(game_id=_GAME_ID, away_score=0))
        db.session.commit()

        rows = db.session.scalars(
            select(Boxscore).where(Boxscore.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_boxscore_upsert_overwrites_changed_field(self, db):
        """Merging with a changed away_score overwrites the existing value."""
        db.session.add(Boxscore(game_id=_GAME_ID, away_score=0))
        db.session.commit()

        db.session.merge(Boxscore(game_id=_GAME_ID, away_score=3))
        db.session.commit()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.away_score == 3


# ── refresh_boxscores ─────────────────────────────────────────────────────────

class TestRefreshBoxscores:
    def _seed_game(self, db, game_id=_GAME_ID, game_date=None):
        """Insert a Game row for today so refresh_boxscores has something to fetch."""
        row = Game(game_id=game_id, game_date=game_date or _TODAY)
        db.session.add(row)
        db.session.commit()

    def test_refresh_boxscores_inserts_row_for_todays_game(self, db):
        """refresh_boxscores() creates a boxscore row for today's game."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row is not None

    def test_refresh_boxscores_maps_fields_correctly(self, db):
        """refresh_boxscores() maps every API field to the correct DB column."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.season_id == 20252026
        assert row.game_type == 3
        assert row.game_date == _TODAY
        assert row.venue == "Scotiabank Arena"
        assert row.away_name == "Toronto Maple Leafs"
        assert row.home_name == "Boston Bruins"
        assert row.away_score == 2
        assert row.home_score == 1
        assert row.away_sog == 14
        assert row.home_sog == 18
        assert row.period == "2nd"
        assert row.clock == "12:34"

    def test_refresh_boxscores_converts_utc_to_eastern(self, db):
        """refresh_boxscores() stores start_time_est converted from UTC to ET."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.start_time_est is not None
        # 23:00 UTC = 19:00 ET (UTC-4 in EDT)
        assert row.start_time_est.hour == 19

    def test_refresh_boxscores_parses_ot_period(self, db):
        """refresh_boxscores() stores 'OT' for overtime periodType."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API_OT):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.period == "OT"

    def test_refresh_boxscores_upserts_not_appends(self, db):
        """Running refresh_boxscores() twice leaves exactly one boxscore row per game."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()
            refresh_boxscores()

        rows = db.session.scalars(
            select(Boxscore).where(Boxscore.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_refresh_boxscores_updates_live_fields_on_rerun(self, db):
        """refresh_boxscores() overwrites changed score on a second run."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        updated = dict(_BOXSCORE_API, awayTeam=dict(_BOXSCORE_API["awayTeam"], score=4))
        with patch("nhl_client.get_boxscore", return_value=updated):
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.away_score == 4
        all_rows = db.session.scalars(select(Boxscore)).all()
        assert len(all_rows) == 1

    def test_refresh_boxscores_skips_game_on_api_failure(self, db):
        """refresh_boxscores() continues when one game's API call fails."""
        self._seed_game(db, game_id=_GAME_ID)
        self._seed_game(db, game_id=_GAME_ID + 1)

        def side_effect(game_id):
            if game_id == _GAME_ID:
                raise RuntimeError("API timeout")
            return dict(_BOXSCORE_API, id=_GAME_ID + 1)

        with patch("nhl_client.get_boxscore", side_effect=side_effect):
            from services.boxscore import refresh_boxscores
            count = refresh_boxscores()

        # Only the successful game is upserted
        assert count == 1
        assert db.session.get(Boxscore, _GAME_ID) is None
        assert db.session.get(Boxscore, _GAME_ID + 1) is not None

    def test_refresh_boxscores_ignores_non_today_games(self, db):
        """refresh_boxscores() only fetches game IDs where game_date == today."""
        # Seed a game for a different date
        db.session.add(Game(game_id=9000001, game_date="2020-01-01"))
        db.session.commit()

        with patch("nhl_client.get_boxscore") as mock_get:
            from services.boxscore import refresh_boxscores
            count = refresh_boxscores()

        mock_get.assert_not_called()
        assert count == 0

    def test_refresh_boxscores_returns_count(self, db):
        """refresh_boxscores() returns the number of boxscores successfully upserted."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            count = refresh_boxscores()

        assert count == 1

    def test_refresh_boxscores_empty_game_table_returns_zero(self, db):
        """refresh_boxscores() returns 0 when no games exist for today."""
        with patch("nhl_client.get_boxscore") as mock_get:
            from services.boxscore import refresh_boxscores
            count = refresh_boxscores()

        mock_get.assert_not_called()
        assert count == 0
