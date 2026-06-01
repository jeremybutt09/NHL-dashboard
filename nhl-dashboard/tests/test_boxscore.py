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


# ── prune_stale_boxscores (Issue #155) ───────────────────────────────────────

_STALE_ID = 2025030316  # ECF Game 6 — series ended before this game was played


class TestPruneStaleBoxscores:
    """Tests for prune_stale_boxscores() — Issue #155."""

    def _api(self, today, game_ids):
        """Build a minimal schedule API response for today with the given game IDs."""
        return {
            "gameWeek": [
                {"date": today, "games": [{"id": gid} for gid in game_ids]}
            ]
        }

    def test_prune_stale_boxscores_removes_game_not_in_api(self, db, boxscore_factory):
        """A FUT boxscore row absent from the API response is deleted."""
        today = _TODAY
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")

        with patch("nhl_client.get_schedule_now", return_value=self._api(today, [])):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 1
        assert db.session.get(Boxscore, _STALE_ID) is None

    def test_prune_stale_boxscores_keeps_game_present_in_api(self, db, boxscore_factory):
        """A boxscore row whose game_id appears in the API response is kept."""
        today = _TODAY
        boxscore_factory("TOR", "BOS", game_id=_GAME_ID, game_date=today, game_state="FUT")

        with patch("nhl_client.get_schedule_now", return_value=self._api(today, [_GAME_ID])):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 0
        assert db.session.get(Boxscore, _GAME_ID) is not None

    def test_prune_stale_boxscores_removes_only_absent_game(self, db, boxscore_factory):
        """When API returns game A but not C, only C is deleted; A is kept."""
        today = _TODAY
        boxscore_factory("TOR", "BOS", game_id=_GAME_ID, game_date=today, game_state="LIVE")
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")

        with patch("nhl_client.get_schedule_now", return_value=self._api(today, [_GAME_ID])):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 1
        assert db.session.get(Boxscore, _GAME_ID) is not None
        assert db.session.get(Boxscore, _STALE_ID) is None

    def test_prune_stale_boxscores_only_affects_target_date(self, db, boxscore_factory):
        """Boxscore rows for other dates are never touched."""
        today = _TODAY
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")
        boxscore_factory("TOR", "BOS", game_id=_GAME_ID, game_date="2020-01-01", game_state="FINAL")

        with patch("nhl_client.get_schedule_now", return_value=self._api(today, [])):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 1
        assert db.session.get(Boxscore, _STALE_ID) is None
        assert db.session.get(Boxscore, _GAME_ID) is not None  # historical row untouched

    def test_prune_stale_boxscores_skips_when_date_not_in_api_response(self, db, boxscore_factory):
        """When the API response has no block for today, no rows are deleted."""
        today = _TODAY
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")

        no_today_response = {"gameWeek": [{"date": "2020-01-01", "games": []}]}

        with patch("nhl_client.get_schedule_now", return_value=no_today_response):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 0
        assert db.session.get(Boxscore, _STALE_ID) is not None  # untouched

    def test_prune_stale_boxscores_tolerates_api_error(self, db, boxscore_factory):
        """API failure returns 0 and leaves all rows intact."""
        today = _TODAY
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")

        with patch("nhl_client.get_schedule_now", side_effect=RuntimeError("API down")):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 0
        assert db.session.get(Boxscore, _STALE_ID) is not None  # untouched

    def test_prune_stale_boxscores_returns_zero_when_nothing_to_prune(self, db):
        """Returns 0 when no boxscore rows exist for today."""
        today = _TODAY

        with patch("nhl_client.get_schedule_now", return_value=self._api(today, [])):
            from services.boxscore import prune_stale_boxscores
            count = prune_stale_boxscores()

        assert count == 0

    def test_refresh_boxscores_then_prune_removes_stale_game(self, db, boxscore_factory):
        """After refresh_boxscores + prune_stale_boxscores (the scheduler pair), stale rows are gone."""
        today = _TODAY
        # Stale game: in boxscore table but absent from the NHL schedule API
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")
        # Valid game: seeded in game table so refresh_boxscores has something to fetch
        db.session.add(Game(game_id=_GAME_ID, game_date=today))
        db.session.commit()

        schedule_response = {
            "gameWeek": [{"date": today, "games": [{"id": _GAME_ID}]}]
        }

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        with patch("nhl_client.get_schedule_now", return_value=schedule_response):
            from services.boxscore import prune_stale_boxscores
            prune_stale_boxscores()

        assert db.session.get(Boxscore, _GAME_ID) is not None
        assert db.session.get(Boxscore, _STALE_ID) is None

    def test_get_games_today_excludes_stale_game_after_prune(self, db, boxscore_factory):
        """build_today_response excludes a stale boxscore row after pruning runs."""
        today = _TODAY
        boxscore_factory("CAR", "MTL", game_id=_STALE_ID, game_date=today, game_state="FUT")

        with patch("nhl_client.get_schedule_now", return_value=self._api(today, [])):
            from services.boxscore import prune_stale_boxscores
            from services.slate import build_today_response
            prune_stale_boxscores()
            response = build_today_response()

        assert response["games"] == []


# ── Issue #156: team name population at write time and backfill ──────────────

class TestBuildBoxscoreTeamNameFallback:
    """_build_boxscore() team_lookup parameter — Issue #156."""

    def test_build_boxscore_uses_team_lookup_for_empty_api_name(self):
        """_build_boxscore() fills empty team name from team_lookup dict."""
        from datetime import datetime, timezone
        from services.boxscore import _build_boxscore

        raw = dict(_BOXSCORE_API)
        raw["awayTeam"] = dict(raw["awayTeam"], name={})
        raw["homeTeam"] = dict(raw["homeTeam"], name={})

        lookup = {"TOR": "Toronto Maple Leafs", "BOS": "Boston Bruins"}
        now = datetime.now(timezone.utc)
        bs = _build_boxscore(raw, now, team_lookup=lookup)

        assert bs.away_name == "Toronto Maple Leafs"
        assert bs.home_name == "Boston Bruins"

    def test_build_boxscore_prefers_api_name_over_lookup(self):
        """_build_boxscore() keeps API name when it is non-empty."""
        from datetime import datetime, timezone
        from services.boxscore import _build_boxscore

        lookup = {"TOR": "Override — Should Not Appear", "BOS": "Override — Should Not Appear"}
        now = datetime.now(timezone.utc)
        bs = _build_boxscore(_BOXSCORE_API, now, team_lookup=lookup)

        assert bs.away_name == "Toronto Maple Leafs"
        assert bs.home_name == "Boston Bruins"

    def test_build_boxscore_no_lookup_leaves_empty_name_unchanged(self):
        """_build_boxscore() with no lookup and empty API name stores empty string."""
        from datetime import datetime, timezone
        from services.boxscore import _build_boxscore

        raw = dict(_BOXSCORE_API)
        raw["awayTeam"] = dict(raw["awayTeam"], name={})
        now = datetime.now(timezone.utc)
        bs = _build_boxscore(raw, now)

        assert bs.away_name == ""


class TestBackfillTeamNames:
    """Tests for backfill_team_names() — Issue #156."""

    def _make_bs(self, db, game_id, away_abbrev, home_abbrev, away_name="", home_name=""):
        """Create a Boxscore row with explicit (possibly empty) team names."""
        row = Boxscore(
            game_id=game_id,
            away_abbrev=away_abbrev,
            home_abbrev=home_abbrev,
            away_name=away_name,
            home_name=home_name,
        )
        db.session.add(row)
        db.session.commit()
        return row

    def test_backfill_team_names_fills_empty_away_name(self, db, team_factory):
        """backfill_team_names() fills empty away_name from team.full_name."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        row = self._make_bs(db, 9001, "TOR", "BOS", away_name="", home_name="Boston Bruins")

        from services.boxscore import backfill_team_names
        count = backfill_team_names()

        db.session.refresh(row)
        assert row.away_name == "Toronto Maple Leafs"
        assert count >= 1

    def test_backfill_team_names_fills_empty_home_name(self, db, team_factory):
        """backfill_team_names() fills empty home_name from team.full_name."""
        team_factory("BOS", "Bruins", full_name="Boston Bruins")
        row = self._make_bs(db, 9002, "TOR", "BOS",
                            away_name="Toronto Maple Leafs", home_name="")

        from services.boxscore import backfill_team_names
        count = backfill_team_names()

        db.session.refresh(row)
        assert row.home_name == "Boston Bruins"
        assert count >= 1

    def test_backfill_team_names_fills_null_away_name(self, db, team_factory):
        """backfill_team_names() fills NULL away_name from team.full_name."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        row = Boxscore(game_id=9003, away_abbrev="TOR", home_abbrev="BOS",
                       away_name=None, home_name="Boston Bruins")
        db.session.add(row)
        db.session.commit()

        from services.boxscore import backfill_team_names
        backfill_team_names()

        db.session.refresh(row)
        assert row.away_name == "Toronto Maple Leafs"

    def test_backfill_team_names_skips_already_populated_rows(self, db, team_factory):
        """backfill_team_names() returns 0 when all names are already populated."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        team_factory("BOS", "Bruins", full_name="Boston Bruins")
        self._make_bs(db, 9004, "TOR", "BOS",
                      away_name="Toronto Maple Leafs", home_name="Boston Bruins")

        from services.boxscore import backfill_team_names
        count = backfill_team_names()

        assert count == 0

    def test_backfill_team_names_falls_back_to_name_when_full_name_null(self, db, team_factory):
        """backfill_team_names() uses team.name when full_name is NULL."""
        team_factory("TOR", "Maple Leafs", full_name=None)
        row = self._make_bs(db, 9005, "TOR", "BOS",
                            away_name="", home_name="Boston Bruins")

        from services.boxscore import backfill_team_names
        backfill_team_names()

        db.session.refresh(row)
        assert row.away_name == "Maple Leafs"

    def test_backfill_team_names_idempotent(self, db, team_factory):
        """Running backfill_team_names() twice yields the same result; second run returns 0."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        row = self._make_bs(db, 9006, "TOR", "BOS",
                            away_name="", home_name="Boston Bruins")

        from services.boxscore import backfill_team_names
        backfill_team_names()
        count2 = backfill_team_names()

        db.session.refresh(row)
        assert row.away_name == "Toronto Maple Leafs"
        assert count2 == 0

    def test_backfill_team_names_returns_count_of_rows_updated(self, db, team_factory):
        """backfill_team_names() returns the number of boxscore rows updated."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        team_factory("BOS", "Bruins", full_name="Boston Bruins")
        # Row 1: both names empty
        self._make_bs(db, 9007, "TOR", "BOS", away_name="", home_name="")
        # Row 2: only away empty
        self._make_bs(db, 9008, "TOR", "BOS",
                      away_name="", home_name="Boston Bruins")

        from services.boxscore import backfill_team_names
        count = backfill_team_names()

        assert count == 2

    def test_backfill_team_names_skips_unknown_abbrev(self, db):
        """backfill_team_names() leaves name empty when no team row exists for the abbrev."""
        row = Boxscore(game_id=9009, away_abbrev="XYZ", home_abbrev="ZZZ",
                       away_name="", home_name="")
        db.session.add(row)
        db.session.commit()

        from services.boxscore import backfill_team_names
        backfill_team_names()

        db.session.refresh(row)
        assert row.away_name == ""
        assert row.home_name == ""


class TestRefreshBoxscoresTeamNamePopulation:
    """refresh_boxscores() fills team names from the team table when API returns empty — Issue #156."""

    def test_refresh_boxscores_populates_name_from_team_table(self, db, team_factory):
        """refresh_boxscores() uses team lookup to fill empty API team name."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        team_factory("BOS", "Bruins", full_name="Boston Bruins")
        db.session.add(Game(game_id=_GAME_ID, game_date=_TODAY))
        db.session.commit()

        raw = dict(_BOXSCORE_API)
        raw["awayTeam"] = dict(raw["awayTeam"], name={"default": ""})
        raw["homeTeam"] = dict(raw["homeTeam"], name={"default": ""})

        with patch("nhl_client.get_boxscore", return_value=raw):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, _GAME_ID)
        assert row.away_name == "Toronto Maple Leafs"
        assert row.home_name == "Boston Bruins"


class TestBackfillBoxscoreNamesCommand:
    """Tests for the backfill-boxscore-names CLI command — Issue #156."""

    def test_backfill_boxscore_names_command_updates_rows(self, app, db, team_factory):
        """backfill-boxscore-names CLI command populates empty team names."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        row = Boxscore(game_id=_GAME_ID, away_abbrev="TOR", home_abbrev="BOS",
                       away_name="", home_name="Boston Bruins")
        db.session.add(row)
        db.session.commit()

        result = app.test_cli_runner().invoke(args=["backfill-boxscore-names"])

        assert result.exit_code == 0
        db.session.refresh(row)
        assert row.away_name == "Toronto Maple Leafs"

    def test_backfill_boxscore_names_command_echoes_count(self, app, db, team_factory):
        """backfill-boxscore-names CLI command prints the number of rows updated."""
        team_factory("TOR", "Maple Leafs", full_name="Toronto Maple Leafs")
        row = Boxscore(game_id=_GAME_ID, away_abbrev="TOR", home_abbrev="BOS",
                       away_name="", home_name="Boston Bruins")
        db.session.add(row)
        db.session.commit()

        result = app.test_cli_runner().invoke(args=["backfill-boxscore-names"])

        assert "1" in result.output


# ── parallel backfill_boxscores by month partition (Issue #157) ───────────────

class TestBackfillBoxscoresParallel:
    """Month-partitioned parallel backfill_boxscores (Issue #157).

    Acceptance criteria:
      - max_workers=1 processes all month partitions sequentially.
      - max_workers>1 fans out partitions concurrently and upserts all rows.
      - An API failure for one game does not abort other month partitions.
    """

    def _seed_games(self, db, game_date_pairs):
        """Seed (game_id, game_date) pairs into the game table."""
        for game_id, game_date in game_date_pairs:
            db.session.add(Game(game_id=game_id, game_date=game_date))
        db.session.commit()

    def test_backfill_boxscores_single_worker_processes_all_partitions(self, db):
        """max_workers=1 processes all month partitions and upserts every row."""
        self._seed_games(db, [
            (5001, "2026-01-15"),
            (5002, "2026-01-25"),
            (5003, "2026-02-10"),
        ])

        def fake_boxscore(gid):
            return dict(_BOXSCORE_API, id=gid)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores(max_workers=1)

        assert count == 3
        for gid in [5001, 5002, 5003]:
            assert db.session.get(Boxscore, gid) is not None

    def test_backfill_boxscores_multi_worker_upserts_all_months(self, db):
        """max_workers=2 fans out month partitions concurrently and upserts all games."""
        self._seed_games(db, [
            (5011, "2026-01-10"),
            (5012, "2026-01-20"),
            (5013, "2026-02-15"),
        ])

        def fake_boxscore(gid):
            return dict(_BOXSCORE_API, id=gid)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores(max_workers=2)

        assert count == 3
        for gid in [5011, 5012, 5013]:
            assert db.session.get(Boxscore, gid) is not None

    def test_backfill_boxscores_failure_isolation_between_partitions(self, db):
        """API failure in one month's game does not abort the other month's partition."""
        self._seed_games(db, [
            (5021, "2026-01-10"),  # Jan — API will raise
            (5022, "2026-02-10"),  # Feb — will succeed
        ])

        def side_effect(gid):
            if gid == 5021:
                raise RuntimeError("timeout")
            return dict(_BOXSCORE_API, id=gid)

        with patch("nhl_client.get_boxscore", side_effect=side_effect), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores(max_workers=2)

        assert count == 1
        assert db.session.get(Boxscore, 5021) is None
        assert db.session.get(Boxscore, 5022) is not None


class TestBackfillBoxscoresCommandMaxWorkers:
    """Tests for --max-workers CLI option (Issue #157)."""

    def test_backfill_boxscores_command_accepts_max_workers_option(self, app, db):
        """backfill-boxscores --max-workers 1 exits cleanly and echoes count."""
        db.session.add(Game(game_id=_GAME_ID, game_date="2026-01-01"))
        db.session.commit()

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API), \
             patch("time.sleep"):
            result = app.test_cli_runner().invoke(
                args=["backfill-boxscores", "--max-workers", "1"]
            )

        assert result.exit_code == 0
        assert "1" in result.output
        assert db.session.get(Boxscore, _GAME_ID) is not None


# ── Resume-aware backfill: skip already-loaded game IDs (Issue #158) ──────────

class TestBackfillBoxscoresResumeAware:
    """backfill_boxscores() skips game IDs already in the boxscore table (Issue #158).

    Acceptance criteria:
      - All games already loaded → nothing fetched, returns 0
      - No games loaded → all games fetched
      - Partial load → only missing games fetched
      - force=True → all games fetched regardless of existing rows
    """

    def _seed_games(self, db, game_date_pairs):
        """Seed (game_id, game_date) pairs into the game table."""
        for game_id, game_date in game_date_pairs:
            db.session.add(Game(game_id=game_id, game_date=game_date))
        db.session.commit()

    def test_backfill_boxscores_skips_all_when_all_already_loaded(self, db):
        """Returns 0 and never calls the API when all game IDs already have a boxscore row."""
        self._seed_games(db, [(4001, "2026-01-10"), (4002, "2026-01-11")])
        db.session.add(Boxscore(game_id=4001))
        db.session.add(Boxscore(game_id=4002))
        db.session.commit()

        with patch("nhl_client.get_boxscore") as mock_get, \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        mock_get.assert_not_called()
        assert count == 0

    def test_backfill_boxscores_fetches_all_when_no_boxscores_exist(self, db):
        """Fetches all game IDs when the boxscore table is empty."""
        self._seed_games(db, [(4011, "2026-01-10"), (4012, "2026-01-11")])

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        assert count == 2
        assert db.session.get(Boxscore, 4011) is not None
        assert db.session.get(Boxscore, 4012) is not None

    def test_backfill_boxscores_fetches_only_missing_games(self, db):
        """Fetches only game IDs absent from the boxscore table, skips existing ones."""
        self._seed_games(db, [
            (4021, "2026-01-10"),  # already loaded
            (4022, "2026-01-11"),  # missing — must be fetched
        ])
        db.session.add(Boxscore(game_id=4021))
        db.session.commit()

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore) as mock_get, \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores()

        # Only the missing game should be fetched
        fetched_ids = [call.args[0] for call in mock_get.call_args_list]
        assert 4021 not in fetched_ids
        assert 4022 in fetched_ids
        assert count == 1
        assert db.session.get(Boxscore, 4022) is not None

    def test_backfill_boxscores_force_fetches_all_despite_existing_rows(self, db):
        """force=True bypasses skip logic and fetches all game IDs."""
        self._seed_games(db, [(4031, "2026-01-10"), (4032, "2026-01-11")])
        db.session.add(Boxscore(game_id=4031))
        db.session.commit()

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with patch("nhl_client.get_boxscore", side_effect=fake_boxscore) as mock_get, \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            count = backfill_boxscores(force=True)

        fetched_ids = [call.args[0] for call in mock_get.call_args_list]
        assert 4031 in fetched_ids
        assert 4032 in fetched_ids
        assert count == 2

    def test_backfill_boxscores_logs_skipped_count(self, db, caplog):
        """Skipped game count is logged at INFO level."""
        import logging
        self._seed_games(db, [(4041, "2026-01-10"), (4042, "2026-01-11")])
        db.session.add(Boxscore(game_id=4041))
        db.session.commit()

        def fake_boxscore(game_id):
            return dict(_BOXSCORE_API, id=game_id)

        with caplog.at_level(logging.INFO, logger="services.boxscore"), \
             patch("nhl_client.get_boxscore", side_effect=fake_boxscore), \
             patch("time.sleep"):
            from services.boxscore import backfill_boxscores
            backfill_boxscores()

        assert any("skip" in rec.message.lower() or "1" in rec.message for rec in caplog.records)


class TestBackfillBoxscoresCommandForce:
    """Tests for --force CLI flag (Issue #158)."""

    def test_backfill_boxscores_command_force_flag_fetches_all(self, app, db):
        """backfill-boxscores --force re-fetches already-loaded game IDs."""
        db.session.add(Game(game_id=_GAME_ID, game_date="2026-01-01"))
        db.session.add(Boxscore(game_id=_GAME_ID))
        db.session.commit()

        with patch("nhl_client.get_boxscore", return_value=_BOXSCORE_API) as mock_get, \
             patch("time.sleep"):
            result = app.test_cli_runner().invoke(
                args=["backfill-boxscores", "--force"]
            )

        assert result.exit_code == 0
        mock_get.assert_called_once_with(_GAME_ID)

    def test_backfill_boxscores_command_no_force_skips_loaded_games(self, app, db):
        """backfill-boxscores without --force skips already-loaded game IDs."""
        db.session.add(Game(game_id=_GAME_ID, game_date="2026-01-01"))
        db.session.add(Boxscore(game_id=_GAME_ID))
        db.session.commit()

        with patch("nhl_client.get_boxscore") as mock_get, \
             patch("time.sleep"):
            result = app.test_cli_runner().invoke(args=["backfill-boxscores"])

        assert result.exit_code == 0
        mock_get.assert_not_called()
