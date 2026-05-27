"""Tests for Boxscore model, refresh_boxscores(), and backfill_boxscores()
service (Issues #133, #135).

Acceptance criteria:
  - boxscore table contains one row per game with game_id, season_id, gameType,
    gameDate, venue, start_time_est (UTC→ET), home/away team names, score, SOG,
    period, and clock.
  - Re-runs upsert existing rows rather than appending duplicates.
  - Background job fetches today's game IDs from the game table.
  - backfill_boxscores() processes ALL game IDs in the game table (not just
    today), is idempotent via upsert, skips individual failures, and returns
    a count of successfully upserted rows.
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
    "gameState": "LIVE",
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

    def test_refresh_boxscores_maps_team_abbrevs(self, db):
        """refresh_boxscores() stores away_abbrev and home_abbrev from the API."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.away_abbrev == "TOR"
        assert row.home_abbrev == "BOS"

    def test_refresh_boxscores_maps_game_state(self, db):
        """refresh_boxscores() stores game_state from the API gameState field."""
        self._seed_game(db)

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.game_state == "LIVE"


class TestBoxscoreModelAbbrevGameState:
    """Tests for the away_abbrev, home_abbrev, and game_state columns (Issue #134)."""

    def test_boxscore_model_stores_abbrev_fields(self, db):
        """Boxscore row persists away_abbrev and home_abbrev."""
        from datetime import datetime, timezone
        row = Boxscore(
            game_id=_GAME_ID,
            away_abbrev="TOR",
            home_abbrev="BOS",
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(Boxscore, _GAME_ID)
        assert retrieved.away_abbrev == "TOR"
        assert retrieved.home_abbrev == "BOS"

    def test_boxscore_model_stores_game_state(self, db):
        """Boxscore row persists game_state."""
        from datetime import datetime, timezone
        row = Boxscore(
            game_id=_GAME_ID,
            game_state="FINAL",
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(Boxscore, _GAME_ID)
        assert retrieved.game_state == "FINAL"


# ── backfill_boxscores ────────────────────────────────────────────────────────

class TestBackfillBoxscores:
    """Tests for backfill_boxscores() — Issue #135."""

    def _seed_games(self, db, game_ids, game_date="2020-01-15"):
        for gid in game_ids:
            db.session.add(Game(game_id=gid, game_date=game_date))
        db.session.commit()

    def test_backfill_boxscores_processes_all_game_table_entries(self, db):
        """backfill_boxscores() fetches a boxscore for every row in the game table."""
        self._seed_games(db, [1001, 1002, 1003])

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 3
        for gid in [1001, 1002, 1003]:
            assert db.session.get(Boxscore, gid) is not None

    def test_backfill_boxscores_includes_non_today_games(self, db):
        """backfill_boxscores() processes historical games (not filtered to today)."""
        self._seed_games(db, [9000002], game_date="2020-01-01")

        with patch("nhl_client.get_boxscore", return_value=dict(_BOXSCORE_API, id=9000002)), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 1
        assert db.session.get(Boxscore, 9000002) is not None

    def test_backfill_boxscores_idempotent_no_duplicates(self, db):
        """Running backfill_boxscores() twice leaves exactly one boxscore per game."""
        self._seed_games(db, [_GAME_ID])

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            backfill_boxscores()
            backfill_boxscores()

        rows = db.session.scalars(
            select(Boxscore).where(Boxscore.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_backfill_boxscores_skips_game_on_api_failure(self, db):
        """backfill_boxscores() continues past an individual API failure."""
        self._seed_games(db, [_GAME_ID, _GAME_ID + 1])

        def side_effect(game_id):
            if game_id == _GAME_ID:
                raise RuntimeError("API timeout")
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=side_effect), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 1
        assert db.session.get(Boxscore, _GAME_ID) is None
        assert db.session.get(Boxscore, _GAME_ID + 1) is not None

    def test_backfill_boxscores_returns_count(self, db):
        """backfill_boxscores() returns the number of successfully upserted rows."""
        self._seed_games(db, [_GAME_ID])

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 1

    def test_backfill_boxscores_empty_game_table_returns_zero(self, db):
        """backfill_boxscores() returns 0 and never calls the API when game table is empty."""
        with patch("nhl_client.get_boxscore") as mock_get, \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        mock_get.assert_not_called()
        assert count == 0

    def test_backfill_boxscores_maps_fields_correctly(self, db):
        """backfill_boxscores() maps every API field to the correct DB column."""
        self._seed_games(db, [_GAME_ID], game_date="2026-01-10")

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            backfill_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.season_id == 20252026
        assert row.game_type == 3
        assert row.venue == "Scotiabank Arena"
        assert row.away_name == "Toronto Maple Leafs"
        assert row.home_name == "Boston Bruins"
        assert row.away_score == 2
        assert row.home_score == 1
        assert row.away_sog == 14
        assert row.home_sog == 18

    def test_backfill_boxscores_season_filter_skips_other_seasons(self, db):
        """backfill_boxscores(season=N) skips games whose season column differs."""
        db.session.add(Game(game_id=2001, game_date="2026-01-01", season=20252026))
        db.session.add(Game(game_id=2002, game_date="2025-01-01", season=20242025))
        db.session.commit()

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores(season=20252026)

        assert count == 1
        assert db.session.get(Boxscore, 2001) is not None
        assert db.session.get(Boxscore, 2002) is None

    def test_backfill_boxscores_skips_empty_dict_response(self, db):
        """backfill_boxscores() skips a game when get_boxscore returns {}."""
        db.session.add(Game(game_id=_GAME_ID, game_date="2025-01-01", season=20242025))
        db.session.add(Game(game_id=_GAME_ID + 1, game_date="2025-01-02", season=20242025))
        db.session.commit()

        def side_effect(game_id):
            if game_id == _GAME_ID:
                return {}
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=side_effect), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 1
        assert db.session.get(Boxscore, _GAME_ID) is None
        assert db.session.get(Boxscore, _GAME_ID + 1) is not None

    def test_backfill_boxscores_empty_response_does_not_abort_run(self, db):
        """backfill_boxscores() continues processing after an empty response."""
        db.session.add(Game(game_id=3001, game_date="2025-01-01"))
        db.session.add(Game(game_id=3002, game_date="2025-01-02"))
        db.session.add(Game(game_id=3003, game_date="2025-01-03"))
        db.session.commit()

        def side_effect(game_id):
            if game_id == 3002:
                return {}
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=side_effect), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 2
        assert db.session.get(Boxscore, 3001) is not None
        assert db.session.get(Boxscore, 3002) is None
        assert db.session.get(Boxscore, 3003) is not None


# ── backfill-boxscores CLI command ────────────────────────────────────────────

class TestBackfillBoxscoresCommand:
    """Tests for the backfill-boxscores Flask CLI command — Issue #135."""

    def test_backfill_boxscores_command_inserts_rows(self, app, db):
        """backfill-boxscores CLI command upserts boxscores for all games in the table."""
        from models import Game
        db.session.add(Game(game_id=_GAME_ID, game_date="2026-01-01"))
        db.session.commit()

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            result = app.test_cli_runner().invoke(args=["backfill-boxscores"])

        assert result.exit_code == 0
        assert db.session.get(Boxscore, _GAME_ID) is not None

    def test_backfill_boxscores_command_echoes_count(self, app, db):
        """backfill-boxscores CLI command prints the number of boxscores upserted."""
        from models import Game
        db.session.add(Game(game_id=_GAME_ID, game_date="2026-01-01"))
        db.session.commit()

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            result = app.test_cli_runner().invoke(args=["backfill-boxscores"])

        assert "1" in result.output

    def test_backfill_boxscores_command_idempotent(self, app, db):
        """Running backfill-boxscores twice leaves exactly one row per game."""
        from models import Game
        db.session.add(Game(game_id=_GAME_ID, game_date="2026-01-01"))
        db.session.commit()

        runner = app.test_cli_runner()
        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            runner.invoke(args=["backfill-boxscores"])
            runner.invoke(args=["backfill-boxscores"])

        rows = db.session.scalars(
            select(Boxscore).where(Boxscore.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_backfill_boxscores_command_with_season_filter(self, app, db):
        """backfill-boxscores --season N limits processing to that season only."""
        from models import Game
        db.session.add(Game(game_id=2001, game_date="2026-01-01", season=20252026))
        db.session.add(Game(game_id=2002, game_date="2025-01-01", season=20242025))
        db.session.commit()

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            result = app.test_cli_runner().invoke(
                args=["backfill-boxscores", "--season", "20252026"]
            )

        assert result.exit_code == 0
        assert db.session.get(Boxscore, 2001) is not None
        assert db.session.get(Boxscore, 2002) is None


# ── multi-season sequential backfill (Issue #149) ────────────────────────────

class TestBackfillBoxscoresMultiSeason:
    """Tests for sequential multi-season backfill covering 20202021–20232024 (Issue #149)."""

    def test_backfill_boxscores_historical_season_id_stored(self, db):
        """backfill_boxscores stores season_id from the API response for a historical season."""
        db.session.add(Game(game_id=2021010001, game_date="2021-01-13", season=20202021))
        db.session.commit()

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id, season=20202021, gameDate="2021-01-13")

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores(season=20202021)

        assert count == 1
        row = db.session.get(Boxscore, 2021010001)
        assert row is not None
        assert row.season_id == 20202021

    def test_backfill_boxscores_sequential_seasons_no_interference(self, db):
        """Running backfill_boxscores for four seasons in sequence produces rows for all."""
        season_games = [
            (6001, 20202021, "2021-01-14"),
            (6002, 20212022, "2021-10-14"),
            (6003, 20222023, "2022-10-14"),
            (6004, 20232024, "2023-10-14"),
        ]
        for game_id, season, game_date in season_games:
            db.session.add(Game(game_id=game_id, game_date=game_date, season=season))
        db.session.commit()

        season_map = {gid: s for gid, s, _ in season_games}

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id, season=season_map[game_id])

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            counts = [backfill_boxscores(season=s) for _, s, _ in season_games]

        assert counts == [1, 1, 1, 1]
        for game_id, season, _ in season_games:
            row = db.session.get(Boxscore, game_id)
            assert row is not None
            assert row.season_id == season

    def test_backfill_boxscores_command_four_seasons_sequential(self, app, db):
        """flask backfill-boxscores --season for four historical seasons exits cleanly."""
        season_games = [
            (7001, 20202021, "2021-01-14"),
            (7002, 20212022, "2021-10-14"),
            (7003, 20222023, "2022-10-14"),
            (7004, 20232024, "2023-10-14"),
        ]
        for game_id, season, game_date in season_games:
            db.session.add(Game(game_id=game_id, game_date=game_date, season=season))
        db.session.commit()

        season_map = {gid: s for gid, s, _ in season_games}

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id, season=season_map[game_id])

        runner = app.test_cli_runner()
        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            for _, season, _ in season_games:
                result = runner.invoke(args=["backfill-boxscores", "--season", str(season)])
                assert result.exit_code == 0, f"Season {season} exited with {result.exit_code}: {result.output}"

        for game_id, season, _ in season_games:
            row = db.session.get(Boxscore, game_id)
            assert row is not None
            assert row.season_id == season
