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
    """Each of the 4 tables must have its own section heading."""
    text = _doc_text()
    for table in ("team", "game", "odds_snapshot", "model_fair"):
        assert table in text.lower(), f"Table '{table}' section missing from schema doc"


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
