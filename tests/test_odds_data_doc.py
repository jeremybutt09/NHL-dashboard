"""Tests verifying docs/odds-data.md exists and has required content."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
ODDS_DOC = os.path.join(REPO_ROOT, "docs", "odds-data.md")


def _doc_text():
    with open(ODDS_DOC) as f:
        return f.read()


def test_odds_data_doc_exists():
    """docs/odds-data.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(ODDS_DOC), "docs/odds-data.md not found"


def test_fixture_structure_documented():
    """The _MOCK fixture structure must be documented with the actual return shape."""
    text = _doc_text()
    assert "_MOCK" in text or "MOCK" in text.upper(), \
        "_MOCK fixture name not documented"
    assert "game_id" in text, "game_id not shown in return shape"
    assert "away_ml" in text, "away_ml key not shown in fixture data structure"
    assert "home_ml" in text, "home_ml key not shown in fixture data structure"


def test_eight_fixture_sets_noted():
    """The doc must note there are 8 hardcoded odds sets."""
    text = _doc_text()
    assert "8" in text, "Number of fixture sets (8) not documented"


def test_american_to_implied_formula_explained():
    """american_to_implied() formula must be explained with an example calculation."""
    text = _doc_text().lower()
    assert "american_to_implied" in text, "american_to_implied not mentioned"
    assert "american" in text, "American odds format not explained"
    assert "implied" in text, "Implied probability concept not explained"


def test_devig_formula_explained():
    """devig_two_way() formula must be explained in plain language with example."""
    text = _doc_text().lower()
    assert "devig_two_way" in text, "devig_two_way function not documented"
    assert "vig" in text, "Vig concept not explained"
    assert "100" in text, "Normalization to 100 not explained"


def test_devig_example_calculation_present():
    """A concrete example of the devig calculation must appear in the doc."""
    text = _doc_text()
    # The issue provides specific values: 45.5, 58.3, 103.8
    assert "103.8" in text or "103" in text, \
        "Devig example total (103.8) not shown"


def test_odds_snapshot_append_only_design_explained():
    """The append-only time-series design of odds_snapshot must be explained."""
    text = _doc_text().lower()
    assert "odds_snapshot" in text, "odds_snapshot table not mentioned"
    assert "append" in text or "time-series" in text or "time series" in text, \
        "Append-only / time-series design not explained"
    assert "sparkline" in text or "trend" in text or "history" in text, \
        "Reason for keeping history (sparklines/trends) not documented"


def test_to_replace_stub_section_present():
    """A 'to replace the stub' section must exist."""
    text = _doc_text().lower()
    assert "replace" in text and "stub" in text, \
        "'To replace the stub' section missing"


def test_get_odds_interface_contract_documented():
    """The fetch_odds(game_ids) interface contract must be documented."""
    text = _doc_text()
    assert "fetch_odds" in text, "fetch_odds interface not documented"
    assert "game_ids" in text or "game_id" in text, "game_id parameter not documented"


def test_files_to_edit_documented():
    """Which file(s) to edit when swapping in a real odds source must be listed."""
    text = _doc_text()
    assert "odds_client.py" in text, "odds_client.py not listed as file to edit"


def test_multi_book_column_noted():
    """New columns needed for multi-book support must be mentioned."""
    text = _doc_text().lower()
    assert "multi-book" in text or "multi book" in text or "multiple book" in text, \
        "Multi-book column requirement not documented"


def test_consensus_book_limitation_noted():
    """The hardcoded 'consensus' book limitation must be called out."""
    text = _doc_text()
    assert "consensus" in text, "'consensus' book limitation not documented"
    assert "book" in text.lower(), "book column not mentioned"
