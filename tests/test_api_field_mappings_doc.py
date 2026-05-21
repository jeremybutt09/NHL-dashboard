"""Tests verifying docs/api-field-mappings.md exists and has required content."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_PATH = os.path.join(REPO_ROOT, "docs", "api-field-mappings.md")


def _doc_text():
    with open(DOC_PATH) as f:
        return f.read()


def test_api_field_mappings_doc_exists():
    """docs/api-field-mappings.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(DOC_PATH), "docs/api-field-mappings.md not found"


def test_schedule_endpoint_section_present():
    """/v1/schedule/now endpoint must have its own section."""
    text = _doc_text()
    assert "/v1/schedule/now" in text, "Schedule endpoint section missing"


def test_boxscore_endpoint_section_present():
    """/v1/gamecenter/{game_id}/boxscore endpoint must have its own section."""
    text = _doc_text()
    assert "/v1/gamecenter" in text, "Boxscore endpoint section missing"


def test_team_table_mappings_present():
    """team table column mappings must be documented."""
    text = _doc_text()
    assert "team.code" in text, "team.code mapping missing"
    assert "team.name" in text, "team.name mapping missing"


def test_game_table_mappings_present():
    """game table column mappings must be documented."""
    text = _doc_text()
    for col in ("game.id", "game.start_utc", "game.venue", "game.away_code",
                "game.home_code", "game.status"):
        assert col in text, f"game.{col} mapping missing"


def test_live_update_fields_present():
    """Live-update fields (period, clock, scores, sog) must be documented."""
    text = _doc_text()
    for col in ("game.period", "game.clock", "game.away_score", "game.home_score",
                "game.away_sog", "game.home_sog"):
        assert col in text, f"{col} live-update mapping missing"


def test_transformations_documented():
    """Transformation functions must be called out in the doc."""
    text = _doc_text()
    assert "_map_game_state" in text, "_map_game_state() transform not documented"
    assert "_map_period" in text, "_map_period() transform not documented"


def test_odds_client_stub_documented():
    """odds_client.py fixture data structure must be documented."""
    text = _doc_text()
    assert "odds_client" in text.lower(), "odds_client stub not documented"
    assert "stub" in text.lower() or "fixture" in text.lower(), \
        "odds_client fixture status not noted"


def test_odds_snapshot_columns_documented():
    """odds_snapshot table columns must appear in the doc."""
    text = _doc_text()
    for col in ("away_ml", "home_ml", "away_implied", "home_implied"):
        assert col in text, f"odds_snapshot.{col} mapping missing"


def test_unused_fields_noted():
    """Doc must note fields that are ignored/unused by the implementation."""
    text = _doc_text()
    assert "unused" in text.lower() or "ignored" in text.lower() or "not consumed" in text.lower(), \
        "No note about unused/ignored API fields found"
