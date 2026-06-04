"""
Issue #167 — Failing tests for docs/tables/dim_player.md.

Verifies the file exists and contains all five required sections
matching the style established by docs/tables/team.md.
All tests fail until the file is created.
"""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
_DOC = os.path.join(REPO_ROOT, "docs", "tables", "dim_player.md")


def _read():
    with open(_DOC) as f:
        return f.read()


def test_dim_player_doc_exists():
    """docs/tables/dim_player.md must exist."""
    assert os.path.isfile(_DOC), "docs/tables/dim_player.md does not exist"


def test_dim_player_doc_title():
    """File must contain the table title header."""
    assert "# Table: `dim_player`" in _read()


def test_dim_player_doc_sqlite_path():
    """File must reference the correct SQLite database path."""
    assert "instance/nhl.db" in _read()


def test_dim_player_doc_model_reference():
    """File must reference the DimPlayer model in models.py."""
    assert "DimPlayer" in _read()


def test_dim_player_doc_columns_section():
    """File must contain a Columns section."""
    assert "## Columns" in _read()


def test_dim_player_doc_all_12_columns():
    """File must document all 12 columns from the DimPlayer model."""
    text = _read()
    columns = [
        "player_id",
        "first_name",
        "last_name",
        "sweater_number",
        "position",
        "shoots_catches",
        "height_in_inches",
        "weight_in_pounds",
        "birth_date",
        "birth_country",
        "headshot_url",
        "updated_at",
    ]
    for col in columns:
        assert col in text, f"Column '{col}' not found in dim_player.md"


def test_dim_player_doc_source_endpoints_section():
    """File must contain a Source endpoints section."""
    assert "## Source endpoints" in _read()


def test_dim_player_doc_roster_endpoint_url():
    """File must reference the NHL roster API endpoint."""
    assert "api-web.nhle.com/v1/roster" in _read()


def test_dim_player_doc_api_field_mapping_table():
    """File must contain an API field → column mapping table."""
    text = _read()
    assert "API field" in text or "API JSON path" in text


def test_dim_player_doc_relationships_section():
    """File must contain a Relationships section."""
    assert "## Relationships" in _read()


def test_dim_player_doc_boxscore_skater_relationship():
    """File must document the boxscore_skater_stats → dim_player relationship."""
    assert "boxscore_skater_stats" in _read()


def test_dim_player_doc_boxscore_goalie_relationship():
    """File must document the boxscore_goalie_stats → dim_player relationship."""
    assert "boxscore_goalie_stats" in _read()
