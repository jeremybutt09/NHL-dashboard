"""Tests verifying docs/database-schema.md exists and has required content."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCHEMA_DOC = os.path.join(REPO_ROOT, "docs", "database-schema.md")


def _doc_text():
    with open(SCHEMA_DOC) as f:
        return f.read()


def test_database_schema_doc_exists():
    """docs/database-schema.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(SCHEMA_DOC), "docs/database-schema.md not found"


def test_all_four_tables_have_sections():
    """All current tables must have their own section headings."""
    text = _doc_text()
    for table in ("team", "live_game", "game", "odds_snapshot", "model_fair",
                  "nhl_odds_partner", "nhl_odds_line", "boxscore", "dashboard_game"):
        assert table in text.lower(), f"Table '{table}' section missing from schema doc"


def test_live_game_table_has_section():
    """live_game table (the live-score table, renamed from legacy game) must be documented."""
    text = _doc_text()
    assert "live_game" in text, "live_game table section missing from database-schema.md"


def test_boxscore_table_has_section():
    """boxscore table (Issue #133) must have its own section."""
    text = _doc_text()
    assert "boxscore" in text.lower(), "boxscore table section missing from database-schema.md"


def test_dashboard_game_table_has_section():
    """dashboard_game table (Issue #134) must have its own section."""
    text = _doc_text()
    assert "dashboard_game" in text.lower(), "dashboard_game table section missing from database-schema.md"


def test_no_nhl_historical_game_reference():
    """nhl_historical_game is a dropped name — must not appear in the schema doc."""
    text = _doc_text()
    assert "nhl_historical_game" not in text, \
        "Stale nhl_historical_game reference found in database-schema.md (renamed to game in Issue #131)"


def test_foreign_key_relationships_described():
    """Foreign key relationships must be explicitly described in the doc."""
    text = _doc_text()
    assert "foreign key" in text.lower(), "No foreign key description found in schema doc"


def test_indices_listed():
    """Indices must be listed in the doc."""
    text = _doc_text()
    assert "index" in text.lower(), "No index information found in schema doc"


def test_no_migrations_note_present():
    """Doc must note that schema changes require manual model edits (no migrations)."""
    text = _doc_text()
    assert "migration" in text.lower(), "No migrations note found in schema doc"


# ── Issue #146: visiting_ → away_ column rename ────────────────────────────────

def test_game_table_no_visiting_columns():
    """game table section must not reference visiting_score or visiting_team_id (Issue #146)."""
    text = _doc_text()
    assert "visiting_score" not in text, \
        "Stale visiting_score column name in database-schema.md — rename to away_score (Issue #146)"
    assert "visiting_team_id" not in text, \
        "Stale visiting_team_id column name in database-schema.md — rename to away_team_id (Issue #146)"


def test_game_table_documents_away_columns():
    """game table section must document away_score and away_team_id columns (Issue #146)."""
    text = _doc_text()
    assert "away_score" in text, \
        "away_score column missing from database-schema.md game table (Issue #146)"
    assert "away_team_id" in text, \
        "away_team_id column missing from database-schema.md game table (Issue #146)"
