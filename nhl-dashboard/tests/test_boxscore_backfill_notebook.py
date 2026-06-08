"""Tests for boxscore_backfill.ipynb existence and structure (Issue #172).

Verifies the notebook file exists and contains all required sections and
structural elements defined in the acceptance criteria: Config cell, Section 1
(game IDs from DB), Section 2 (preview DataFrame), Section 3 (upsert
functions), Section 4 (batch upsert with rate-limiting and per-game commit),
and Section 5 (verification row counts).
"""
import json
from pathlib import Path

_NOTEBOOK_PATH = (
    Path(__file__).parent.parent / "notebooks" / "boxscore_backfill.ipynb"
)


def _notebook_source() -> str:
    """Return all cell source text from boxscore_backfill.ipynb joined."""
    with open(_NOTEBOOK_PATH) as f:
        nb = json.load(f)
    return "\n".join("".join(cell["source"]) for cell in nb["cells"])


class TestBoxscoreBackfillNotebookExists:
    def test_notebook_file_exists(self):
        """boxscore_backfill.ipynb must exist in the notebooks directory."""
        assert _NOTEBOOK_PATH.exists(), (
            f"Expected notebook at {_NOTEBOOK_PATH} — create it to satisfy Issue #172."
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


class TestBoxscoreBackfillSetup:
    def test_notebook_references_nhl_api_base(self):
        """Notebook must reference the NHL web API base URL."""
        src = _notebook_source()
        assert "api-web.nhle.com" in src

    def test_notebook_references_gamecenter_boxscore_endpoint(self):
        """Notebook must reference the /v1/gamecenter/{id}/boxscore endpoint."""
        src = _notebook_source()
        assert "gamecenter" in src and "boxscore" in src

    def test_notebook_references_sqlalchemy_engine(self):
        """Notebook must connect via SQLAlchemy create_engine (no Flask app context)."""
        src = _notebook_source()
        assert "create_engine" in src

    def test_notebook_references_sqlite_db_path(self):
        """Notebook must reference the Flask app's SQLite database at instance/nhl.db."""
        src = _notebook_source()
        assert "instance" in src and "nhl.db" in src

    def test_notebook_references_rate_limiting(self):
        """Notebook must rate-limit API calls at 50 ms between requests."""
        src = _notebook_source()
        assert "time.sleep" in src
        assert any(term in src for term in ["0.05", "50 ms", "50ms"])


class TestBoxscoreBackfillConfig:
    def test_notebook_has_start_date_config(self):
        """Notebook must define a START_DATE config variable."""
        src = _notebook_source()
        assert "START_DATE" in src

    def test_notebook_has_end_date_config(self):
        """Notebook must define an END_DATE config variable."""
        src = _notebook_source()
        assert "END_DATE" in src

    def test_notebook_has_game_types_config(self):
        """Notebook must define a GAME_TYPES config variable defaulting to [2, 3]."""
        src = _notebook_source()
        assert "GAME_TYPES" in src
        assert "2" in src and "3" in src


class TestBoxscoreBackfillSection1:
    def test_notebook_section1_exists(self):
        """Notebook must contain Section 1 — Load game IDs from DB."""
        src = _notebook_source()
        assert "Section 1" in src

    def test_notebook_section1_queries_game_table(self):
        """Section 1 must query the game table for game IDs."""
        src = _notebook_source()
        assert "game" in src
        assert any(
            term in src for term in [
                "SELECT game_id", "FROM game", "game_id",
            ]
        )

    def test_notebook_section1_filters_by_date_range(self):
        """Section 1 must filter the game table by the configured date range."""
        src = _notebook_source()
        assert "START_DATE" in src and "END_DATE" in src
        assert any(
            term in src for term in ["BETWEEN", "game_date", ">=", "<="]
        )

    def test_notebook_section1_filters_by_game_type(self):
        """Section 1 must filter by GAME_TYPES to restrict to regular season / playoffs."""
        src = _notebook_source()
        assert "GAME_TYPES" in src
        assert any(term in src for term in ["game_type", "IN", "gameType"])


class TestBoxscoreBackfillSection2:
    def test_notebook_section2_exists(self):
        """Notebook must contain Section 2 — Preview."""
        src = _notebook_source()
        assert "Section 2" in src

    def test_notebook_section2_shows_preview_dataframe(self):
        """Section 2 must display a DataFrame for the developer to confirm scope."""
        src = _notebook_source()
        assert any(
            term in src for term in ["DataFrame", "display(", "df_", "head("]
        )

    def test_notebook_section2_shows_game_date(self):
        """Section 2 preview must include game_date column."""
        src = _notebook_source()
        assert "game_date" in src

    def test_notebook_section2_shows_team_info(self):
        """Section 2 preview must show away/home team information."""
        src = _notebook_source()
        assert any(term in src for term in ["away_team", "home_team", "away", "home"])


class TestBoxscoreBackfillSection3:
    def test_notebook_section3_exists(self):
        """Notebook must contain Section 3 — Upsert functions."""
        src = _notebook_source()
        assert "Section 3" in src

    def test_notebook_section3_defines_upsert_game_stats(self):
        """Section 3 must define upsert_game_stats() function."""
        src = _notebook_source()
        assert "upsert_game_stats" in src

    def test_notebook_section3_defines_upsert_skater_stats(self):
        """Section 3 must define upsert_skater_stats() function."""
        src = _notebook_source()
        assert "upsert_skater_stats" in src

    def test_notebook_section3_defines_upsert_goalie_stats(self):
        """Section 3 must define upsert_goalie_stats() function."""
        src = _notebook_source()
        assert "upsert_goalie_stats" in src

    def test_notebook_section3_defines_check_and_backfill_player(self):
        """Section 3 must define check_and_backfill_player() for dim_player gap detection."""
        src = _notebook_source()
        assert "check_and_backfill_player" in src

    def test_notebook_section3_uses_session_merge(self):
        """Section 3 upsert functions must use session.merge() for idempotent upserts."""
        src = _notebook_source()
        assert "session.merge" in src or "merge(" in src

    def test_notebook_section3_imports_fact_boxscore_game_stats(self):
        """Section 3 must import FactBoxscoreGameStats from models."""
        src = _notebook_source()
        assert "FactBoxscoreGameStats" in src

    def test_notebook_section3_imports_fact_skater_stats(self):
        """Section 3 must import FactSkaterStats from models."""
        src = _notebook_source()
        assert "FactSkaterStats" in src

    def test_notebook_section3_imports_fact_goalie_stats(self):
        """Section 3 must import FactGoalieStats from models."""
        src = _notebook_source()
        assert "FactGoalieStats" in src

    def test_notebook_section3_imports_dim_player(self):
        """Section 3 must import DimPlayer for backfill gap detection."""
        src = _notebook_source()
        assert "DimPlayer" in src

    def test_notebook_section3_parses_save_shots_against(self):
        """upsert_goalie_stats must parse saveShotsAgainst composite string."""
        src = _notebook_source()
        assert "saveShotsAgainst" in src or "save_shots_against" in src
        assert "saves" in src and "shots_against" in src

    def test_notebook_section3_backfill_calls_player_landing(self):
        """check_and_backfill_player must call the NHL player landing endpoint."""
        src = _notebook_source()
        assert "player" in src and "landing" in src


class TestBoxscoreBackfillSection4:
    def test_notebook_section4_exists(self):
        """Notebook must contain Section 4 — Batch upsert."""
        src = _notebook_source()
        assert "Section 4" in src

    def test_notebook_section4_loops_over_game_ids(self):
        """Section 4 must iterate over the game ID list."""
        src = _notebook_source()
        assert any(
            term in src for term in [
                "for game_id in", "GAME_IDS", "game_ids",
            ]
        )

    def test_notebook_section4_calls_upsert_game_stats(self):
        """Section 4 batch loop must call upsert_game_stats()."""
        src = _notebook_source()
        assert "upsert_game_stats" in src

    def test_notebook_section4_calls_upsert_skater_stats(self):
        """Section 4 batch loop must call upsert_skater_stats()."""
        src = _notebook_source()
        assert "upsert_skater_stats" in src

    def test_notebook_section4_calls_upsert_goalie_stats(self):
        """Section 4 batch loop must call upsert_goalie_stats()."""
        src = _notebook_source()
        assert "upsert_goalie_stats" in src

    def test_notebook_section4_commits_per_game(self):
        """Section 4 must commit once per game (not once at the end) for crash safety."""
        src = _notebook_source()
        assert "session.commit()" in src

    def test_notebook_section4_has_rate_limiting(self):
        """Section 4 must rate-limit API requests at 50 ms between games."""
        src = _notebook_source()
        assert "time.sleep" in src

    def test_notebook_section4_prints_per_game_progress(self):
        """Section 4 must print per-game progress."""
        src = _notebook_source()
        assert "print" in src

    def test_notebook_section4_handles_api_errors(self):
        """Section 4 must handle individual game API failures without aborting the loop."""
        src = _notebook_source()
        assert any(term in src for term in ["try", "except", "raise_for_status"])


class TestBoxscoreBackfillSection5:
    def test_notebook_section5_exists(self):
        """Notebook must contain Section 5 — Verification."""
        src = _notebook_source()
        assert "Section 5" in src

    def test_notebook_section5_queries_fact_boxscore_game_stats(self):
        """Section 5 must show row count for fact_boxscore_game_stats."""
        src = _notebook_source()
        assert "fact_boxscore_game_stats" in src

    def test_notebook_section5_queries_fact_skater_stats(self):
        """Section 5 must show row count for fact_skater_stats."""
        src = _notebook_source()
        assert "fact_skater_stats" in src

    def test_notebook_section5_queries_fact_goalie_stats(self):
        """Section 5 must show row count for fact_goalie_stats."""
        src = _notebook_source()
        assert "fact_goalie_stats" in src

    def test_notebook_section5_shows_row_counts(self):
        """Section 5 must display row counts for all three fact tables."""
        src = _notebook_source()
        assert any(term in src for term in ["COUNT", "count", "COUNT(*)", "row_count"])

    def test_notebook_section5_shows_sample_rows(self):
        """Section 5 must display sample rows to confirm data quality."""
        src = _notebook_source()
        assert any(term in src for term in ["LIMIT", "head(", "display(", "sample("])
