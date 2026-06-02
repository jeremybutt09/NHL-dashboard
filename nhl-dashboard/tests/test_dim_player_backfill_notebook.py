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

    def test_notebook_defines_32_teams(self):
        """Notebook must define all 32 NHL team abbreviations."""
        src = _notebook_source()
        assert "NHL_TEAMS" in src
        # Spot-check a sample of the 32 teams
        for team in ("TOR", "EDM", "BOS", "NYR", "MTL"):
            assert team in src, f"Expected team abbreviation {team} in NHL_TEAMS list"

    def test_notebook_references_sqlalchemy_engine(self):
        """Notebook must connect via SQLAlchemy create_engine (no Flask app context)."""
        src = _notebook_source()
        assert "create_engine" in src

    def test_notebook_references_sqlite_db_path(self):
        """Notebook must reference the Flask app's SQLite database file path."""
        src = _notebook_source()
        assert "nhl_dashboard.db" in src

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

    def test_notebook_section1_fetches_one_team_roster(self):
        """Section 1 must fetch a single team roster to show response shape."""
        src = _notebook_source()
        assert any(term in src for term in ["SAMPLE_TEAM", "sample_team", "TOR"])

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

    def test_notebook_fetches_20252026_season(self):
        """Section 3 must fetch the 20252026 season roster."""
        src = _notebook_source()
        assert "20252026" in src

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
