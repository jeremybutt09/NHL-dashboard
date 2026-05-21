"""Tests verifying docs/data-pipeline.md exists and has required content."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
PIPELINE_DOC = os.path.join(REPO_ROOT, "docs", "data-pipeline.md")


def _doc_text():
    with open(PIPELINE_DOC) as f:
        return f.read()


def test_data_pipeline_doc_exists():
    """docs/data-pipeline.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(PIPELINE_DOC), "docs/data-pipeline.md not found"


def test_data_flow_diagram_present():
    """Top-level data flow diagram must be present (NHL API → DB → API response)."""
    text = _doc_text()
    assert "nhl" in text.lower(), "NHL API reference missing from data flow diagram"
    assert "api" in text.lower(), "API reference missing from data flow diagram"


def test_all_five_jobs_documented():
    """Each of the 5 scheduler job IDs must appear in the doc."""
    text = _doc_text()
    for job_id in ("poll_slate", "poll_live", "poll_odds", "compute_fair", "prune_snapshots"):
        assert job_id in text, f"Job '{job_id}' missing from data pipeline doc"


def test_trigger_intervals_present():
    """Trigger intervals for all jobs must be mentioned."""
    text = _doc_text()
    # poll_slate and poll_odds: 5 min; poll_live: 15 sec; prune_snapshots: 1 hour
    assert "5 min" in text or "5-minute" in text or "5 minutes" in text, \
        "5-minute interval not documented"
    assert "15 sec" in text or "15 seconds" in text or "15-second" in text, \
        "15-second interval not documented"
    assert "1 hour" in text or "hourly" in text, "Hourly interval not documented"


def test_tables_read_and_written_documented():
    """Each job section must reference the tables it reads and writes."""
    text = _doc_text().lower()
    for table in ("team", "game", "odds_snapshot", "model_fair"):
        assert table in text, f"Table '{table}' not referenced in data pipeline doc"


def test_update_strategies_documented():
    """Upsert, insert-only, and delete strategies must be mentioned."""
    text = _doc_text().lower()
    assert "upsert" in text, "Upsert strategy not documented"
    assert "insert" in text, "Insert-only strategy not documented"
    assert "delete" in text, "Delete strategy not documented"


def test_devig_formula_explained():
    """The model_fair computation (devig formula) must be explained."""
    text = _doc_text().lower()
    assert "devig" in text, "Devig formula explanation missing"
    assert "implied" in text, "Implied probability explanation missing"


def test_snapshot_pruning_policy_noted():
    """The 7-day retention and hourly purge policy must appear in the doc."""
    text = _doc_text()
    assert "7" in text, "7-day retention not mentioned"
    assert "prune" in text.lower() or "retention" in text.lower() or "purge" in text.lower(), \
        "Pruning/retention policy not documented"


def test_local_dev_safety_noted():
    """Document must indicate which jobs are safe to disable for local development."""
    text = _doc_text().lower()
    assert "local" in text or "development" in text or "dev" in text, \
        "Local development guidance missing from pipeline doc"
    assert "disable" in text or "safe" in text or "skip" in text, \
        "No guidance on which jobs can be disabled for local dev"
