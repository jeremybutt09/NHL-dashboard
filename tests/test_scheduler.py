"""Tests for APScheduler background jobs (Issue #42)."""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Game, OddsSnapshot, Team  # noqa: E402


EXPECTED_JOB_IDS = {"poll_slate", "poll_live", "poll_odds", "compute_fair", "prune_snapshots"}


@pytest.fixture
def test_app():
    """Flask app with TESTING=True and in-memory SQLite."""
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


def test_scheduler_does_not_start_in_test_config(test_app):
    """Scheduler must not run when TESTING=True."""
    from scheduler import _scheduler
    assert not _scheduler.running


def test_all_job_ids_registered():
    """All five job IDs must be registered even when scheduler is not started."""
    with patch("scheduler._scheduler.start"):
        application = create_app({
            "TESTING": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })

    with application.app_context():
        _db.create_all()
        from scheduler import _scheduler
        registered_ids = {j.id for j in _scheduler.get_jobs()}
        for job_id in EXPECTED_JOB_IDS:
            assert job_id in registered_ids, f"missing job: {job_id}"
        _db.drop_all()


def test_scheduler_jobs_have_exception_handling():
    """Each scheduler job function must wrap its body in try/except with logger.exception."""
    import inspect
    import scheduler
    source = inspect.getsource(scheduler)
    assert source.count("logger.exception") >= 5


def test_prune_snapshots_deletes_old_rows(test_app):
    """prune_snapshots must delete rows older than 7 days and keep newer ones."""
    now = datetime.utcnow()
    old_cutoff = now - timedelta(days=8)
    recent = now - timedelta(days=1)

    _db.session.add_all([
        Team(code="TOR", name="Maple Leafs"),
        Team(code="BOS", name="Bruins"),
    ])
    _db.session.commit()

    game = Game(
        id=2026020999,
        start_utc=now,
        venue="TD Garden",
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        updated_at=now,
    )
    _db.session.add(game)
    _db.session.commit()

    old_snap = OddsSnapshot(
        game_id=2026020999,
        fetched_at=old_cutoff,
        book="consensus",
        away_ml=120,
        home_ml=-140,
        away_implied=45.0,
        home_implied=58.33,
    )
    new_snap = OddsSnapshot(
        game_id=2026020999,
        fetched_at=recent,
        book="consensus",
        away_ml=115,
        home_ml=-135,
        away_implied=46.5,
        home_implied=57.4,
    )
    _db.session.add_all([old_snap, new_snap])
    _db.session.commit()

    from scheduler import prune_snapshots
    prune_snapshots()

    remaining = OddsSnapshot.query.all()
    assert len(remaining) == 1
    assert remaining[0].fetched_at == recent
