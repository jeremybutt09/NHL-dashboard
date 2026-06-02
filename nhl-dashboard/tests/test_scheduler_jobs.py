"""Unit tests for background scheduler job functions (Issue #93).

Each job function is called directly — no APScheduler scheduler is started.
All NHL API calls are mocked via unittest.mock.patch.
"""
import logging
import os
from unittest.mock import patch

import pytest

_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


# ── poll_nhl_odds ─────────────────────────────────────────────────────────────

class TestPollNhlOddsConfig:
    def test_poll_score_interval_default_is_30(self, app):
        """POLL_SCORE_INTERVAL defaults to 30 seconds in Config."""
        assert app.config["POLL_SCORE_INTERVAL"] == 30

    def test_poll_nhl_odds_function_exists_in_scheduler(self):
        """scheduler._poll_nhl_odds is defined and callable."""
        import scheduler as sched
        assert callable(getattr(sched, "_poll_nhl_odds", None))

    def test_poll_nhl_odds_calls_refresh_nhl_odds(self, app):
        """_poll_nhl_odds() calls services.scores.refresh_nhl_odds."""
        import scheduler as sched
        sched._app = app
        with patch("services.scores.refresh_nhl_odds") as mock_refresh:
            sched._with_ctx(sched._poll_nhl_odds)()
        mock_refresh.assert_called_once()


# ── daily historical refresh ──────────────────────────────────────────────────

class TestDailyHistoricalRefresh:
    def test_refresh_historical_function_exists_in_scheduler(self):
        """scheduler._refresh_historical is defined and callable."""
        import scheduler as sched
        assert callable(getattr(sched, "_refresh_historical", None))

    def test_refresh_historical_calls_refresh_recent_historical_games(self, app):
        """_refresh_historical() delegates to services.historical.refresh_recent_historical_games."""
        import scheduler as sched
        sched._app = app
        with patch("services.historical.refresh_recent_historical_games") as mock_fn:
            sched._with_ctx(sched._refresh_historical)()
        mock_fn.assert_called_once()
