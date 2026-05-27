"""Tests for time_utils: now_et(), today_et(), and migrate_timestamps_to_et() (Issues #136, #150).

Acceptance criteria:
  - now_et() returns a tz-naive datetime representing Eastern Time.
  - today_et() returns the current calendar date in ET as a YYYY-MM-DD string.
  - All freshness timestamp columns (fetched_at, updated_at, computed_at) are written
    as ET tz-naive values at the service write layer.
  - migrate_timestamps_to_et() shifts existing UTC-naive rows to ET equivalents.
"""
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

_EASTERN = ZoneInfo("America/New_York")


# ── now_et() ──────────────────────────────────────────────────────────────────

class TestNowEt:
    def test_now_et_returns_naive_datetime(self):
        """now_et() returns a tz-naive datetime (SQLite-compatible)."""
        from services.time_utils import now_et
        result = now_et()
        assert isinstance(result, datetime)
        assert result.tzinfo is None

    def test_now_et_is_close_to_eastern_time(self):
        """now_et() value is within 2 seconds of datetime.now(Eastern)."""
        from services.time_utils import now_et
        expected = datetime.now(_EASTERN).replace(tzinfo=None)
        result = now_et()
        delta = abs((result - expected).total_seconds())
        assert delta < 2.0

    def test_now_et_differs_from_utc_by_et_offset(self):
        """now_et() is 4–5 hours behind UTC (EDT=UTC-4, EST=UTC-5)."""
        from services.time_utils import now_et
        utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        et_naive = now_et()
        delta_hours = (utc_naive - et_naive).total_seconds() / 3600
        assert 3.5 <= delta_hours <= 5.5, (
            f"Expected 4–5h behind UTC, got {delta_hours:.2f}h"
        )


# ── migrate_timestamps_to_et() ────────────────────────────────────────────────

class TestMigrateTimestampsToEt:
    def test_migrate_converts_fetched_at_in_nhl_odds_line(self, db):
        """NhlOddsLine.fetched_at UTC-naive value is shifted to ET after migration."""
        from models import LiveGame, NhlOddsLine, NhlOddsPartner
        from services.time_utils import migrate_timestamps_to_et

        db.session.add(NhlOddsPartner(partner_id=7, name="Partner7"))
        db.session.add(LiveGame(
            game_id=2026030001,
            start_est=datetime(2026, 5, 25, 23, 0),
            status="scheduled",
        ))
        # Stored as UTC naive (old convention): 15:00 UTC = 11:00 EDT
        db.session.add(NhlOddsLine(
            game_id=2026030001, partner_id=7,
            fetched_at=datetime(2026, 5, 25, 15, 0, 0),
            away_value="-152", home_value="+126",
        ))
        db.session.commit()

        result = migrate_timestamps_to_et()

        row = db.session.scalars(select(NhlOddsLine)).first()
        assert row.fetched_at == datetime(2026, 5, 25, 11, 0, 0)  # UTC-4 (EDT in May)
        assert result["nhl_odds_line"] == 1

    def test_migrate_converts_updated_at_in_live_game(self, db):
        """LiveGame.updated_at UTC-naive value is shifted to ET after migration."""
        from models import LiveGame
        from services.time_utils import migrate_timestamps_to_et

        db.session.add(LiveGame(
            game_id=2026030002,
            start_est=datetime(2026, 5, 25, 23, 0),
            status="scheduled",
            updated_at=datetime(2026, 5, 25, 20, 0, 0),  # 20:00 UTC = 16:00 EDT
        ))
        db.session.commit()

        migrate_timestamps_to_et()

        row = db.session.get(LiveGame, 2026030002)
        assert row.updated_at == datetime(2026, 5, 25, 16, 0, 0)  # UTC-4 (EDT)

    def test_migrate_converts_computed_at_in_model_fair(self, db):
        """ModelFair.computed_at UTC-naive value is shifted to ET after migration."""
        from models import LiveGame, ModelFair
        from services.time_utils import migrate_timestamps_to_et

        db.session.add(LiveGame(
            game_id=2026030003,
            start_est=datetime(2026, 5, 25, 23, 0),
            status="scheduled",
        ))
        db.session.add(ModelFair(
            game_id=2026030003,
            away_fair=45.0, home_fair=55.0,
            computed_at=datetime(2026, 5, 25, 18, 0, 0),  # 18:00 UTC = 14:00 EDT
        ))
        db.session.commit()

        migrate_timestamps_to_et()

        row = db.session.get(ModelFair, 2026030003)
        assert row.computed_at == datetime(2026, 5, 25, 14, 0, 0)  # UTC-4 (EDT)

    def test_migrate_skips_null_timestamps(self, db):
        """Rows with NULL timestamps are not touched and cause no error."""
        from models import LiveGame
        from services.time_utils import migrate_timestamps_to_et

        db.session.add(LiveGame(
            game_id=2026030004,
            start_est=datetime(2026, 5, 25, 23, 0),
            status="scheduled",
            updated_at=None,
        ))
        db.session.commit()

        result = migrate_timestamps_to_et()

        row = db.session.get(LiveGame, 2026030004)
        assert row.updated_at is None
        assert result["live_game"] == 0

    def test_migrate_returns_counts_for_all_tables(self, db):
        """Return dict contains all expected freshness-timestamp table names."""
        from services.time_utils import migrate_timestamps_to_et

        result = migrate_timestamps_to_et()

        expected_tables = {
            "nhl_odds_line", "odds_snapshot", "live_game",
            "model_fair", "boxscore", "dashboard_game",
        }
        assert set(result.keys()) == expected_tables


# ── Service write layer: freshness timestamps are stamped in ET ───────────────

class TestServiceWritesEasternTime:
    def test_refresh_scores_stamps_updated_at_in_et(self, db):
        """refresh_scores() writes LiveGame.updated_at using Eastern Time."""
        from models import LiveGame

        db.session.add(LiveGame(
            game_id=2026030001,
            start_est=datetime(2026, 5, 25, 23, 0),
            status="scheduled",
        ))
        db.session.commit()

        api_data = {
            "currentDate": "2026-05-25",
            "games": [{
                "id": 2026030001,
                "gameState": "FUT",
                "startTimeUTC": "2026-05-25T23:00:00Z",
                "gameDate": "2026-05-25",
                "venue": {"default": "Scotiabank Arena"},
                "awayTeam": {"abbrev": "TOR"},
                "homeTeam": {"abbrev": "BOS"},
            }],
            "oddsPartners": [],
        }
        fixed_et = datetime(2026, 5, 25, 11, 30, 0)

        with patch("nhl_client.get_score_now", return_value=api_data), \
             patch("services.scores.now_et", return_value=fixed_et):
            from services.scores import refresh_scores
            refresh_scores()

        row = db.session.get(LiveGame, 2026030001)
        assert row.updated_at == fixed_et

    def test_refresh_boxscores_stamps_updated_at_in_et(self, db):
        """refresh_boxscores() writes Boxscore.updated_at using Eastern Time."""
        from datetime import date
        from models import Boxscore, Game

        today = date.today().isoformat()
        db.session.add(Game(game_id=2026030001, game_date=today, season=20252026))
        db.session.commit()

        boxscore_api = {
            "id": 2026030001,
            "season": 20252026,
            "gameType": 3,
            "gameDate": today,
            "gameState": "FINAL",
            "venue": {"default": "Scotiabank Arena"},
            "startTimeUTC": f"{today}T23:00:00Z",
            "awayTeam": {
                "id": 10, "name": {"default": "Toronto Maple Leafs"},
                "abbrev": "TOR", "score": 2, "sog": 14,
            },
            "homeTeam": {
                "id": 6, "name": {"default": "Boston Bruins"},
                "abbrev": "BOS", "score": 1, "sog": 18,
            },
            "periodDescriptor": {"number": 3, "periodType": "REG"},
            "clock": {"timeRemaining": "00:00"},
        }
        fixed_et = datetime(2026, 5, 25, 11, 30, 0)

        with patch("nhl_client.get_boxscore", return_value=boxscore_api), \
             patch("services.boxscore.now_et", return_value=fixed_et):
            from services.boxscore import refresh_boxscores
            refresh_boxscores()

        row = db.session.get(Boxscore, 2026030001)
        assert row.updated_at == fixed_et

    def test_refresh_dashboard_games_stamps_updated_at_in_et(self, db):
        """refresh_dashboard_games() writes DashboardGame.updated_at using Eastern Time."""
        from datetime import date
        from models import Boxscore, DashboardGame

        today = date.today().isoformat()
        db.session.add(Boxscore(
            game_id=2026030001,
            game_date=today,
            game_state="FINAL",
            away_name="Toronto Maple Leafs",
            away_abbrev="TOR",
            home_name="Boston Bruins",
            home_abbrev="BOS",
        ))
        db.session.commit()

        fixed_et = datetime(2026, 5, 25, 11, 30, 0)

        with patch("services.dashboard_game.now_et", return_value=fixed_et):
            from services.dashboard_game import refresh_dashboard_games
            refresh_dashboard_games()

        row = db.session.get(DashboardGame, 2026030001)
        assert row.updated_at == fixed_et

    def test_refresh_schedule_stamps_updated_at_in_et(self, db):
        """refresh_schedule() writes LiveGame.updated_at using Eastern Time."""
        import datetime as dt_module

        schedule_data = {
            "gameWeek": [{
                "date": dt_module.date.today().isoformat(),
                "games": [{
                    "id": 2026030001,
                    "startTimeUTC": "2026-05-25T23:00:00Z",
                    "gameState": "FUT",
                    "gameDate": "2026-05-25",
                    "venue": {"default": "Scotiabank Arena"},
                    "awayTeam": {"abbrev": "TOR"},
                    "homeTeam": {"abbrev": "BOS"},
                }],
            }]
        }
        fixed_et = datetime(2026, 5, 25, 11, 30, 0)

        with patch("nhl_client.get_schedule_now", return_value=schedule_data), \
             patch("nhl_client.get_all_teams", return_value=[]), \
             patch("services.slate.now_et", return_value=fixed_et):
            from services.slate import refresh_schedule
            refresh_schedule()

        from models import LiveGame
        row = db.session.get(LiveGame, 2026030001)
        assert row is not None
        assert row.updated_at == fixed_et


# ── today_et() ────────────────────────────────────────────────────────────────

class TestTodayEt:
    def test_today_et_returns_string(self):
        """today_et() returns a string value."""
        from services.time_utils import today_et
        assert isinstance(today_et(), str)

    def test_today_et_returns_iso_date_format(self):
        """today_et() returns a YYYY-MM-DD formatted string."""
        from services.time_utils import today_et
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', today_et())

    def test_today_et_returns_et_calendar_date_not_utc_at_midnight_boundary(self):
        """today_et() returns the ET date even when UTC has rolled to the next day.

        23:30 ET on 2026-05-26 = 03:30 UTC on 2026-05-27.  today_et() must
        return '2026-05-26', not '2026-05-27'.
        """
        from services.time_utils import today_et
        fake_et_now = datetime(2026, 5, 26, 23, 30, 0)  # tz-naive ET: still May 26
        with patch("services.time_utils.now_et", return_value=fake_et_now):
            result = today_et()
        assert result == "2026-05-26"

    def test_today_et_matches_now_et_date(self):
        """today_et() returns the date portion of now_et()."""
        from services.time_utils import today_et, now_et
        expected = now_et().strftime('%Y-%m-%d')
        assert today_et() == expected
