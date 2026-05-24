"""Tests for Issue #108: Jupyter notebook for interactive database exploration."""

import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTEBOOK_PATH = os.path.join(
    REPO_ROOT, "nhl-dashboard", "notebooks", "db_explorer.ipynb"
)
REQUIREMENTS_PATH = os.path.join(
    REPO_ROOT, "nhl-dashboard", "notebooks", "requirements.txt"
)
GITIGNORE_PATH = os.path.join(REPO_ROOT, ".gitignore")


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


def _load_gitignore() -> list[str]:
    with open(GITIGNORE_PATH) as f:
        return [line.strip() for line in f.read().splitlines()]


# ── File existence ────────────────────────────────────────────────────────────

def test_notebook_exists():
    """Notebook must exist at nhl-dashboard/notebooks/db_explorer.ipynb."""
    assert os.path.isfile(NOTEBOOK_PATH), (
        f"Notebook not found at {NOTEBOOK_PATH}"
    )


def test_notebook_requirements_exists():
    """requirements.txt must exist at nhl-dashboard/notebooks/requirements.txt."""
    assert os.path.isfile(REQUIREMENTS_PATH), (
        f"requirements.txt not found at {REQUIREMENTS_PATH}"
    )


# ── requirements.txt content ──────────────────────────────────────────────────

def test_notebook_requirements_contains_jupyter():
    """notebooks/requirements.txt must list jupyter."""
    with open(REQUIREMENTS_PATH) as f:
        content = f.read()
    assert "jupyter" in content, "jupyter missing from notebooks/requirements.txt"


def test_notebook_requirements_contains_pandas():
    """notebooks/requirements.txt must list pandas."""
    with open(REQUIREMENTS_PATH) as f:
        content = f.read()
    assert "pandas" in content, "pandas missing from notebooks/requirements.txt"


def test_notebook_requirements_contains_matplotlib():
    """notebooks/requirements.txt must list matplotlib."""
    with open(REQUIREMENTS_PATH) as f:
        content = f.read()
    assert "matplotlib" in content, "matplotlib missing from notebooks/requirements.txt"


# ── .gitignore ────────────────────────────────────────────────────────────────

def test_gitignore_has_ipynb_checkpoints():
    """Root .gitignore must ignore Jupyter checkpoint directories."""
    lines = _load_gitignore()
    # Accepts the broad pattern or the specific notebooks path
    covered = any(".ipynb_checkpoints" in line for line in lines)
    assert covered, ".ipynb_checkpoints pattern missing from root .gitignore"


# ── Notebook validity ─────────────────────────────────────────────────────────

def test_notebook_is_valid_json():
    """db_explorer.ipynb must be valid JSON."""
    nb = _load_notebook()
    assert isinstance(nb, dict), "Notebook is not a JSON object"


def test_notebook_has_nbformat():
    """db_explorer.ipynb must declare nbformat (valid Jupyter notebook)."""
    nb = _load_notebook()
    assert "nbformat" in nb, "nbformat key missing from notebook"
    assert nb["nbformat"] >= 4, "nbformat must be 4 or higher"


def test_notebook_has_cells():
    """db_explorer.ipynb must contain at least one cell."""
    nb = _load_notebook()
    assert len(nb.get("cells", [])) > 0, "Notebook has no cells"


# ── Section coverage ──────────────────────────────────────────────────────────

def test_notebook_has_section_1_connection():
    """Notebook must include a Section 1 covering Connection & Setup."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "Section 1" in full_text or "Connection" in full_text, (
        "Section 1 (Connection & Setup) not found in notebook"
    )


def test_notebook_has_section_2_team():
    """Notebook must include a Section 2 covering the team table."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "Section 2" in full_text or "team" in full_text.lower(), (
        "Section 2 (team table) not found in notebook"
    )


def test_notebook_has_section_3_game():
    """Notebook must include a Section 3 covering the game table."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "Section 3" in full_text or "game" in full_text.lower(), (
        "Section 3 (game table) not found in notebook"
    )


def test_notebook_has_section_4_odds_snapshot():
    """Notebook must include a Section 4 covering odds_snapshot."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "Section 4" in full_text or "odds_snapshot" in full_text, (
        "Section 4 (odds_snapshot) not found in notebook"
    )


def test_notebook_has_section_5_model_fair():
    """Notebook must include a Section 5 covering model_fair."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "Section 5" in full_text or "model_fair" in full_text, (
        "Section 5 (model_fair) not found in notebook"
    )


def test_notebook_has_section_6_pipeline_check():
    """Notebook must include a Section 6 with an end-to-end pipeline check."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "Section 6" in full_text or "pipeline" in full_text.lower(), (
        "Section 6 (pipeline check) not found in notebook"
    )


# ── Output hygiene ────────────────────────────────────────────────────────────

def test_notebook_cells_have_cleared_outputs():
    """All code cells must ship with cleared outputs (no pre-run results)."""
    nb = _load_notebook()
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            outputs = cell.get("outputs", [])
            assert outputs == [], (
                f"Code cell {i} has non-empty outputs; notebook must ship with cleared outputs"
            )


# ── Issue #106 reference ──────────────────────────────────────────────────────

def test_notebook_references_issue_106():
    """Notebook must reference Issue #106 near the implied probability scale check."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "106" in full_text, (
        "Issue #106 not referenced in notebook; scale check cell must mention it"
    )


# ── Setup instructions ────────────────────────────────────────────────────────

def test_notebook_has_setup_instructions():
    """Notebook must contain a markdown cell with pip install / jupyter notebook instructions."""
    nb = _load_notebook()
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if "pip install" in source and "jupyter" in source:
                return
    raise AssertionError(
        "No markdown cell with pip install / jupyter setup instructions found"
    )


# ── DB connection path ────────────────────────────────────────────────────────

def test_notebook_connects_via_relative_path():
    """Notebook must connect to the DB via a relative path (not an absolute path)."""
    nb = _load_notebook()
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if "nhl.db" in source or "instance" in source:
                # Must not contain a hardcoded absolute path starting with /Users
                assert "/Users/" not in source, (
                    "Notebook uses a hardcoded absolute path; use a relative path instead"
                )
                return
    raise AssertionError("No code cell connecting to nhl.db found in notebook")
