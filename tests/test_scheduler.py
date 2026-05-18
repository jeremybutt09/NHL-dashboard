"""Tests for scheduler jobs and odds client stub (Issue #29)."""

import sys
import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'backend'))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_ctx(app):
    """Push app context and recreate tables for each test."""
    with app.app_context():
        from app import db
        db.create_all()
        yield app


# ---------------------------------------------------------------------------
# odds_client tests
# ---------------------------------------------------------------------------

def test_get_odds_returns_correct_shape():
    """get_odds() returns a dict with the four required integer keys."""
    import odds_client

    result = odds_client.get_odds(1001)

    assert isinstance(result, dict)
    for key in ("away_ml", "home_ml", "away_ml_open", "home_ml_open"):
        assert key in result
        assert isinstance(result[key], int)


def test_get_odds_is_deterministic():
    """get_odds() returns the same values on repeated calls for the same game_id."""
    import odds_client

    first = odds_client.get_odds(2026010001)
    second = odds_client.get_odds(2026010001)

    assert first == second


# ---------------------------------------------------------------------------
# scheduler job registration tests
# ---------------------------------------------------------------------------

def test_jobs_are_registered_with_correct_intervals(app):
    """_make_scheduler() registers all 5 jobs with the correct trigger intervals."""
    import scheduler

    sched = scheduler._make_scheduler(app)
    jobs = {j.id: j for j in sched.get_jobs()}

    assert set(jobs.keys()) == {
        "poll_slate", "poll_live", "poll_odds", "compute_fair", "prune_snapshots"
    }

    assert jobs["poll_slate"].trigger.interval == timedelta(seconds=300)
    assert jobs["poll_live"].trigger.interval == timedelta(seconds=15)
    assert jobs["poll_odds"].trigger.interval == timedelta(seconds=300)
    assert jobs["compute_fair"].trigger.interval == timedelta(seconds=300)
    assert jobs["prune_snapshots"].trigger.interval == timedelta(seconds=3600)


def test_init_scheduler_does_not_start_in_testing_mode(app):
    """init_scheduler() returns without starting when TESTING=True."""
    import scheduler

    result = scheduler.init_scheduler(app)

    assert result is None


# ---------------------------------------------------------------------------
# poll_odds logic tests
# ---------------------------------------------------------------------------

def test_poll_odds_inserts_snapshot_with_correct_implied_values(app_ctx):
    """poll_odds() inserts an OddsSnapshot with correct implied probability values."""
    from app import db
    from models import Game, Team, OddsSnapshot
    from services.implied import american_to_implied
    import odds_client
    import scheduler

    db.session.add(Team(code="TOR", name="Toronto"))
    db.session.add(Team(code="BOS", name="Boston"))
    db.session.add(Game(
        id=2026010001,
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        away_score=0,
        home_score=0,
        away_sog=0,
        home_sog=0,
        start_utc=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ))
    db.session.commit()

    scheduler.poll_odds()

    snaps = db.session.query(OddsSnapshot).filter_by(game_id=2026010001).all()
    assert len(snaps) == 1

    snap = snaps[0]
    expected = odds_client.get_odds(2026010001)
    assert snap.away_ml == expected["away_ml"]
    assert snap.home_ml == expected["home_ml"]
    assert snap.book == "consensus"
    assert abs(snap.away_implied - american_to_implied(expected["away_ml"])) < 0.01
    assert abs(snap.home_implied - american_to_implied(expected["home_ml"])) < 0.01


# ---------------------------------------------------------------------------
# prune_snapshots logic tests
# ---------------------------------------------------------------------------

def test_prune_snapshots_deletes_only_old_rows(app_ctx):
    """prune_snapshots() removes rows older than 7 days and keeps recent ones."""
    from app import db
    from models import Game, Team, OddsSnapshot
    import scheduler

    db.session.add(Team(code="TOR", name="Toronto"))
    db.session.add(Team(code="BOS", name="Boston"))
    db.session.add(Game(
        id=2026010001,
        away_code="TOR",
        home_code="BOS",
        status="final",
        away_score=3,
        home_score=2,
        away_sog=28,
        home_sog=25,
        start_utc=datetime.now(timezone.utc) - timedelta(days=8),
        updated_at=datetime.now(timezone.utc),
    ))
    db.session.commit()

    now = datetime.now(timezone.utc)
    old_snap = OddsSnapshot(
        game_id=2026010001,
        fetched_at=now - timedelta(days=8),
        book="consensus",
        away_ml=120,
        home_ml=-140,
        away_implied=45.45,
        home_implied=58.33,
    )
    recent_snap = OddsSnapshot(
        game_id=2026010001,
        fetched_at=now - timedelta(days=6),
        book="consensus",
        away_ml=120,
        home_ml=-140,
        away_implied=45.45,
        home_implied=58.33,
    )
    db.session.add(old_snap)
    db.session.add(recent_snap)
    db.session.commit()

    old_id = old_snap.id
    recent_id = recent_snap.id

    scheduler.prune_snapshots()

    assert db.session.get(OddsSnapshot, old_id) is None
    assert db.session.get(OddsSnapshot, recent_id) is not None
