"""Tests for dim_team_backfill.ipynb existence and structure (Issue #173).

Verifies the notebook file exists and contains all required sections and
structural elements defined in the acceptance criteria: Setup, detect missing
teams, resolve team IDs, fetch per-team detail, upsert function, batch upsert,
and verification with before/after row counts.
"""
import json
from pathlib import Path

_NOTEBOOK_PATH = (
    Path(__file__).parent.parent / "notebooks" / "dim_team_backfill.ipynb"
)


def _notebook_source() -> str:
    """Return all cell source text from dim_team_backfill.ipynb joined."""
    with open(_NOTEBOOK_PATH) as f:
        nb = json.load(f)
    return "\n".join("".join(cell["source"]) for cell in nb["cells"])


class TestDimTeamBackfillNotebookExists:
    def test_notebook_file_exists(self):
        """dim_team_backfill.ipynb must exist in the notebooks directory."""
        assert _NOTEBOOK_PATH.exists(), (
            f"Expected notebook at {_NOTEBOOK_PATH} — create it to satisfy Issue #173."
        )

    def test_notebook_is_valid_json_with_cells(self):
        """Notebook must parse as valid Jupyter JSON with a cells array."""
        with open(_NOTEBOOK_PATH) as f:
            nb = json.load(f)
        assert "cells" in nb
        assert len(nb["cells"]) > 0

    def test_notebook_has_markdown_and_code_cells(self):
        """Notebook must contain both markdown and code cells."""
        with open(_NOTEBOOK_PATH) as f:
            nb = json.load(f)
        cell_types = {cell["cell_type"] for cell in nb["cells"]}
        assert "markdown" in cell_types
        assert "code" in cell_types


class TestDimTeamBackfillSetup:
    def test_notebook_references_nhl_stats_api(self):
        """Notebook must reference the NHL Stats REST API base URL."""
        src = _notebook_source()
        assert "api.nhle.com/stats/rest" in src

    def test_notebook_references_sqlalchemy_engine(self):
        """Notebook must connect via SQLAlchemy create_engine (no Flask app context)."""
        src = _notebook_source()
        assert "create_engine" in src

    def test_notebook_references_sqlite_db_path(self):
        """Notebook must reference the Flask app's SQLite database at instance/nhl.db."""
        src = _notebook_source()
        assert "instance" in src and "nhl.db" in src

    def test_notebook_references_httpx(self):
        """Notebook must use httpx for HTTP calls."""
        src = _notebook_source()
        assert "httpx" in src

    def test_notebook_references_rate_limiting(self):
        """Notebook must rate-limit API calls at 50 ms between requests."""
        src = _notebook_source()
        assert "time.sleep" in src
        assert any(term in src for term in ["0.05", "50 ms", "50ms"])


class TestDimTeamBackfillSection1:
    def test_notebook_section1_exists(self):
        """Notebook must contain Section 1 — Detect missing teams."""
        src = _notebook_source()
        assert "Section 1" in src

    def test_notebook_section1_queries_live_game_away_code(self):
        """Section 1 must query live_game.away_code to detect missing teams."""
        src = _notebook_source()
        assert "away_code" in src
        assert "live_game" in src

    def test_notebook_section1_queries_live_game_home_code(self):
        """Section 1 must query live_game.home_code to detect missing teams."""
        src = _notebook_source()
        assert "home_code" in src

    def test_notebook_section1_subtracts_existing_teams(self):
        """Section 1 must subtract tri-codes already present in the team table."""
        src = _notebook_source()
        assert "team" in src
        assert any(term in src for term in ["tri_code", "SELECT tri_code"])

    def test_notebook_section1_identifies_missing_codes(self):
        """Section 1 must build a list/set of missing tri-codes."""
        src = _notebook_source()
        assert any(term in src for term in ["missing", "MISSING"])


class TestDimTeamBackfillSection2:
    def test_notebook_section2_exists(self):
        """Notebook must contain Section 2 — Resolve team IDs."""
        src = _notebook_source()
        assert "Section 2" in src

    def test_notebook_section2_calls_team_list_endpoint(self):
        """Section 2 must call GET /stats/rest/en/team to get the full team list."""
        src = _notebook_source()
        assert "stats/rest/en/team" in src

    def test_notebook_section2_builds_tricode_to_id_map(self):
        """Section 2 must build a triCode → id lookup map."""
        src = _notebook_source()
        assert any(term in src for term in ["triCode", "tri_code"])
        assert any(term in src for term in ["lookup", "map", "tricode_to_id", "id_map", "TEAM_ID"])


class TestDimTeamBackfillSection3:
    def test_notebook_section3_exists(self):
        """Notebook must contain Section 3 — Fetch per-team detail."""
        src = _notebook_source()
        assert "Section 3" in src

    def test_notebook_section3_calls_team_id_endpoint(self):
        """Section 3 must call GET /stats/rest/en/team/id/{id} for each missing team."""
        src = _notebook_source()
        assert "stats/rest/en/team/id" in src

    def test_notebook_section3_extracts_franchise_id(self):
        """Section 3 must extract franchiseId from the per-team detail response."""
        src = _notebook_source()
        assert "franchiseId" in src or "franchise_id" in src

    def test_notebook_section3_extracts_full_name(self):
        """Section 3 must extract fullName from the per-team detail response."""
        src = _notebook_source()
        assert "fullName" in src or "full_name" in src

    def test_notebook_section3_extracts_league_id(self):
        """Section 3 must extract leagueId from the per-team detail response."""
        src = _notebook_source()
        assert "leagueId" in src or "league_id" in src

    def test_notebook_section3_extracts_raw_tricode(self):
        """Section 3 must extract rawTricode from the per-team detail response."""
        src = _notebook_source()
        assert "rawTricode" in src or "raw_tricode" in src


class TestDimTeamBackfillSection4:
    def test_notebook_section4_exists(self):
        """Notebook must contain Section 4 — Upsert function."""
        src = _notebook_source()
        assert "Section 4" in src

    def test_notebook_section4_defines_upsert_team(self):
        """Section 4 must define an upsert_team function."""
        src = _notebook_source()
        assert "upsert_team" in src

    def test_notebook_section4_uses_session_merge(self):
        """upsert_team must use session.merge() for idempotent upserts."""
        src = _notebook_source()
        assert "session.merge" in src or "merge(" in src

    def test_notebook_section4_imports_team_model(self):
        """Section 4 must import Team from models."""
        src = _notebook_source()
        assert "Team" in src
        assert "from models" in src or "import models" in src


class TestDimTeamBackfillSection5:
    def test_notebook_section5_exists(self):
        """Notebook must contain Section 5 — Batch upsert."""
        src = _notebook_source()
        assert "Section 5" in src

    def test_notebook_section5_loops_over_missing_teams(self):
        """Section 5 must iterate over the missing tri-code list."""
        src = _notebook_source()
        assert any(
            term in src for term in ["for tri_code in", "for code in", "for team in"]
        )

    def test_notebook_section5_calls_upsert_team(self):
        """Section 5 batch loop must call upsert_team()."""
        src = _notebook_source()
        assert "upsert_team" in src

    def test_notebook_section5_commits_after_batch(self):
        """Section 5 must commit the session after the batch upsert."""
        src = _notebook_source()
        assert "session.commit()" in src

    def test_notebook_section5_has_rate_limiting(self):
        """Section 5 must rate-limit API requests at 50 ms."""
        src = _notebook_source()
        assert "time.sleep" in src

    def test_notebook_section5_handles_errors(self):
        """Section 5 must handle individual API failures without aborting the loop."""
        src = _notebook_source()
        assert any(term in src for term in ["try", "except", "raise_for_status"])


class TestDimTeamBackfillSection6:
    def test_notebook_section6_exists(self):
        """Notebook must contain Section 6 — Verification."""
        src = _notebook_source()
        assert "Section 6" in src

    def test_notebook_section6_shows_before_after_counts(self):
        """Section 6 must show before/after row counts to confirm insertions."""
        src = _notebook_source()
        assert any(term in src for term in ["before", "after", "COUNT", "count"])

    def test_notebook_section6_queries_team_table(self):
        """Section 6 must query the team table to confirm new rows were inserted."""
        src = _notebook_source()
        assert "team" in src
        assert any(term in src for term in ["SELECT COUNT", "COUNT(*)", "count"])

    def test_notebook_section6_shows_sample_rows(self):
        """Section 6 must display a sample of newly inserted rows."""
        src = _notebook_source()
        assert any(term in src for term in ["LIMIT", "head(", "display(", "sample("])

    def test_notebook_section6_shows_dataframe(self):
        """Section 6 must display a DataFrame of inserted rows."""
        src = _notebook_source()
        assert any(term in src for term in ["DataFrame", "display(", "df_"])


class TestDimTeamBackfillColumns:
    def test_notebook_references_tri_code(self):
        """Notebook must reference tri_code column."""
        assert "tri_code" in _notebook_source()

    def test_notebook_references_team_id(self):
        """Notebook must reference team_id column."""
        assert "team_id" in _notebook_source()

    def test_notebook_references_franchise_id(self):
        """Notebook must reference franchise_id column."""
        assert "franchise_id" in _notebook_source()

    def test_notebook_references_full_name(self):
        """Notebook must reference full_name column."""
        assert "full_name" in _notebook_source()

    def test_notebook_references_league_id(self):
        """Notebook must reference league_id column."""
        assert "league_id" in _notebook_source()

    def test_notebook_references_raw_tricode(self):
        """Notebook must reference raw_tricode column."""
        assert "raw_tricode" in _notebook_source()
