"""Unit tests for background scheduler job functions (Issue #93).

Each job function is called directly — no APScheduler scheduler is started.
All NHL API calls are mocked via unittest.mock.patch.
"""
import json
import logging
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


# ── poll_scores ───────────────────────────────────────────────────────────────

def _make_score_now_data(*games):
    """Build a minimal /v1/score/now response from a list of game dicts."""
    return {"currentDate": "2026-05-24", "games": list(games)}


def _score_game(game_id, state="LIVE", period_num=2, period_type="REG",
                clock="14:22", away_score=1, home_score=2, away_sog=12, home_sog=15):
    """Build a single game entry matching the /v1/score/now shape."""
    return {
        "id": game_id,
        "gameState": state,
        "periodDescriptor": {"number": period_num, "periodType": period_type},
        "clock": {"timeRemaining": clock},
        "awayTeam": {"abbrev": "TST", "score": away_score, "sog": away_sog},
        "homeTeam": {"abbrev": "HME", "score": home_score, "sog": home_sog},
    }


class TestPollScores:
    def _make_teams(self, team_factory):
        team_factory(code="EDM", name="Edmonton Oilers")
        team_factory(code="FLA", name="Florida Panthers")

    def _make_game(self, db, game_id, status="scheduled"):
        game = Game(
            game_id=game_id,
            away_code="EDM",
            home_code="FLA",
            status=status,
            away_score=0,
            home_score=0,
            away_sog=0,
            home_sog=0,
            start_utc=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(game)
        db.session.commit()
        return game

    def test_refresh_scores_updates_all_matched_games(self, db, team_factory):
        """refresh_scores() updates all 3 game rows when all are present in the DB."""
        self._make_teams(team_factory)
        g1 = self._make_game(db, 2026030201, status="scheduled")
        g2 = self._make_game(db, 2026030202, status="live")
        g3 = self._make_game(db, 2026030203, status="live")

        api_data = _make_score_now_data(
            _score_game(2026030201, state="LIVE", away_score=1, home_score=0),
            _score_game(2026030202, state="FUT",  away_score=0, home_score=0),
            _score_game(2026030203, state="FINAL", away_score=3, home_score=2),
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        db.session.refresh(g1)
        db.session.refresh(g2)
        db.session.refresh(g3)
        assert g1.status == "live"
        assert g2.status == "scheduled"
        assert g3.status == "final"
        assert g3.away_score == 3
        assert g3.home_score == 2

    def test_refresh_scores_single_api_call(self, db, team_factory):
        """refresh_scores() issues exactly one GET to /v1/score/now regardless of game count."""
        self._make_teams(team_factory)
        self._make_game(db, 2026030201)
        self._make_game(db, 2026030202)

        api_data = _make_score_now_data(
            _score_game(2026030201),
            _score_game(2026030202),
        )
        with patch("nhl_client.get_score_now", return_value=api_data) as mock_api:
            from services.scores import refresh_scores
            refresh_scores()

        assert mock_api.call_count == 1

    def test_refresh_scores_transitions_scheduled_to_live(self, db, team_factory):
        """refresh_scores() transitions a scheduled game to live when API returns LIVE."""
        self._make_teams(team_factory)
        game = self._make_game(db, 2026030201, status="scheduled")

        api_data = _make_score_now_data(
            _score_game(2026030201, state="LIVE", period_num=1, clock="18:30",
                        away_score=0, home_score=0)
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        db.session.refresh(game)
        assert game.status == "live"
        assert game.period == "1st"
        assert game.clock == "18:30"

    def test_refresh_scores_transitions_live_to_final(self, db, team_factory):
        """refresh_scores() transitions a live game to final when API returns FINAL."""
        self._make_teams(team_factory)
        game = self._make_game(db, 2026030201, status="live")

        api_data = _make_score_now_data(
            _score_game(2026030201, state="FINAL", period_num=3, clock="00:00",
                        away_score=4, home_score=2)
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        db.session.refresh(game)
        assert game.status == "final"
        assert game.away_score == 4
        assert game.home_score == 2

    def test_refresh_scores_skips_missing_game_id(self, db, team_factory):
        """refresh_scores() skips a game_id from the API that is not in the DB."""
        self._make_teams(team_factory)
        # Only game 201 is in DB; API also returns 999 which is absent
        game = self._make_game(db, 2026030201)

        api_data = _make_score_now_data(
            _score_game(2026030201, state="LIVE"),
            _score_game(9999999999, state="LIVE"),  # not in DB
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()  # must not raise

        db.session.refresh(game)
        assert game.status == "live"

    def test_refresh_scores_logs_warning_for_missing_game_id(self, db, team_factory, caplog):
        """refresh_scores() logs a warning when a game_id from the API is not in the DB."""
        self._make_teams(team_factory)
        self._make_game(db, 2026030201)

        api_data = _make_score_now_data(
            _score_game(2026030201, state="LIVE"),
            _score_game(9999999999, state="LIVE"),
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            with caplog.at_level(logging.WARNING):
                from services.scores import refresh_scores
                refresh_scores()

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("9999999999" in m for m in warning_messages)
        assert any("skipping" in m for m in warning_messages)

    def test_refresh_scores_api_failure_logs_error(self, db, team_factory, caplog):
        """refresh_scores() logs an error when get_score_now raises."""
        self._make_teams(team_factory)
        self._make_game(db, 2026030201)

        with patch("nhl_client.get_score_now", side_effect=RuntimeError("NHL API down")):
            with caplog.at_level(logging.ERROR):
                from services.scores import refresh_scores
                refresh_scores()

        assert any(r.levelno == logging.ERROR for r in caplog.records)

    def test_refresh_scores_no_partial_writes_on_api_failure(self, db, team_factory):
        """refresh_scores() makes no DB writes when get_score_now raises."""
        self._make_teams(team_factory)
        game = self._make_game(db, 2026030201, status="scheduled")

        with patch("nhl_client.get_score_now", side_effect=RuntimeError("NHL API down")):
            from services.scores import refresh_scores
            refresh_scores()

        db.session.refresh(game)
        assert game.status == "scheduled"

    def test_refresh_scores_period_ot_parsed_correctly(self, db, team_factory):
        """refresh_scores() writes 'OT' for a game with periodType='OT'."""
        self._make_teams(team_factory)
        game = self._make_game(db, 2026030201, status="live")

        api_data = _make_score_now_data(
            _score_game(2026030201, state="LIVE", period_num=4, period_type="OT", clock="03:12")
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        db.session.refresh(game)
        assert game.period == "OT"

    def test_refresh_scores_sog_updated(self, db, team_factory):
        """refresh_scores() updates away_sog and home_sog from the API response."""
        self._make_teams(team_factory)
        game = self._make_game(db, 2026030201)

        api_data = _make_score_now_data(
            _score_game(2026030201, state="LIVE", away_sog=22, home_sog=18)
        )
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        db.session.refresh(game)
        assert game.away_sog == 22
        assert game.home_sog == 18


# ── POLL_SCORE_INTERVAL config ────────────────────────────────────────────────

class TestPollScoreIntervalConfig:
    def test_poll_score_interval_default_is_30(self, app):
        """POLL_SCORE_INTERVAL defaults to 30 seconds in Config."""
        assert app.config["POLL_SCORE_INTERVAL"] == 30

    def test_poll_scores_function_exists_in_scheduler(self):
        """scheduler._poll_scores is defined and callable."""
        import scheduler as sched
        assert callable(getattr(sched, "_poll_scores", None))

    def test_poll_scores_calls_refresh_scores(self, app):
        """_poll_scores() calls services.scores.refresh_scores."""
        import scheduler as sched
        sched._app = app
        with patch("services.scores.refresh_scores") as mock_refresh:
            sched._with_ctx(sched._poll_scores)()
        mock_refresh.assert_called_once()
