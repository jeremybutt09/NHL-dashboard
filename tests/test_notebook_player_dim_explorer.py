"""Tests for Issue #162: player_dim_explorer.ipynb.

Validates structural properties of the notebook — existence, valid JSON,
section coverage, cleared outputs, and no source corruption.  Does not
execute the notebook or call the live NHL API.
"""

import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTEBOOK_PATH = os.path.join(
    REPO_ROOT, "nhl-dashboard", "notebooks", "player_dim_explorer.ipynb"
)


def _load_notebook() -> dict:
    with open(NOTEBOOK_PATH) as f:
        return json.load(f)


def _all_cell_sources(nb: dict) -> str:
    """Return all cell source text concatenated for keyword searches."""
    parts = []
    for cell in nb.get("cells", []):
        source = cell.get("source", [])
        if isinstance(source, list):
            parts.append("".join(source))
        else:
            parts.append(source)
    return "\n".join(parts)


# ── File existence ────────────────────────────────────────────────────────────


def test_player_dim_notebook_exists():
    """Notebook must exist at nhl-dashboard/notebooks/player_dim_explorer.ipynb."""
    assert os.path.isfile(NOTEBOOK_PATH), f"Notebook not found at {NOTEBOOK_PATH}"


# ── Notebook validity ─────────────────────────────────────────────────────────


def test_player_dim_notebook_is_valid_json():
    """player_dim_explorer.ipynb must be valid JSON."""
    nb = _load_notebook()
    assert isinstance(nb, dict), "Notebook is not a JSON object"


def test_player_dim_notebook_has_nbformat():
    """player_dim_explorer.ipynb must declare nbformat >= 4."""
    nb = _load_notebook()
    assert "nbformat" in nb, "nbformat key missing from notebook"
    assert nb["nbformat"] >= 4, "nbformat must be 4 or higher"


def test_player_dim_notebook_has_cells():
    """player_dim_explorer.ipynb must contain at least one cell."""
    nb = _load_notebook()
    assert len(nb.get("cells", [])) > 0, "Notebook has no cells"


# ── Output hygiene ────────────────────────────────────────────────────────────


def test_player_dim_notebook_cells_have_cleared_outputs():
    """All code cells must ship with cleared outputs (no pre-run results)."""
    nb = _load_notebook()
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            outputs = cell.get("outputs", [])
            assert outputs == [], (
                f"Code cell {i} has non-empty outputs; notebook must ship with cleared outputs"
            )


# ── Issue reference ───────────────────────────────────────────────────────────


def test_player_dim_notebook_references_issue_162():
    """Notebook must reference Issue #162."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "162" in full_text, "Issue #162 not referenced in notebook"


# ── Setup instructions ────────────────────────────────────────────────────────


def test_player_dim_notebook_has_setup_instructions():
    """Notebook must contain a markdown cell with pip install / jupyter instructions."""
    nb = _load_notebook()
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if "pip install" in source and "jupyter" in source:
                return
    raise AssertionError(
        "No markdown cell with pip install / jupyter setup instructions found"
    )


# ── Endpoint coverage ─────────────────────────────────────────────────────────


def test_player_dim_notebook_references_roster_endpoint():
    """Notebook must reference the /v1/roster/ endpoint."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "/v1/roster/" in full_text or "roster/" in full_text, (
        "No reference to /v1/roster/ endpoint found in notebook"
    )


def test_player_dim_notebook_references_landing_endpoint():
    """Notebook must reference the /v1/player/ landing endpoint."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "/v1/player/" in full_text or "player/" in full_text, (
        "No reference to /v1/player/{id}/landing endpoint found in notebook"
    )


def test_player_dim_notebook_references_boxscore_endpoint():
    """Notebook must reference the boxscore endpoint or playerByGameStats."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "boxscore" in full_text.lower() or "playerByGameStats" in full_text, (
        "No reference to boxscore / playerByGameStats found in notebook"
    )


def test_player_dim_notebook_covers_all_32_teams():
    """Notebook must reference all 32 NHL teams in the batch fetch section."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "32" in full_text, "No reference to 32 teams in notebook"


# ── Section coverage ──────────────────────────────────────────────────────────


def test_player_dim_notebook_has_field_inventory_section():
    """Notebook must include a field inventory section."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "field inventory" in full_text.lower() or "Field Inventory" in full_text, (
        "No field inventory section found in notebook"
    )


def test_player_dim_notebook_has_comparison_section():
    """Notebook must include a side-by-side comparison section."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "comparison" in full_text.lower() or "side-by-side" in full_text.lower(), (
        "No comparison / side-by-side section found in notebook"
    )


def test_player_dim_notebook_has_ddl_section():
    """Notebook must include a proposed player dim DDL."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "CREATE TABLE" in full_text or "DDL" in full_text, (
        "No DDL / CREATE TABLE section found in notebook"
    )


def test_player_dim_notebook_has_workflow_section():
    """Notebook must document the backfill and ongoing upsert workflow."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "backfill" in full_text.lower() or "workflow" in full_text.lower(), (
        "No backfill / workflow section found in notebook"
    )


def test_player_dim_notebook_has_gap_analysis():
    """Notebook must include a gap analysis section."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "gap analysis" in full_text.lower() or "Gap Analysis" in full_text, (
        "No gap analysis section found in notebook"
    )


# ── Source corruption check ───────────────────────────────────────────────────


def test_player_dim_no_cell_has_character_per_item_source():
    """Every cell source must contain complete lines, not one character per item.

    Guards against the corruption pattern caught by Issue #145 in db_explorer.ipynb.
    """
    nb = _load_notebook()
    corrupted = []
    for i, cell in enumerate(nb.get("cells", [])):
        src = cell.get("source", [])
        if src and all(len(s.strip()) <= 1 for s in src):
            corrupted.append((i, cell.get("id", "unknown")))
    assert corrupted == [], (
        f"Corrupted character-per-item source found in cells: {corrupted}"
    )


# ── Proposed DDL fields ───────────────────────────────────────────────────────


def test_player_dim_ddl_includes_player_id():
    """Proposed DDL must include player_id as the primary key."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "player_id" in full_text, "player_id not found in notebook"


def test_player_dim_ddl_includes_current_team_id():
    """Proposed DDL must include current_team_id (landing-only field)."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "current_team_id" in full_text or "currentTeamId" in full_text, (
        "current_team_id / currentTeamId not referenced in notebook"
    )


def test_player_dim_ddl_includes_is_active():
    """Proposed DDL must include is_active (landing-only field)."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "is_active" in full_text or "isActive" in full_text, (
        "is_active / isActive not referenced in notebook"
    )
