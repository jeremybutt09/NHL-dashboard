"""Unit tests for background scheduler job functions (Issue #93).

Each job function is called directly — no APScheduler scheduler is started.
All NHL API calls are mocked via unittest.mock.patch.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import Game, Team, OddsSnapshot, ModelFair

_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture(name: str) -> dict:
    """Return parsed JSON from tests/fixtures/<name>."""
    with open(os.path.join(_FIXTURES, name)) as fh:
        return json.load(fh)


# ── poll_slate ────────────────────────────────────────────────────────────────

class TestPollSlate:
    def test_refresh_schedule_upserts_game_rows(self, db):
        """refresh_schedule() with a 2-game schedule fixture upserts exactly 2 Game rows."""
        data = _fixture("schedule_now.json")
        with patch("nhl_client.get_schedule_now", return_value=data):
            from services.slate import refresh_schedule
            refresh_schedule()

        games = db.session.scalars(select(Game)).all()
        assert len(games) == 2

    def test_refresh_schedule_upserts_referenced_team_rows(self, db):
        """refresh_schedule() creates Team rows for all teams referenced by the fixture games."""
        data = _fixture("schedule_now.json")
        with patch("nhl_client.get_schedule_now", return_value=data):
            from services.slate import refresh_schedule
            refresh_schedule()

        team_codes = {t.tri_code for t in db.session.scalars(select(Team)).all()}
        assert {"STL", "ANA", "LAK", "SJS"}.issubset(team_codes)

    def test_refresh_schedule_idempotent_no_duplicate_game_rows(self, db):
        """Calling refresh_schedule() twice with identical data does not duplicate Game rows."""
        data = _fixture("schedule_now.json")
        with patch("nhl_client.get_schedule_now", return_value=data):
            from services.slate import refresh_schedule
            refresh_schedule()
            refresh_schedule()

        games = db.session.scalars(select(Game)).all()
        assert len(games) == 2

    def test_refresh_schedule_idempotent_no_duplicate_team_rows(self, db):
        """Calling refresh_schedule() twice with identical data does not duplicate Team rows."""
        data = _fixture("schedule_now.json")
        with patch("nhl_client.get_schedule_now", return_value=data):
            from services.slate import refresh_schedule
            refresh_schedule()
            refresh_schedule()

        teams = db.session.scalars(select(Team)).all()
        # Fixture contains exactly 4 distinct teams: STL, ANA, LAK, SJS
        assert len(teams) == 4


# ── poll_live ─────────────────────────────────────────────────────────────────

class TestPollLive:
    def test_refresh_live_updates_period_clock_and_home_score(
        self, db, team_factory, game_factory
    ):
        """refresh_live() updates period, clock, and score for a game whose status is 'live'."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(
            away_code="TOR",
            home_code="BOS",
            status="live",
            period="1st",
            clock="18:30",
            home_score=0,
            away_score=0,
        )

        boxscore = {
            "gameState": "LIVE",
            "periodDescriptor": {"number": 2, "periodType": "REG"},
            "clock": {"timeRemaining": "14:00"},
            "awayTeam": {"score": 2, "sog": 18},
            "homeTeam": {"score": 1, "sog": 8},
        }
        with patch("nhl_client.get_boxscore", return_value=boxscore):
            from services.live import refresh_live
            refresh_live()

        db.session.refresh(game)
        assert game.period == "2nd"
        assert game.clock == "14:00"
        assert game.home_score == 1

    def test_refresh_live_preserves_venue_and_team_codes(
        self, db, team_factory, game_factory
    ):
        """refresh_live() does not overwrite venue, away_code, or home_code."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="live")
        game.venue = "Scotiabank Arena"
        db.session.commit()

        boxscore = {
            "gameState": "LIVE",
            "periodDescriptor": {"number": 1, "periodType": "REG"},
            "clock": {"timeRemaining": "12:00"},
            "awayTeam": {"score": 0, "sog": 5},
            "homeTeam": {"score": 0, "sog": 5},
        }
        with patch("nhl_client.get_boxscore", return_value=boxscore):
            from services.live import refresh_live
            refresh_live()

        db.session.refresh(game)
        assert game.venue == "Scotiabank Arena"
        assert game.away_code == "TOR"
        assert game.home_code == "BOS"

    def test_refresh_live_skips_non_live_games(self, db, team_factory, game_factory):
        """refresh_live() does not touch games whose status is not 'live'."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(
            away_code="TOR", home_code="BOS", status="scheduled", home_score=0
        )

        with patch("nhl_client.get_boxscore") as mock_bs:
            from services.live import refresh_live
            refresh_live()

        mock_bs.assert_not_called()
        db.session.refresh(game)
        assert game.home_score == 0


# ── poll_odds ─────────────────────────────────────────────────────────────────

class TestPollOdds:
    def _make_game_1001(self, db):
        """Create a Game with game_id=1001, which is present in odds_client._MOCK."""
        # Use a placeholder team code not needing FK enforcement
        game = Game(
            game_id=1001,
            away_code="TOR",
            home_code="BOS",
            status="scheduled",
            start_utc=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(game)
        db.session.commit()
        return game

    def test_refresh_odds_inserts_snapshot_for_active_game(self, db, team_factory):
        """refresh_odds() inserts one OddsSnapshot row for a game in the mock odds table."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        self._make_game_1001(db)

        from services.slate import refresh_odds
        refresh_odds()

        rows = db.session.scalars(
            select(OddsSnapshot).where(OddsSnapshot.game_id == 1001)
        ).all()
        assert len(rows) == 1

    def test_refresh_odds_append_only_second_call_adds_row(self, db, team_factory):
        """Calling refresh_odds() twice inserts two separate OddsSnapshot rows (append-only)."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        self._make_game_1001(db)

        from services.slate import refresh_odds
        refresh_odds()
        refresh_odds()

        rows = db.session.scalars(
            select(OddsSnapshot).where(OddsSnapshot.game_id == 1001)
        ).all()
        assert len(rows) == 2


# ── compute_fair ──────────────────────────────────────────────────────────────

class TestComputeFair:
    def test_compute_all_fair_upserts_model_fair_row(
        self, db, team_factory, game_factory, odds_snapshot_factory
    ):
        """compute_all_fair() creates a ModelFair row for a game that has an OddsSnapshot."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="scheduled")
        odds_snapshot_factory(game_id=game.game_id, away_ml=-110, home_ml=100)

        from services.implied import compute_all_fair
        compute_all_fair()

        mf = db.session.get(ModelFair, game.game_id)
        assert mf is not None

    def test_compute_all_fair_probabilities_sum_to_one_hundred(
        self, db, team_factory, game_factory, odds_snapshot_factory
    ):
        """ModelFair home_fair + away_fair == 100.0 after compute_all_fair()."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="scheduled")
        odds_snapshot_factory(game_id=game.game_id, away_ml=-110, home_ml=100)

        from services.implied import compute_all_fair
        compute_all_fair()

        mf = db.session.get(ModelFair, game.game_id)
        assert mf.home_fair + mf.away_fair == pytest.approx(100.0, abs=0.01)

    def test_compute_all_fair_idempotent_single_row_per_game(
        self, db, team_factory, game_factory, odds_snapshot_factory
    ):
        """Calling compute_all_fair() twice produces exactly one ModelFair row per game."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="scheduled")
        odds_snapshot_factory(game_id=game.game_id)

        from services.implied import compute_all_fair
        compute_all_fair()
        compute_all_fair()

        rows = db.session.scalars(
            select(ModelFair).where(ModelFair.game_id == game.game_id)
        ).all()
        assert len(rows) == 1


# ── prune_snapshots ───────────────────────────────────────────────────────────

class TestPruneSnapshots:
    def _add_snapshot(self, db, game_id: int, fetched_at: datetime) -> OddsSnapshot:
        snap = OddsSnapshot(
            game_id=game_id,
            fetched_at=fetched_at,
            book="consensus",
            away_ml=-110,
            home_ml=100,
            away_implied=52.38,
            home_implied=50.0,
        )
        db.session.add(snap)
        return snap

    def test_prune_snapshots_deletes_row_older_than_7_days(
        self, db, team_factory, game_factory
    ):
        """prune_old_snapshots() removes an OddsSnapshot row that is 8 days old."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="scheduled")
        now = datetime.now(timezone.utc)

        self._add_snapshot(db, game.game_id, now)
        self._add_snapshot(db, game.game_id, now - timedelta(days=3))
        self._add_snapshot(db, game.game_id, now - timedelta(days=8))
        db.session.commit()

        from services.slate import prune_old_snapshots
        prune_old_snapshots()

        remaining = db.session.scalars(
            select(OddsSnapshot).where(OddsSnapshot.game_id == game.game_id)
        ).all()
        assert len(remaining) == 2

    def test_prune_snapshots_keeps_row_at_3_days_old(
        self, db, team_factory, game_factory
    ):
        """prune_old_snapshots() retains a snapshot row that is only 3 days old."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="scheduled")
        now = datetime.now(timezone.utc)

        self._add_snapshot(db, game.game_id, now)
        self._add_snapshot(db, game.game_id, now - timedelta(days=3))
        db.session.commit()

        from services.slate import prune_old_snapshots
        prune_old_snapshots()

        remaining = db.session.scalars(
            select(OddsSnapshot).where(OddsSnapshot.game_id == game.game_id)
        ).all()
        assert len(remaining) == 2

    def test_prune_snapshots_keeps_current_row(
        self, db, team_factory, game_factory
    ):
        """prune_old_snapshots() retains a snapshot row fetched at the current time."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS", status="scheduled")

        self._add_snapshot(db, game.game_id, datetime.now(timezone.utc))
        db.session.commit()

        from services.slate import prune_old_snapshots
        prune_old_snapshots()

        remaining = db.session.scalars(
            select(OddsSnapshot).where(OddsSnapshot.game_id == game.game_id)
        ).all()
        assert len(remaining) == 1
