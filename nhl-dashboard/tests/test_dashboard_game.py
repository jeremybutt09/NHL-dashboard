"""Tests for DashboardGame model and refresh_dashboard_games() service (Issue #134).

Acceptance criteria:
  - dashboard_game table contains one row per today's game with all fields
    needed to render the app: team names, abbrevs, score, SOG, period, clock,
    start_time_est, venue, status, and game_id.
  - Only records matching today's game_date are returned.
  - Re-runs upsert existing rows rather than appending duplicates.
  - status is derived from boxscore.game_state: 'live', 'final', or 'scheduled'.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from models import Boxscore, DashboardGame

_TODAY = date.today().isoformat()
_GAME_ID = 2026030247
_START_EST = datetime(2026, 5, 25, 19, 0, tzinfo=timezone.utc)


def _make_boxscore(db, game_id=_GAME_ID, game_date=None, game_state="LIVE"):
    """Insert a fully-populated Boxscore row for use in dashboard_game tests."""
    row = Boxscore(
        game_id=game_id,
        game_date=game_date or _TODAY,
        venue="Scotiabank Arena",
        start_time_est=_START_EST,
        away_name="Toronto Maple Leafs",
        away_abbrev="TOR",
        home_name="Boston Bruins",
        home_abbrev="BOS",
        away_score=2,
        home_score=1,
        away_sog=14,
        home_sog=18,
        period="2nd",
        clock="12:34",
        game_state=game_state,
        updated_at=datetime.now(timezone.utc),
    )
    db.session.add(row)
    db.session.commit()
    return row


# ── DashboardGame model ───────────────────────────────────────────────────────

class TestDashboardGameModel:
    def test_dashboard_game_model_stores_all_columns(self, db):
        """DashboardGame row persists all expected display columns."""
        now = datetime.now(timezone.utc)
        row = DashboardGame(
            game_id=_GAME_ID,
            game_date=_TODAY,
            venue="Scotiabank Arena",
            start_time_est=now,
            away_name="Toronto Maple Leafs",
            away_abbrev="TOR",
            home_name="Boston Bruins",
            home_abbrev="BOS",
            away_score=2,
            home_score=1,
            away_sog=14,
            home_sog=18,
            period="2nd",
            clock="12:34",
            status="live",
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()

        retrieved = db.session.get(DashboardGame, _GAME_ID)
        assert retrieved is not None
        assert retrieved.game_id == _GAME_ID
        assert retrieved.game_date == _TODAY
        assert retrieved.venue == "Scotiabank Arena"
        assert retrieved.start_time_est is not None
        assert retrieved.away_name == "Toronto Maple Leafs"
        assert retrieved.away_abbrev == "TOR"
        assert retrieved.home_name == "Boston Bruins"
        assert retrieved.home_abbrev == "BOS"
        assert retrieved.away_score == 2
        assert retrieved.home_score == 1
        assert retrieved.away_sog == 14
        assert retrieved.home_sog == 18
        assert retrieved.period == "2nd"
        assert retrieved.clock == "12:34"
        assert retrieved.status == "live"

    def test_dashboard_game_game_id_is_pk(self, db):
        """game_id is the integer primary key."""
        db.session.add(DashboardGame(game_id=9999))
        db.session.commit()
        assert db.session.get(DashboardGame, 9999) is not None

    def test_dashboard_game_upsert_idempotent(self, db):
        """Merging the same game_id twice leaves exactly one row."""
        db.session.add(DashboardGame(game_id=_GAME_ID, away_score=0))
        db.session.commit()
        db.session.merge(DashboardGame(game_id=_GAME_ID, away_score=0))
        db.session.commit()

        rows = db.session.scalars(
            select(DashboardGame).where(DashboardGame.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_dashboard_game_upsert_overwrites_changed_field(self, db):
        """Merging with a changed away_score overwrites the existing value."""
        db.session.add(DashboardGame(game_id=_GAME_ID, away_score=0))
        db.session.commit()
        db.session.merge(DashboardGame(game_id=_GAME_ID, away_score=3))
        db.session.commit()

        row = db.session.get(DashboardGame, _GAME_ID)
        assert row.away_score == 3


# ── refresh_dashboard_games ───────────────────────────────────────────────────

class TestRefreshDashboardGames:
    def test_refresh_dashboard_games_creates_row_from_boxscore(self, db):
        """refresh_dashboard_games() creates a DashboardGame row for today's boxscore."""
        _make_boxscore(db)

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID) is not None

    def test_refresh_dashboard_games_maps_fields_from_boxscore(self, db):
        """refresh_dashboard_games() copies all display fields from boxscore."""
        _make_boxscore(db)

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        row = db.session.get(DashboardGame, _GAME_ID)
        assert row.game_date == _TODAY
        assert row.venue == "Scotiabank Arena"
        assert row.away_name == "Toronto Maple Leafs"
        assert row.away_abbrev == "TOR"
        assert row.home_name == "Boston Bruins"
        assert row.home_abbrev == "BOS"
        assert row.away_score == 2
        assert row.home_score == 1
        assert row.away_sog == 14
        assert row.home_sog == 18
        assert row.period == "2nd"
        assert row.clock == "12:34"

    def test_refresh_dashboard_games_maps_start_time_est(self, db):
        """refresh_dashboard_games() copies start_time_est from boxscore."""
        _make_boxscore(db)

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        row = db.session.get(DashboardGame, _GAME_ID)
        # SQLite strips tzinfo on round-trip; compare naive equivalents.
        assert row.start_time_est == _START_EST.replace(tzinfo=None)

    def test_refresh_dashboard_games_derives_status_live(self, db):
        """game_state='LIVE' maps to status='live'."""
        _make_boxscore(db, game_state="LIVE")

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "live"

    def test_refresh_dashboard_games_derives_status_crit_as_live(self, db):
        """game_state='CRIT' (overtime in progress) maps to status='live'."""
        _make_boxscore(db, game_state="CRIT")

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "live"

    def test_refresh_dashboard_games_derives_status_final(self, db):
        """game_state='FINAL' maps to status='final'."""
        _make_boxscore(db, game_state="FINAL")

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "final"

    def test_refresh_dashboard_games_derives_status_off_as_final(self, db):
        """game_state='OFF' (post-game window) maps to status='final'."""
        _make_boxscore(db, game_state="OFF")

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "final"

    def test_refresh_dashboard_games_derives_status_fut_as_scheduled(self, db):
        """game_state='FUT' (future/pre-game) maps to status='scheduled'."""
        _make_boxscore(db, game_state="FUT")

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "scheduled"

    def test_refresh_dashboard_games_derives_status_pre_as_scheduled(self, db):
        """game_state='PRE' maps to status='scheduled'."""
        _make_boxscore(db, game_state="PRE")

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "scheduled"

    def test_refresh_dashboard_games_derives_status_none_as_scheduled(self, db):
        """game_state=None maps to status='scheduled'."""
        _make_boxscore(db, game_state=None)

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        assert db.session.get(DashboardGame, _GAME_ID).status == "scheduled"

    def test_refresh_dashboard_games_filters_to_today_only(self, db):
        """refresh_dashboard_games() ignores boxscore rows with a non-today game_date."""
        _make_boxscore(db, game_date="2020-01-01")

        from services.dashboard_game import refresh_dashboard_games
        count = refresh_dashboard_games()

        assert count == 0
        assert db.session.get(DashboardGame, _GAME_ID) is None

    def test_refresh_dashboard_games_upserts_not_appends(self, db):
        """Running refresh_dashboard_games() twice leaves exactly one row per game."""
        _make_boxscore(db)

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()
        refresh_dashboard_games()

        rows = db.session.scalars(
            select(DashboardGame).where(DashboardGame.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_refresh_dashboard_games_updates_changed_field_on_rerun(self, db):
        """refresh_dashboard_games() overwrites away_score when boxscore is updated."""
        _make_boxscore(db)

        from services.dashboard_game import refresh_dashboard_games
        refresh_dashboard_games()

        bs = db.session.get(Boxscore, _GAME_ID)
        bs.away_score = 4
        db.session.commit()

        refresh_dashboard_games()

        row = db.session.get(DashboardGame, _GAME_ID)
        assert row.away_score == 4
        assert len(db.session.scalars(select(DashboardGame)).all()) == 1

    def test_refresh_dashboard_games_returns_count(self, db):
        """refresh_dashboard_games() returns the number of rows upserted."""
        _make_boxscore(db)

        from services.dashboard_game import refresh_dashboard_games
        count = refresh_dashboard_games()

        assert count == 1

    def test_refresh_dashboard_games_empty_boxscore_returns_zero(self, db):
        """refresh_dashboard_games() returns 0 when no boxscore rows exist for today."""
        from services.dashboard_game import refresh_dashboard_games
        count = refresh_dashboard_games()

        assert count == 0

    def test_refresh_dashboard_games_uses_et_date_at_utc_midnight_boundary(self, db):
        """refresh_dashboard_games() picks up ET-today boxscores when UTC is already next day.

        Simulates 23:30 ET on 2026-05-26 (= 03:30 UTC on 2026-05-27): today_et() must
        return '2026-05-26' so the May-26 boxscore is included.
        """
        from unittest.mock import patch
        from services.dashboard_game import refresh_dashboard_games

        _make_boxscore(db, game_id=9901, game_date="2026-05-26")

        with patch("services.dashboard_game.today_et", return_value="2026-05-26"):
            count = refresh_dashboard_games()

        assert count == 1
        assert db.session.get(DashboardGame, 9901) is not None

    def test_refresh_dashboard_games_excludes_et_tomorrow_at_utc_midnight_boundary(self, db):
        """refresh_dashboard_games() excludes ET-tomorrow boxscores at the UTC midnight boundary."""
        from unittest.mock import patch
        from services.dashboard_game import refresh_dashboard_games

        _make_boxscore(db, game_id=9902, game_date="2026-05-27")

        with patch("services.dashboard_game.today_et", return_value="2026-05-26"):
            count = refresh_dashboard_games()

        assert count == 0
        assert db.session.get(DashboardGame, 9902) is None

    def test_refresh_dashboard_games_multiple_games(self, db):
        """refresh_dashboard_games() processes all of today's boxscore rows."""
        _make_boxscore(db, game_id=_GAME_ID)
        _make_boxscore(db, game_id=_GAME_ID + 1)

        from services.dashboard_game import refresh_dashboard_games
        count = refresh_dashboard_games()

        assert count == 2
        assert db.session.get(DashboardGame, _GAME_ID) is not None
        assert db.session.get(DashboardGame, _GAME_ID + 1) is not None


# ── scheduler integration ─────────────────────────────────────────────────────

class TestRefreshDashboardGamesScheduler:
    def test_refresh_dashboard_games_function_exists_in_scheduler(self):
        """scheduler._refresh_dashboard_games is defined and callable."""
        import scheduler as sched
        assert callable(getattr(sched, "_refresh_dashboard_games", None))

    def test_refresh_dashboard_games_calls_service(self, app):
        """_refresh_dashboard_games() delegates to services.dashboard_game.refresh_dashboard_games."""
        from unittest.mock import patch
        import scheduler as sched
        sched._app = app
        with patch("services.dashboard_game.refresh_dashboard_games") as mock_fn:
            sched._with_ctx(sched._refresh_dashboard_games)()
        mock_fn.assert_called_once()
