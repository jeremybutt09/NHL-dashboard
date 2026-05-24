"""Tests for structured logging in scheduler jobs (Issue #102).

Verifies that _with_ctx emits INFO on success and ERROR (with traceback)
on exception, that no print() calls exist in scheduler.py, and that the
root logger level is driven by FLASK_LOG_LEVEL.
"""
import logging
import os
from unittest.mock import patch

import pytest

import scheduler as sched


# ── helper ────────────────────────────────────────────────────────────────────

def _set_app(app):
    """Point the module-global _app at the test Flask app."""
    sched._app = app


# ── successful run emits INFO ─────────────────────────────────────────────────

class TestPollSlateSuccessLog:
    def test_poll_slate_success_emits_info_log(self, app, caplog):
        """_with_ctx(_poll_slate) emits at least one INFO record on success."""
        _set_app(app)
        with patch("services.slate.refresh_slate"):
            with caplog.at_level(logging.INFO, logger="scheduler"):
                sched._with_ctx(sched._poll_slate)()

        assert any(r.levelno == logging.INFO for r in caplog.records)

    def test_poll_slate_success_log_contains_job_name(self, app, caplog):
        """INFO record from a successful run references the job function name."""
        _set_app(app)
        with patch("services.slate.refresh_slate"):
            with caplog.at_level(logging.INFO, logger="scheduler"):
                sched._with_ctx(sched._poll_slate)()

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("_poll_slate" in m or "poll_slate" in m for m in info_messages)


# ── failed run emits ERROR with traceback ────────────────────────────────────

class TestPollSlateErrorLog:
    def test_poll_slate_exception_emits_error_log(self, app, caplog):
        """_with_ctx(_poll_slate) emits an ERROR record when refresh_slate raises."""
        _set_app(app)
        with patch("services.slate.refresh_slate", side_effect=RuntimeError("nhl api down")):
            with caplog.at_level(logging.ERROR, logger="scheduler"):
                sched._with_ctx(sched._poll_slate)()

        assert any(r.levelno == logging.ERROR for r in caplog.records)

    def test_poll_slate_exception_log_contains_job_name(self, app, caplog):
        """ERROR record references the failing job function name."""
        _set_app(app)
        with patch("services.slate.refresh_slate", side_effect=RuntimeError("nhl api down")):
            with caplog.at_level(logging.ERROR, logger="scheduler"):
                sched._with_ctx(sched._poll_slate)()

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("_poll_slate" in r.message or "poll_slate" in r.message for r in error_records)

    def test_poll_slate_exception_includes_exc_info(self, app, caplog):
        """ERROR log record carries exc_info so the traceback is present."""
        _set_app(app)
        with patch("services.slate.refresh_slate", side_effect=RuntimeError("nhl api down")):
            with caplog.at_level(logging.ERROR, logger="scheduler"):
                sched._with_ctx(sched._poll_slate)()

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records, "No ERROR records emitted"
        assert error_records[0].exc_info is not None, "exc_info (traceback) missing from ERROR record"

    def test_poll_slate_exception_does_not_propagate(self, app):
        """Exception inside the job must be swallowed — the wrapper should not re-raise."""
        _set_app(app)
        with patch("services.slate.refresh_slate", side_effect=RuntimeError("nhl api down")):
            # Should not raise
            sched._with_ctx(sched._poll_slate)()


# ── log level is configurable ─────────────────────────────────────────────────

class TestLogLevelConfigurable:
    def test_flask_log_level_warning_sets_root_logger(self, monkeypatch):
        """FLASK_LOG_LEVEL=WARNING causes create_app() to set root logger to WARNING."""
        monkeypatch.setenv("FLASK_LOG_LEVEL", "WARNING")
        from app import create_app
        create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        assert logging.getLogger().level == logging.WARNING

    def test_flask_log_level_info_is_default(self, monkeypatch):
        """Root logger is INFO when FLASK_LOG_LEVEL is not set."""
        monkeypatch.delenv("FLASK_LOG_LEVEL", raising=False)
        from app import create_app
        create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        assert logging.getLogger().level == logging.INFO


# ── no print() calls remain ───────────────────────────────────────────────────

class TestNoPrintCalls:
    def test_scheduler_has_no_print_calls(self):
        """scheduler.py must contain zero print() calls."""
        scheduler_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "scheduler.py"
        )
        with open(scheduler_path) as fh:
            source = fh.read()
        assert "print(" not in source, "Found print() call in scheduler.py"
