"""Tests for dim_player_backfill.ipynb existence and structure (Issue #165).

Verifies the notebook file exists and contains all required sections and
structural elements defined in the acceptance criteria: Setup, single-team
sample, upsert function, batch fetch for all 32 teams, and verification.
"""
import json
from pathlib import Path

_NOTEBOOK_PATH = (
    Path(__file__).parent.parent / "notebooks" / "dim_player_backfill.ipynb"
)


def _notebook_source() -> str:
    """Return all cell source text from dim_player_backfill.ipynb joined."""
    with open(_NOTEBOOK_PATH) as f:
        nb = json.load(f)
    return "\n".join("".join(cell["source"]) for cell in nb["cells"])


class TestDimPlayerBackfillNotebookExists:
    def test_notebook_file_exists(self):
        """dim_player_backfill.ipynb must exist in the notebooks directory."""
        assert _NOTEBOOK_PATH.exists(), (
            f"Expected notebook at {_NOTEBOOK_PATH} — create it to satisfy Issue #165."
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


class TestDimPlayerBackfillSetup:
    def test_notebook_references_nhl_api_base(self):
        """Notebook must reference the NHL web API base URL."""
        src = _notebook_source()
        assert "api-web.nhle.com" in src

    def test_notebook_references_roster_endpoint(self):
        """Notebook must reference the /v1/roster/{team}/{season} endpoint."""
        src = _notebook_source()
        assert "roster" in src

    def test_notebook_loads_teams_from_db(self):
        """Notebook must load NHL_TEAMS from the team table, not a hardcoded list."""
        src = _notebook_source()
        assert "NHL_TEAMS" in src
        assert "SELECT tri_code FROM team" in src, (
            "Expected DB query 'SELECT tri_code FROM team' — teams must come from the DB, not a hardcoded list"
        )

    def test_notebook_references_sqlalchemy_engine(self):
        """Notebook must connect via SQLAlchemy create_engine (no Flask app context)."""
        src = _notebook_source()
        assert "create_engine" in src

    def test_notebook_references_sqlite_db_path(self):
        """Notebook must reference the Flask app's SQLite database at instance/nhl.db."""
        src = _notebook_source()
        assert "instance" in src and "nhl.db" in src, (
            "Expected DB path 'instance/nhl.db' — the path changed from nhl_dashboard.db"
        )

    def test_notebook_references_eastern_time(self):
        """updated_at must be set to current Eastern time on each upsert."""
        src = _notebook_source()
        assert any(term in src for term in ["Eastern", "eastern", "ET", "US/Eastern", "America/New_York"])

    def test_notebook_references_rate_limiting(self):
        """Notebook must rate-limit API calls at 50 ms between requests."""
        src = _notebook_source()
        assert "time.sleep" in src
        assert any(term in src for term in ["0.05", "50", "rate"])


class TestDimPlayerBackfillSection1:
    def test_notebook_contains_single_team_sample_section(self):
        """Notebook must contain Section 1 — Single team sample."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "Section 1", "Single team sample", "single team", "sample",
            ]
        )

    def test_notebook_section1_queries_team_table(self):
        """Section 1 must query the team table in the DB to build the team list."""
        src = _notebook_source()
        assert "tri_code" in src and "team" in src, (
            "Expected Section 1 to query 'tri_code' from 'team' table in the DB"
        )

    def test_notebook_section1_prints_response_shape(self):
        """Section 1 must print the raw response shape or field inventory."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "keys()", "print", "pprint", "forwards", "defensemen", "goalies",
            ]
        )


class TestDimPlayerBackfillSection2:
    def test_notebook_contains_upsert_function_section(self):
        """Notebook must contain Section 2 — Upsert function definition."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "Section 2", "Upsert function", "upsert", "INSERT OR REPLACE",
            ]
        )

    def test_notebook_defines_upsert_player_function(self):
        """Notebook must define an upsert_player function."""
        src = _notebook_source()
        assert "upsert_player" in src

    def test_notebook_upsert_uses_session_merge_or_insert_replace(self):
        """upsert_player must use session.merge() or INSERT OR REPLACE."""
        src = _notebook_source()
        assert any(
            term in src for term in ["session.merge", "INSERT OR REPLACE", "merge("]
        )

    def test_notebook_upsert_sets_updated_at(self):
        """upsert_player must set updated_at on each call."""
        src = _notebook_source()
        assert "updated_at" in src


class TestDimPlayerBackfillSection3:
    def test_notebook_contains_batch_fetch_section(self):
        """Notebook must contain Section 3 — Batch fetch for all 32 teams."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "Section 3", "Batch fetch", "batch fetch", "all 32", "all teams",
            ]
        )

    def test_notebook_loops_over_all_teams(self):
        """Section 3 must iterate over all teams in NHL_TEAMS."""
        src = _notebook_source()
        assert "NHL_TEAMS" in src
        assert any(term in src for term in ["for team in", "for t in"])

    def test_notebook_fetches_all_seasons_via_roster_season_endpoint(self):
        """Section 4 must iterate over all seasons fetched from roster-season, not a single hardcoded one."""
        src = _notebook_source()
        assert "roster-season" in src, (
            "Expected 'roster-season' endpoint — seasons must come from the API, not hardcoded"
        )

    def test_notebook_handles_http_errors(self):
        """Section 3 must handle HTTP errors and non-200 responses gracefully."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "status_code", "raise_for_status", "except", "try", "failed_teams",
            ]
        )

    def test_notebook_prints_progress_per_team(self):
        """Section 3 must print progress for each team fetched."""
        src = _notebook_source()
        assert "print" in src


class TestDimPlayerBackfillSection4:
    def test_notebook_contains_verification_section(self):
        """Notebook must contain Section 4 — Verification."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "Section 4", "Verification", "verification", "verify",
            ]
        )

    def test_notebook_queries_dim_player_row_count(self):
        """Section 4 must query and print the total row count in dim_player."""
        src = _notebook_source()
        assert "dim_player" in src
        assert any(term in src for term in ["count", "COUNT", "row_count", "len("])

    def test_notebook_shows_position_breakdown(self):
        """Section 4 must show a position breakdown query."""
        src = _notebook_source()
        assert any(term in src for term in ["position", "value_counts", "GROUP BY"])

    def test_notebook_displays_sample_rows(self):
        """Section 4 must display a sample of rows to confirm success."""
        src = _notebook_source()
        assert any(
            term in src for term in ["head(", "sample(", "LIMIT", "limit", "display("]
        )


class TestDimPlayerBackfillColumns:
    def test_notebook_references_player_id(self):
        """Notebook must reference player_id column."""
        assert "player_id" in _notebook_source()

    def test_notebook_references_first_name(self):
        """Notebook must reference first_name column."""
        assert "first_name" in _notebook_source()

    def test_notebook_references_last_name(self):
        """Notebook must reference last_name column."""
        assert "last_name" in _notebook_source()

    def test_notebook_references_sweater_number(self):
        """Notebook must reference sweater_number column."""
        assert "sweater_number" in _notebook_source()

    def test_notebook_references_position(self):
        """Notebook must reference position column."""
        assert "position" in _notebook_source()

    def test_notebook_references_shoots_catches(self):
        """Notebook must reference shoots_catches column."""
        assert "shoots_catches" in _notebook_source()

    def test_notebook_references_height_in_inches(self):
        """Notebook must reference height_in_inches column."""
        assert "height_in_inches" in _notebook_source()

    def test_notebook_references_weight_in_pounds(self):
        """Notebook must reference weight_in_pounds column."""
        assert "weight_in_pounds" in _notebook_source()

    def test_notebook_references_birth_date(self):
        """Notebook must reference birth_date column."""
        assert "birth_date" in _notebook_source()

    def test_notebook_references_birth_country(self):
        """Notebook must reference birth_country column."""
        assert "birth_country" in _notebook_source()

    def test_notebook_references_headshot_url(self):
        """Notebook must reference headshot_url column."""
        assert "headshot_url" in _notebook_source()


class TestDimPlayerBackfillIssue166:
    """Tests for Issue #166: DB-driven teams, full historical seasons."""

    def test_notebook_uses_instance_db_path(self):
        """DB path must point to instance/nhl.db, not nhl_dashboard.db."""
        src = _notebook_source()
        assert "instance" in src
        assert "nhl.db" in src
        assert "nhl_dashboard.db" not in src, (
            "Old DB path nhl_dashboard.db must be removed; use instance/nhl.db"
        )

    def test_notebook_uses_roster_season_endpoint(self):
        """Notebook must call GET /v1/roster-season/{team} to fetch available seasons."""
        src = _notebook_source()
        assert "roster-season" in src, (
            "Expected 'roster-season' endpoint to fetch all available seasons per team"
        )

    def test_notebook_defines_roster_seasons_variable(self):
        """Notebook must define ROSTER_SEASONS dict mapping tri-code to season list."""
        src = _notebook_source()
        assert "ROSTER_SEASONS" in src, (
            "Expected ROSTER_SEASONS dict built from /v1/roster-season/{team} responses"
        )

    def test_notebook_no_hardcoded_season_constant(self):
        """Notebook must not define a hardcoded SEASON = '...' constant."""
        src = _notebook_source()
        assert "SEASON   =" not in src and 'SEASON = "' not in src, (
            "SEASON constant must be removed — seasons come from roster-season API"
        )

    def test_notebook_no_hardcoded_team_list(self):
        """Notebook must not contain a hardcoded list of team abbreviations."""
        src = _notebook_source()
        # Old 32-team hardcoded list had at least 5 abbreviations in a list literal
        hardcoded_count = sum(1 for t in ("ANA", "BOS", "BUF", "CGY", "CAR",
                                          "CHI", "COL", "CBJ", "DAL", "DET")
                              if f'"{t}"' in src)
        assert hardcoded_count < 3, (
            "Found hardcoded team abbreviations — teams must come from the DB query"
        )

    def test_notebook_section4_iterates_over_seasons(self):
        """Section 4 batch loop must iterate over seasons from ROSTER_SEASONS."""
        src = _notebook_source()
        assert "for season in" in src, (
            "Expected 'for season in ...' nested loop over ROSTER_SEASONS seasons"
        )

    def test_notebook_commits_inside_team_loop(self):
        """session.commit() must be called once per team, not once after all teams."""
        src = _notebook_source()
        assert "session.commit()" in src, "Expected session.commit() in batch upsert section"
