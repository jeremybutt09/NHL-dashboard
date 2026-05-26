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


# ── Issue #110: pathlib-based DB_PATH ─────────────────────────────────────────

def test_notebook_db_path_uses_pathlib():
    """First code cell must import Path from pathlib and use it to derive DB_PATH.

    A plain string literal like DB_PATH = "nhl-dashboard/..." fails when Jupyter's
    cwd is the notebook directory rather than the repo root (Issue #110).
    """
    nb = _load_notebook()
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    assert code_cells, "No code cells found in notebook"
    first_source = "".join(code_cells[0].get("source", []))
    assert "pathlib" in first_source, (
        "First code cell must import pathlib to derive DB_PATH (Issue #110)"
    )
    assert "Path" in first_source, (
        "First code cell must use Path() to resolve DB_PATH (Issue #110)"
    )


def test_notebook_db_path_defined_only_in_first_code_cell():
    """DB_PATH must be assigned exactly once, in the first code cell.

    Repeating DB_PATH = '...' in every cell forces a repo-root launch dir (Issue #110).
    Defining it once in Section 1 and referencing it in subsequent cells fixes this.
    """
    nb = _load_notebook()
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    definitions = []
    for i, cell in enumerate(code_cells):
        source = "".join(cell.get("source", []))
        if "DB_PATH" in source and "=" in source:
            # Count assignment lines (not just references like conn = sqlite3.connect(DB_PATH))
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith("DB_PATH") and "=" in stripped and "==" not in stripped:
                    definitions.append(i)
                    break
    assert len(definitions) == 1, (
        f"DB_PATH is assigned in {len(definitions)} code cell(s) (at cell indices {definitions}); "
        "it must be assigned exactly once, in the first code cell only (Issue #110)"
    )
    assert definitions[0] == 0, (
        f"DB_PATH assignment found in code cell index {definitions[0]}, expected cell index 0"
    )


# ── Issue #128: Section 3 — last 10 games instead of today's games ────────────


def _get_section3_cells(nb: dict):
    """Return (markdown_cell, code_cell) for Section 3 (not 3.5)."""
    cells = nb.get("cells", [])
    for i, cell in enumerate(cells):
        source = "".join(cell.get("source", []))
        if "Section 3 —" in source and cell.get("cell_type") == "markdown":
            for j in range(i + 1, len(cells)):
                if cells[j].get("cell_type") == "code":
                    return cell, cells[j]
    return None, None


def test_section3_markdown_mentions_last_10_games():
    """Section 3 markdown cell must describe 'last 10 games', not today's slate."""
    nb = _load_notebook()
    md_cell, _ = _get_section3_cells(nb)
    assert md_cell is not None, "Section 3 markdown cell not found"
    source = "".join(md_cell.get("source", []))
    assert "last 10" in source.lower(), (
        "Section 3 markdown must mention 'last 10 games' (Issue #128)"
    )


def test_section3_code_print_says_last_10_games():
    """Section 3 code cell must print 'Last 10 games:' not 'Games today:'."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "Last 10 games:" in source, (
        "Section 3 must use 'Last 10 games:' print label (Issue #128)"
    )


def test_section3_code_has_no_games_today_label():
    """Section 3 code cell must not use 'Games today:' print label."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "Games today:" not in source, (
        "Section 3 'Games today:' label must be replaced with 'Last 10 games:' (Issue #128)"
    )


def test_section3_code_uses_order_by_game_date_desc():
    """Section 3 code SQL must use ORDER BY game_date DESC (game table has no start_est)."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "game_date DESC" in source, (
        "Section 3 SQL must ORDER BY game_date DESC — game table has game_date not start_est (Issue #142)"
    )


# ── Issue #142: Section 3 must use SELECT * and correct column references ──────


def test_section3_code_uses_select_star():
    """Section 3 code SQL must use SELECT * to avoid referencing dropped columns."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "SELECT *" in source, (
        "Section 3 SQL must use SELECT * instead of a named column list (Issue #142)"
    )


def test_section3_code_does_not_reference_away_code():
    """Section 3 code must not reference away_code — column does not exist in game table."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "away_code" not in source, (
        "Section 3 still references away_code — game table has no such column; "
        "use visiting_team_id instead (Issue #142)"
    )


def test_section3_code_does_not_reference_home_code():
    """Section 3 code must not reference home_code — column does not exist in game table."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "home_code" not in source, (
        "Section 3 still references home_code — game table has no such column; "
        "use home_team_id instead (Issue #142)"
    )


def test_section3_code_uses_limit_10():
    """Section 3 code SQL must include LIMIT 10."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "LIMIT 10" in source, (
        "Section 3 SQL must include LIMIT 10 (Issue #128)"
    )


def test_section3_code_has_no_today_date_filter():
    """Section 3 code must not filter games by today's date."""
    nb = _load_notebook()
    _, code_cell = _get_section3_cells(nb)
    assert code_cell is not None, "Section 3 code cell not found"
    source = "".join(code_cell.get("source", []))
    assert "LIKE :today" not in source, (
        "Section 3 must not filter by today's date — show last 10 regardless (Issue #128)"
    )


# ── Issue #139: EXPECTED_TABLES must reflect current schema ──────────────────

def _get_section1_code_source(nb: dict) -> str:
    """Return the source of the first code cell (Section 1 setup cell)."""
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            return "".join(cell.get("source", []))
    return ""


def _get_section6_code_source(nb: dict) -> str:
    """Return the source of the Section 6 pipeline-check code cell."""
    cells = nb.get("cells", [])
    for i, cell in enumerate(cells):
        source = "".join(cell.get("source", []))
        if "Section 6" in source and cell.get("cell_type") == "markdown":
            for j in range(i + 1, len(cells)):
                if cells[j].get("cell_type") == "code":
                    return "".join(cells[j].get("source", []))
    return ""


def test_section1_expected_tables_excludes_nhl_historical_game():
    """Section 1 EXPECTED_TABLES must not include nhl_historical_game (renamed to game in #131)."""
    nb = _load_notebook()
    src = _get_section1_code_source(nb)
    assert "EXPECTED_TABLES" in src, "EXPECTED_TABLES not found in Section 1"
    # Extract the set literal — look for nhl_historical_game appearing inside EXPECTED_TABLES
    assert '"nhl_historical_game"' not in src and "'nhl_historical_game'" not in src, (
        "Section 1 EXPECTED_TABLES still contains nhl_historical_game — "
        "replace with game, boxscore, dashboard_game (Issue #139)"
    )


def test_section1_expected_tables_includes_boxscore():
    """Section 1 EXPECTED_TABLES must include boxscore (Issue #139)."""
    nb = _load_notebook()
    src = _get_section1_code_source(nb)
    assert '"boxscore"' in src or "'boxscore'" in src, (
        "Section 1 EXPECTED_TABLES must include boxscore (Issue #139)"
    )


def test_section1_expected_tables_includes_dashboard_game():
    """Section 1 EXPECTED_TABLES must include dashboard_game (Issue #139)."""
    nb = _load_notebook()
    src = _get_section1_code_source(nb)
    assert '"dashboard_game"' in src or "'dashboard_game'" in src, (
        "Section 1 EXPECTED_TABLES must include dashboard_game (Issue #139)"
    )


def test_section6_expected_tables_excludes_nhl_historical_game():
    """Section 6 EXPECTED_TABLES must not include nhl_historical_game (Issue #139)."""
    nb = _load_notebook()
    src = _get_section6_code_source(nb)
    assert "EXPECTED_TABLES" in src, "EXPECTED_TABLES not found in Section 6"
    assert '"nhl_historical_game"' not in src and "'nhl_historical_game'" not in src, (
        "Section 6 EXPECTED_TABLES still contains nhl_historical_game (Issue #139)"
    )


def test_section6_expected_tables_includes_boxscore():
    """Section 6 EXPECTED_TABLES must include boxscore (Issue #139)."""
    nb = _load_notebook()
    src = _get_section6_code_source(nb)
    assert '"boxscore"' in src or "'boxscore'" in src, (
        "Section 6 EXPECTED_TABLES must include boxscore (Issue #139)"
    )


def test_section6_expected_tables_includes_dashboard_game():
    """Section 6 EXPECTED_TABLES must include dashboard_game (Issue #139)."""
    nb = _load_notebook()
    src = _get_section6_code_source(nb)
    assert '"dashboard_game"' in src or "'dashboard_game'" in src, (
        "Section 6 EXPECTED_TABLES must include dashboard_game (Issue #139)"
    )


def test_notebook_has_boxscore_section():
    """Notebook must include a dedicated explorer section for the boxscore table (Issue #139)."""
    nb = _load_notebook()
    full_text = _all_cell_sources(nb)
    assert "boxscore" in full_text.lower(), "No boxscore section found in notebook (Issue #139)"
    # Must have a markdown header for it
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if "boxscore" in source.lower() and (
                "##" in source or "Section" in source
            ):
                return
    raise AssertionError(
        "No markdown section header for boxscore table found in notebook (Issue #139)"
    )


def test_notebook_has_dashboard_game_section():
    """Notebook must include a dedicated explorer section for the dashboard_game table (Issue #139)."""
    nb = _load_notebook()
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if "dashboard_game" in source.lower() and (
                "##" in source or "Section" in source
            ):
                return
    raise AssertionError(
        "No markdown section header for dashboard_game table found in notebook (Issue #139)"
    )


def test_notebook_section7_queries_game_not_nhl_historical_game():
    """Section 7 must query the `game` table, not nhl_historical_game (Issue #139)."""
    nb = _load_notebook()
    cells = nb.get("cells", [])
    in_section7 = False
    for cell in cells:
        source = "".join(cell.get("source", []))
        if "Section 7" in source:
            in_section7 = True
        if in_section7 and cell.get("cell_type") == "code":
            assert "nhl_historical_game" not in source, (
                "Section 7 code cell still references nhl_historical_game — "
                "update to use game table (Issue #139)"
            )
        # Stop after Section 7's cells (when next section starts)
        if in_section7 and cell.get("cell_type") == "markdown" and "Section 8" in source:
            break


# ── Issue #141: Section 2b team-to-game join must use team_id ────────────────


def _get_section2b_code_source(nb: dict) -> str:
    """Return source of the code cell immediately following the Section 2b markdown header."""
    cells = nb.get("cells", [])
    for i, cell in enumerate(cells):
        source = "".join(cell.get("source", []))
        if "Section 2b" in source and cell.get("cell_type") == "markdown":
            for j in range(i + 1, len(cells)):
                if cells[j].get("cell_type") == "code":
                    return "".join(cells[j].get("source", []))
    return ""


def test_section2b_join_uses_visiting_team_id():
    """Section 2b JOIN must reference visiting_team_id, not away_code (Issue #141)."""
    nb = _load_notebook()
    src = _get_section2b_code_source(nb)
    assert src, "Section 2b code cell not found"
    assert "visiting_team_id" in src, (
        "Section 2b JOIN must use g.visiting_team_id (Issue #141)"
    )


def test_section2b_join_uses_home_team_id():
    """Section 2b JOIN must reference home_team_id, not home_code (Issue #141)."""
    nb = _load_notebook()
    src = _get_section2b_code_source(nb)
    assert src, "Section 2b code cell not found"
    assert "home_team_id" in src, (
        "Section 2b JOIN must use g.home_team_id (Issue #141)"
    )


def test_section2b_join_uses_team_id_column():
    """Section 2b JOIN must join on team.team_id, not team.tri_code (Issue #141)."""
    nb = _load_notebook()
    src = _get_section2b_code_source(nb)
    assert src, "Section 2b code cell not found"
    assert "t_away.team_id" in src and "t_home.team_id" in src, (
        "Section 2b JOIN must use t_away.team_id and t_home.team_id (Issue #141)"
    )


def test_section2b_join_does_not_use_away_code():
    """Section 2b JOIN must not reference the non-existent away_code column (Issue #141)."""
    nb = _load_notebook()
    src = _get_section2b_code_source(nb)
    assert src, "Section 2b code cell not found"
    assert "away_code" not in src, (
        "Section 2b JOIN still references away_code — game table has no such column (Issue #141)"
    )


def test_section2b_join_does_not_use_home_code():
    """Section 2b JOIN must not reference the non-existent home_code column (Issue #141)."""
    nb = _load_notebook()
    src = _get_section2b_code_source(nb)
    assert src, "Section 2b code cell not found"
    assert "home_code" not in src, (
        "Section 2b JOIN still references home_code — game table has no such column (Issue #141)"
    )


# ── Issue #143: Section 8a must use SELECT * and filter out FUT game state ─────


def _get_section8a_code_source(nb: dict) -> str:
    """Return source of the code cell immediately following the Section 8a markdown header."""
    cells = nb.get("cells", [])
    for i, cell in enumerate(cells):
        source = "".join(cell.get("source", []))
        if "8a" in source and cell.get("cell_type") == "markdown":
            for j in range(i + 1, len(cells)):
                if cells[j].get("cell_type") == "code":
                    return "".join(cells[j].get("source", []))
    return ""


def test_section8a_uses_select_star():
    """Section 8a code SQL must use SELECT * to avoid breaking on schema changes."""
    nb = _load_notebook()
    src = _get_section8a_code_source(nb)
    assert src, "Section 8a code cell not found"
    assert "SELECT *" in src, (
        "Section 8a SQL must use SELECT * instead of a named column list (Issue #143)"
    )


def test_section8a_filters_out_fut_game_state():
    """Section 8a code SQL must filter out FUT rows so only completed/live games are shown."""
    nb = _load_notebook()
    src = _get_section8a_code_source(nb)
    assert src, "Section 8a code cell not found"
    assert "!= 'FUT'" in src or "<> 'FUT'" in src, (
        "Section 8a SQL must filter out game_state = 'FUT' rows (Issue #143)"
    )


def test_section8a_does_not_use_explicit_column_list():
    """Section 8a code cell must not use the old explicit column list."""
    nb = _load_notebook()
    src = _get_section8a_code_source(nb)
    assert src, "Section 8a code cell not found"
    assert "away_sog, home_sog," not in src, (
        "Section 8a still uses explicit column list — replace with SELECT * (Issue #143)"
    )
