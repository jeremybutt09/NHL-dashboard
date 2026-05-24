"""
Issue #105 — Failing tests for doc accuracy corrections.

Each test asserts the CORRECT state that the docs must reach after the rewrite.
All tests should FAIL against the stale docs and PASS once the docs are fixed.
"""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

_PIPELINE = os.path.join(REPO_ROOT, "docs", "data-pipeline.md")
_MAPPINGS = os.path.join(REPO_ROOT, "docs", "api-field-mappings.md")
_ODDS     = os.path.join(REPO_ROOT, "docs", "odds-data.md")
_TESTING  = os.path.join(REPO_ROOT, "docs", "testing-guide.md")
_SCHEMA   = os.path.join(REPO_ROOT, "docs", "database-schema.md")
_MODELS   = os.path.join(REPO_ROOT, "nhl-dashboard", "backend", "models.py")


def _read(path):
    with open(path) as f:
        return f.read()


# ── data-pipeline.md ─────────────────────────────────────────────────────────

def test_data_pipeline_refresh_slate_function_name():
    """data-pipeline.md must reference refresh_slate(), not build_slate()."""
    assert "refresh_slate" in _read(_PIPELINE), \
        "refresh_slate() not found in data-pipeline.md"


def test_data_pipeline_no_build_slate():
    """data-pipeline.md must not reference the obsolete build_slate() name."""
    assert "build_slate" not in _read(_PIPELINE), \
        "Obsolete build_slate() name still present in data-pipeline.md"


def test_data_pipeline_refresh_live_function_name():
    """data-pipeline.md must reference refresh_live(), not update_live_scores()."""
    assert "refresh_live" in _read(_PIPELINE), \
        "refresh_live() not found in data-pipeline.md"


def test_data_pipeline_no_update_live_scores():
    """data-pipeline.md must not reference the obsolete update_live_scores() name."""
    assert "update_live_scores" not in _read(_PIPELINE), \
        "Obsolete update_live_scores() still present in data-pipeline.md"


def test_data_pipeline_prune_old_snapshots_referenced():
    """data-pipeline.md must reference prune_old_snapshots() from services/slate.py."""
    assert "prune_old_snapshots" in _read(_PIPELINE), \
        "prune_old_snapshots() not documented in data-pipeline.md"


def test_data_pipeline_start_scheduler_referenced():
    """data-pipeline.md must reference start_scheduler(app), not init_scheduler()."""
    assert "start_scheduler" in _read(_PIPELINE), \
        "start_scheduler(app) not found in data-pipeline.md"


def test_data_pipeline_no_init_scheduler():
    """data-pipeline.md must not reference the obsolete init_scheduler() name."""
    assert "init_scheduler" not in _read(_PIPELINE), \
        "Obsolete init_scheduler() still present in data-pipeline.md"


def test_data_pipeline_prune_job_id_is_prune():
    """APScheduler job ID for the prune job is 'prune', not 'prune_snapshots'."""
    text = _read(_PIPELINE)
    # Job ID column in the scheduler table must show the actual id used in add_job()
    assert "| `prune`" in text or '| prune |' in text or "'prune'" in text, \
        "Actual prune job ID ('prune') not documented in data-pipeline.md"


def test_data_pipeline_poll_odds_delegates_to_refresh_odds():
    """data-pipeline.md must document that _poll_odds() delegates to refresh_odds()."""
    assert "refresh_odds" in _read(_PIPELINE), \
        "_poll_odds() → refresh_odds() delegation not documented in data-pipeline.md"


# ── api-field-mappings.md ────────────────────────────────────────────────────

def test_api_mappings_get_schedule_now_function_name():
    """api-field-mappings.md must reference get_schedule_now(), not get_schedule_today()."""
    assert "get_schedule_now" in _read(_MAPPINGS), \
        "get_schedule_now() not found in api-field-mappings.md"


def test_api_mappings_no_NhlClient_class():
    """nhl_client.py uses module-level functions; NhlClient class must not appear."""
    assert "NhlClient" not in _read(_MAPPINGS), \
        "Non-existent NhlClient class still referenced in api-field-mappings.md"


def test_api_mappings_no_get_schedule_today():
    """The obsolete NhlClient.get_schedule_today() must not appear in the doc."""
    assert "get_schedule_today" not in _read(_MAPPINGS), \
        "Obsolete get_schedule_today() still present in api-field-mappings.md"


def test_api_mappings_cache_maxsize_128():
    """TTLCache in nhl_client.py is maxsize=128, doc must reflect this (not 64)."""
    text = _read(_MAPPINGS)
    assert "128" in text, "Cache maxsize 128 not documented in api-field-mappings.md"
    assert "64-slot" not in text, "Wrong cache size '64-slot' still in api-field-mappings.md"


def test_api_mappings_cache_keyed_by_url_path():
    """Cache in nhl_client.py is keyed by URL path string, not game_id."""
    text = _read(_MAPPINGS)
    # Doc must say the key is the URL/path, not game_id
    assert ("path" in text.lower() or "/gamecenter" in text or "url" in text.lower()), \
        "Cache key (URL path string) not described in api-field-mappings.md"
    assert "keyed by `game_id`" not in text and "key by game_id" not in text, \
        "Wrong 'keyed by game_id' cache description still in api-field-mappings.md"


def test_api_mappings_upsert_uses_session_get():
    """Upsert pattern is db.session.get() + add(), not db.session.merge()."""
    text = _read(_MAPPINGS)
    assert "session.get" in text or "db.session.get" in text, \
        "db.session.get() upsert pattern not documented in api-field-mappings.md"


def test_api_mappings_no_session_merge():
    """db.session.merge() is not used; must not appear in api-field-mappings.md."""
    assert "session.merge" not in _read(_MAPPINGS), \
        "Incorrect db.session.merge() still referenced in api-field-mappings.md"


def test_api_mappings_fetch_odds_function_name():
    """odds_client.py exports fetch_odds(), not get_odds(); doc must reflect this."""
    assert "fetch_odds" in _read(_MAPPINGS), \
        "fetch_odds() not documented in api-field-mappings.md"


def test_api_mappings_fetch_odds_takes_list():
    """fetch_odds() takes a list of game_ids; doc must show list[int] or game_ids param."""
    text = _read(_MAPPINGS)
    assert "game_ids" in text or "list[int]" in text, \
        "fetch_odds(game_ids: list[int]) signature not in api-field-mappings.md"


def test_api_mappings_status_mapping_inline_in_refresh_slate():
    """Status-mapping logic is inline in refresh_slate(); doc must reflect actual location."""
    text = _read(_MAPPINGS)
    assert "refresh_slate" in text or "slate.py" in text, \
        "Inline status-mapping location (refresh_slate/slate.py) missing from api-field-mappings.md"


def test_api_mappings_period_mapping_inline_in_live():
    """Period-mapping logic is inline in _update_from_boxscore(); doc must reflect this."""
    text = _read(_MAPPINGS)
    assert "_update_from_boxscore" in text or "live.py" in text, \
        "Inline period-mapping location (_update_from_boxscore/live.py) missing from api-field-mappings.md"


# ── odds-data.md ─────────────────────────────────────────────────────────────

def test_odds_data_fetch_odds_function_name():
    """odds-data.md must document fetch_odds(), not the obsolete get_odds()."""
    text = _read(_ODDS)
    assert "fetch_odds" in text, "fetch_odds() not documented in odds-data.md"


def test_odds_data_no_get_odds_as_main_function():
    """get_odds() no longer exists; must not be described as the current interface."""
    text = _read(_ODDS)
    # 'get_odds' must not appear as the current stub function name
    assert "get_odds(game_id)" not in text, \
        "Obsolete get_odds(game_id) still described as current interface in odds-data.md"


def test_odds_data_mock_constant_name():
    """odds_client.py uses _MOCK dict, not _SLATE_ODDS; doc must be updated."""
    text = _read(_ODDS)
    assert "_MOCK" in text or "MOCK" in text.upper(), \
        "_MOCK constant not documented in odds-data.md"


def test_odds_data_return_shape_has_away_ml_open():
    """fetch_odds() return shape includes away_ml_open and home_ml_open columns."""
    text = _read(_ODDS)
    assert "away_ml_open" in text and "home_ml_open" in text, \
        "away_ml_open/home_ml_open not documented in fetch_odds return shape in odds-data.md"


def test_odds_data_fetch_odds_returns_list():
    """fetch_odds() returns list[dict], doc must reflect the list return type."""
    text = _read(_ODDS)
    assert "list" in text.lower() or "[]" in text or "[{" in text, \
        "list return type for fetch_odds() not documented in odds-data.md"


# ── testing-guide.md ─────────────────────────────────────────────────────────

def test_testing_guide_no_nhl_dashboard_package():
    """No nhl_dashboard Python package exists; coverage command must not reference it."""
    text = _read(_TESTING)
    assert "nhl_dashboard" not in text, \
        "Non-existent package 'nhl_dashboard' still in coverage command in testing-guide.md"


def test_testing_guide_status_example_lowercase():
    """App normalizes status to lowercase; example must use 'live', not 'LIVE'."""
    text = _read(_TESTING)
    assert '"LIVE"' not in text and "'LIVE'" not in text, \
        "Uppercase 'LIVE' status still in example in testing-guide.md"
    assert '"live"' in text or "'live'" in text, \
        "Lowercase 'live' status example missing from testing-guide.md"


# ── database-schema.md + models.py ───────────────────────────────────────────

def test_models_game_start_utc_nullable_false():
    """game.start_utc is documented as NOT NULL; models.py must enforce nullable=False."""
    text = _read(_MODELS)
    assert "start_utc" in text and "nullable=False" in text, \
        "game.start_utc missing nullable=False in models.py"


def test_models_game_status_nullable_false():
    """game.status is documented as NOT NULL; models.py must enforce nullable=False."""
    import re
    text = _read(_MODELS)
    # Find the Game model section and check the status line
    match = re.search(r'status\s*=\s*db\.Column\(.*?nullable=False', text)
    assert match, "game.status missing nullable=False in models.py"


def test_models_odds_snapshot_fetched_at_nullable_false():
    """odds_snapshot.fetched_at is documented as NOT NULL; models.py must enforce it."""
    import re
    text = _read(_MODELS)
    match = re.search(r'fetched_at\s*=\s*db\.Column\(.*?nullable=False', text)
    assert match, "odds_snapshot.fetched_at missing nullable=False in models.py"


def test_models_odds_snapshot_book_nullable_false():
    """odds_snapshot.book is documented as NOT NULL; models.py must enforce it."""
    import re
    text = _read(_MODELS)
    match = re.search(r'book\s*=\s*db\.Column\(.*?nullable=False', text)
    assert match, "odds_snapshot.book missing nullable=False in models.py"
