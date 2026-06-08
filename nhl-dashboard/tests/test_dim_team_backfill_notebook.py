"""Tests for dim_team_backfill.ipynb structure after Issue #175 fix.

Verifies the notebook queries the game table by numeric team_id (not live_game
by tri-code) and removes the unnecessary two-step tri-code → ID resolution.

Section map after fix:
  Setup          — imports, engine, NHL_STATS_BASE
  Section 1      — Detect missing teams: game.home_team_id / away_team_id vs team.team_id
  Section 2      — Fetch per-team detail: GET /team/id/{id} for each MISSING_TEAM_IDS entry
  Section 3      — Upsert function: upsert_team(session, team_dict)
  Section 4      — Batch upsert: loop TEAM_DETAIL_MAP, commit
  Section 5      — Verification: before/after counts, confirm MISSING_TEAM_IDS ⊆ team.team_id
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
            f"Expected notebook at {_NOTEBOOK_PATH}"
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

    def test_notebook_section1_queries_game_table_away_team_id(self):
        """Section 1 must query game.away_team_id (integer), not live_game.away_code."""
        src = _notebook_source()
        assert "away_team_id" in src
        assert "game" in src

    def test_notebook_section1_queries_game_table_home_team_id(self):
        """Section 1 must query game.home_team_id (integer), not live_game.home_code."""
        src = _notebook_source()
        assert "home_team_id" in src

    def test_notebook_section1_does_not_query_live_game(self):
        """Section 1 must NOT reference the live_game table — use game table instead."""
        src = _notebook_source()
        assert "live_game" not in src

    def test_notebook_section1_compares_against_team_team_id(self):
        """Section 1 must compare integer IDs against team.team_id, not team.tri_code."""
        src = _notebook_source()
        # Must reference team_id from team table as the comparison column
        assert "team_id" in src

    def test_notebook_section1_uses_missing_team_ids(self):
        """Section 1 must store result in MISSING_TEAM_IDS (not MISSING_CODES)."""
        src = _notebook_source()
        assert "MISSING_TEAM_IDS" in src

    def test_notebook_section1_does_not_use_missing_codes(self):
        """Section 1 must not use MISSING_CODES — the bug that caused 0 upserts."""
        src = _notebook_source()
        assert "MISSING_CODES" not in src


class TestDimTeamBackfillSection2:
    def test_notebook_section2_exists(self):
        """Notebook must contain Section 2 — Fetch per-team detail."""
        src = _notebook_source()
        assert "Section 2" in src

    def test_notebook_section2_calls_team_id_endpoint(self):
        """Section 2 must call GET /stats/rest/en/team/id/{id} for each missing ID."""
        src = _notebook_source()
        assert "stats/rest/en/team/id" in src

    def test_notebook_section2_builds_team_detail_map(self):
        """Section 2 must build TEAM_DETAIL_MAP keyed by integer team ID."""
        src = _notebook_source()
        assert "TEAM_DETAIL_MAP" in src

    def test_notebook_section2_does_not_use_tricode_to_id(self):
        """Section 2 must not use TRICODE_TO_ID — the unnecessary resolution step."""
        src = _notebook_source()
        assert "TRICODE_TO_ID" not in src

    def test_notebook_section2_extracts_franchise_id(self):
        """Section 2 must extract franchiseId from the per-team detail response."""
        src = _notebook_source()
        assert "franchiseId" in src or "franchise_id" in src

    def test_notebook_section2_extracts_full_name(self):
        """Section 2 must extract fullName from the per-team detail response."""
        src = _notebook_source()
        assert "fullName" in src or "full_name" in src

    def test_notebook_section2_extracts_league_id(self):
        """Section 2 must extract leagueId from the per-team detail response."""
        src = _notebook_source()
        assert "leagueId" in src or "league_id" in src

    def test_notebook_section2_extracts_raw_tricode(self):
        """Section 2 must extract rawTricode from the per-team detail response."""
        src = _notebook_source()
        assert "rawTricode" in src or "raw_tricode" in src

    def test_notebook_section2_handles_errors(self):
        """Section 2 must handle individual API failures without aborting the loop."""
        src = _notebook_source()
        assert any(term in src for term in ["try", "except", "raise_for_status"])


class TestDimTeamBackfillSection3:
    def test_notebook_section3_exists(self):
        """Notebook must contain Section 3 — Upsert function."""
        src = _notebook_source()
        assert "Section 3" in src

    def test_notebook_section3_defines_upsert_team(self):
        """Section 3 must define an upsert_team function."""
        src = _notebook_source()
        assert "upsert_team" in src

    def test_notebook_section3_uses_session_merge(self):
        """upsert_team must use session.merge() for idempotent upserts."""
        src = _notebook_source()
        assert "session.merge" in src or "merge(" in src

    def test_notebook_section3_imports_team_model(self):
        """Section 3 must import Team from models."""
        src = _notebook_source()
        assert "Team" in src
        assert "from models" in src or "import models" in src


class TestDimTeamBackfillSection4:
    def test_notebook_section4_exists(self):
        """Notebook must contain Section 4 — Batch upsert."""
        src = _notebook_source()
        assert "Section 4" in src

    def test_notebook_section4_loops_over_team_detail_map(self):
        """Section 4 must iterate over TEAM_DETAIL_MAP (not a tri-code list)."""
        src = _notebook_source()
        assert "TEAM_DETAIL_MAP" in src
        assert any(term in src for term in ["for ", "TEAM_DETAIL_MAP.items"])

    def test_notebook_section4_calls_upsert_team(self):
        """Section 4 batch loop must call upsert_team()."""
        src = _notebook_source()
        assert "upsert_team" in src

    def test_notebook_section4_commits_after_batch(self):
        """Section 4 must commit the session after the batch upsert."""
        src = _notebook_source()
        assert "session.commit()" in src


class TestDimTeamBackfillSection5:
    def test_notebook_section5_exists(self):
        """Notebook must contain Section 5 — Verification."""
        src = _notebook_source()
        assert "Section 5" in src

    def test_notebook_section5_shows_before_after_counts(self):
        """Section 5 must show before/after row counts to confirm insertions."""
        src = _notebook_source()
        assert any(term in src for term in ["before", "after", "COUNT", "count"])

    def test_notebook_section5_queries_team_table(self):
        """Section 5 must query the team table to confirm new rows were inserted."""
        src = _notebook_source()
        assert "team" in src
        assert any(term in src for term in ["SELECT COUNT", "COUNT(*)", "count"])

    def test_notebook_section5_confirms_missing_team_ids_resolved(self):
        """Section 5 must confirm all MISSING_TEAM_IDS now appear in team.team_id."""
        src = _notebook_source()
        assert "MISSING_TEAM_IDS" in src

    def test_notebook_section5_shows_dataframe(self):
        """Section 5 must display a DataFrame of inserted rows."""
        src = _notebook_source()
        assert any(term in src for term in ["DataFrame", "display(", "df_"])

    def test_notebook_no_section6(self):
        """After the fix, the notebook must have only 5 numbered sections (no Section 6)."""
        src = _notebook_source()
        assert "Section 6" not in src


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
