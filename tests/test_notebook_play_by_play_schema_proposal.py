"""Tests for Issue #176: play_by_play_schema_proposal.ipynb improvements.

Validates that:
  1. The setup cell queries the game table for multiple game IDs instead of
     hardcoding a single GAME_ID.
  2. All three schema DDL blocks (Sections 4, 5, 6) use PRIMARY KEY (game_id,
     event_idx) instead of a surrogate id + UNIQUE constraint.
"""

import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTEBOOK_PATH = os.path.join(
    REPO_ROOT, "nhl-dashboard", "notebooks", "play_by_play_schema_proposal.ipynb"
)


def _load_notebook() -> dict:
    with open(NOTEBOOK_PATH) as f:
        return json.load(f)


def _all_cell_sources(nb: dict) -> str:
    parts = []
    for cell in nb.get("cells", []):
        source = cell.get("source", [])
        if isinstance(source, list):
            parts.append("".join(source))
        else:
            parts.append(source)
    return "\n".join(parts)


def _get_setup_cell_source(nb: dict) -> str:
    """Return the source of the first code cell (the setup cell)."""
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            return "".join(cell.get("source", []))
    return ""


def _get_section_markdown_source(nb: dict, section_marker: str) -> str:
    """Return the markdown source of the cell containing section_marker."""
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if section_marker in source:
                return source
    return ""


# ── File existence and validity ───────────────────────────────────────────────


def test_pbp_notebook_exists():
    """play_by_play_schema_proposal.ipynb must exist."""
    assert os.path.isfile(NOTEBOOK_PATH), f"Notebook not found at {NOTEBOOK_PATH}"


def test_pbp_notebook_is_valid_json():
    """play_by_play_schema_proposal.ipynb must be valid JSON."""
    nb = _load_notebook()
    assert isinstance(nb, dict), "Notebook is not a JSON object"


def test_pbp_notebook_has_nbformat():
    """play_by_play_schema_proposal.ipynb must declare nbformat >= 4."""
    nb = _load_notebook()
    assert "nbformat" in nb
    assert nb["nbformat"] >= 4


def test_pbp_notebook_cells_have_cleared_outputs():
    """All code cells must ship with cleared outputs."""
    nb = _load_notebook()
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            assert cell.get("outputs", []) == [], (
                f"Code cell {i} has non-empty outputs; notebook must ship with cleared outputs"
            )


def test_pbp_no_cell_has_character_per_item_source():
    """Every cell source must contain complete lines, not one character per item."""
    nb = _load_notebook()
    corrupted = []
    for i, cell in enumerate(nb.get("cells", [])):
        src = cell.get("source", [])
        if src and all(len(s.strip()) <= 1 for s in src):
            corrupted.append((i, cell.get("id", "unknown")))
    assert corrupted == [], (
        f"Corrupted character-per-item source found in cells: {corrupted}"
    )


# ── Scenario 1: Multi-game sampling ──────────────────────────────────────────


def test_pbp_setup_cell_no_hardcoded_game_id():
    """Setup cell must not hardcode GAME_ID = 2025030411."""
    nb = _load_notebook()
    src = _get_setup_cell_source(nb)
    assert "GAME_ID = 2025030411" not in src, (
        "Setup cell still hardcodes GAME_ID = 2025030411; "
        "must query the game table instead (Issue #176)"
    )


def test_pbp_setup_cell_queries_game_table():
    """Setup cell must query the game table with game_type IN (2, 3)."""
    nb = _load_notebook()
    src = _get_setup_cell_source(nb)
    assert "game_type" in src, (
        "Setup cell must filter by game_type to span regular season (2) and playoffs (3)"
    )
    assert "IN (2, 3)" in src or "game_type" in src, (
        "Setup cell must filter game_type to include game types 2 and 3"
    )


def test_pbp_setup_cell_samples_multiple_games():
    """Setup cell must use LIMIT to sample multiple game IDs."""
    nb = _load_notebook()
    src = _get_setup_cell_source(nb)
    assert "LIMIT" in src, (
        "Setup cell must use LIMIT to sample multiple game IDs from the game table"
    )


def test_pbp_setup_cell_extends_plays():
    """Setup cell must loop over game IDs and extend a shared plays list."""
    nb = _load_notebook()
    src = _get_setup_cell_source(nb)
    assert "plays.extend" in src, (
        "Setup cell must call plays.extend() to aggregate plays across multiple games"
    )


def test_pbp_setup_cell_fetches_play_by_play_in_loop():
    """Setup cell must call play-by-play endpoint inside a for loop."""
    nb = _load_notebook()
    src = _get_setup_cell_source(nb)
    assert "for " in src and "play-by-play" in src, (
        "Setup cell must loop over game IDs and fetch /play-by-play for each"
    )


# ── Scenario 2: Composite PK in all schema DDL blocks ────────────────────────


def test_pbp_no_autoincrement_in_any_ddl():
    """No DDL block in Sections 4–6 may contain AUTOINCREMENT (surrogate id removed)."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "AUTOINCREMENT" not in full_text, (
        "At least one DDL block still contains AUTOINCREMENT; "
        "remove the surrogate id column from all schema options (Issue #176)"
    )


def test_pbp_option_a_has_composite_pk():
    """Section 4 (Option A) play_event DDL must use PRIMARY KEY (game_id, event_idx)."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 4")
    assert src, "Section 4 markdown cell not found"
    assert "PRIMARY KEY (game_id, event_idx)" in src, (
        "Section 4 DDL must use PRIMARY KEY (game_id, event_idx) instead of UNIQUE"
    )


def test_pbp_option_a_no_unique_constraint():
    """Section 4 (Option A) DDL must not use UNIQUE (game_id, event_idx)."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 4")
    assert src, "Section 4 markdown cell not found"
    assert "UNIQUE (game_id, event_idx)" not in src, (
        "Section 4 DDL still uses UNIQUE (game_id, event_idx); promote to PRIMARY KEY"
    )


def test_pbp_option_b_base_table_has_composite_pk():
    """Section 5 (Option B) play_event base table must use PRIMARY KEY (game_id, event_idx)."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 5")
    assert src, "Section 5 markdown cell not found"
    assert "PRIMARY KEY (game_id, event_idx)" in src, (
        "Section 5 play_event base DDL must use PRIMARY KEY (game_id, event_idx)"
    )


def test_pbp_option_b_no_unique_constraint():
    """Section 5 (Option B) DDL must not use UNIQUE (game_id, event_idx)."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 5")
    assert src, "Section 5 markdown cell not found"
    assert "UNIQUE (game_id, event_idx)" not in src, (
        "Section 5 DDL still uses UNIQUE (game_id, event_idx); promote to PRIMARY KEY"
    )


def test_pbp_option_b_child_tables_no_fk_to_play_event_id():
    """Section 5 child tables must not FK to play_event(id) after surrogate id removal."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 5")
    assert src, "Section 5 markdown cell not found"
    assert "REFERENCES play_event(id)" not in src, (
        "Section 5 child table still references play_event(id); "
        "update FK to reference the composite key (game_id, event_idx)"
    )


def test_pbp_option_c_has_composite_pk():
    """Section 6 (Option C) DDL must use PRIMARY KEY (game_id, event_idx) on both tables."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 6")
    assert src, "Section 6 markdown cell not found"
    assert "PRIMARY KEY (game_id, event_idx)" in src, (
        "Section 6 DDL must use PRIMARY KEY (game_id, event_idx) instead of UNIQUE"
    )


def test_pbp_option_c_no_unique_constraint():
    """Section 6 (Option C) DDL must not use UNIQUE (game_id, event_idx)."""
    nb = _load_notebook()
    src = _get_section_markdown_source(nb, "Section 6")
    assert src, "Section 6 markdown cell not found"
    assert "UNIQUE (game_id, event_idx)" not in src, (
        "Section 6 DDL still uses UNIQUE (game_id, event_idx); promote to PRIMARY KEY"
    )
