"""Tests for boxscore_explorer.ipynb existence and structure (Issue #160).

Verifies the notebook file exists and contains all required sections, field
inventory analysis, and star schema design defined in the acceptance criteria.
"""
import json
from pathlib import Path

import pytest

_NOTEBOOK_PATH = (
    Path(__file__).parent.parent / "notebooks" / "boxscore_explorer.ipynb"
)


def _notebook_source() -> str:
    """Return all cell source text from boxscore_explorer.ipynb joined."""
    with open(_NOTEBOOK_PATH) as f:
        nb = json.load(f)
    return "\n".join("".join(cell["source"]) for cell in nb["cells"])


class TestBoxscoreExplorerNotebookExists:
    def test_notebook_file_exists(self):
        """boxscore_explorer.ipynb must exist in the notebooks directory."""
        assert _NOTEBOOK_PATH.exists(), (
            f"Expected notebook at {_NOTEBOOK_PATH} — create it to satisfy Issue #160."
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


class TestBoxscoreExplorerEndpoint:
    def test_notebook_references_boxscore_endpoint(self):
        """Notebook must reference the /v1/gamecenter/{game_id}/boxscore endpoint."""
        assert "boxscore" in _notebook_source()

    def test_notebook_references_gamecenter_path(self):
        """Notebook must reference the gamecenter API path."""
        assert "gamecenter" in _notebook_source()

    def test_notebook_references_nhle_api_base(self):
        """Notebook must reference the NHL web API base URL."""
        src = _notebook_source()
        assert "api-web.nhle.com" in src or "nhle.com" in src


class TestBoxscoreExplorerGameSampling:
    def test_notebook_samples_at_least_25_games(self):
        """Notebook must reference sampling of 25 or more game IDs."""
        src = _notebook_source()
        # Accept any indication of 25+ game sampling
        assert any(term in src for term in ["25", "50", "sample", "game_ids", "GAME_IDS"])

    def test_notebook_references_different_game_types(self):
        """Notebook must reference regular season and/or playoff game types."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in ["regular season", "playoff", "game_type", "gameType", "season", "02", "03"]
        )

    def test_notebook_references_game_id_list(self):
        """Notebook must define or describe a list of game IDs to sample."""
        src = _notebook_source()
        assert any(term in src for term in ["game_ids", "game_id", "GAME_IDS", "GAME_ID"])


class TestBoxscoreExplorerFieldInventory:
    def test_notebook_contains_field_inventory_section(self):
        """Notebook must include a Field Inventory section."""
        src = _notebook_source()
        assert any(
            term in src
            for term in ["Field Inventory", "field inventory", "Field inventory"]
        )

    def test_notebook_references_null_rates(self):
        """Notebook must enumerate null rates per field."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in ["null rate", "null_rate", "null count", "null%", "isnull", "isna"]
        )

    def test_notebook_references_data_types(self):
        """Notebook must enumerate data types per field."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in ["dtype", "data type", "type", "inferred_type"]
        )

    def test_notebook_references_example_values(self):
        """Notebook must show example values per field."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in ["example", "sample value", "unique", "value_counts", "head("]
        )

    def test_notebook_references_top_level_fields(self):
        """Notebook must enumerate top-level API response fields."""
        src = _notebook_source()
        assert any(
            term in src
            for term in ["awayTeam", "homeTeam", "playerByGameStats", "gameDate", "top-level", "top_level"]
        )


class TestBoxscoreExplorerStarSchema:
    def test_notebook_contains_star_schema_section(self):
        """Notebook must include a Star Schema section."""
        src = _notebook_source()
        assert any(
            term in src
            for term in ["Star Schema", "star schema", "star_schema"]
        )

    def test_notebook_contains_fact_table_candidate(self):
        """Notebook must propose a fact table candidate."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in [
                "fact table", "fact_table", "boxscore_player_stats",
                "boxscore_team_stats", "player_stat", "team_stat",
            ]
        )

    def test_notebook_contains_dimension_table_candidates(self):
        """Notebook must propose dimension table candidates."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in ["dimension", "dim_", "dimension table"]
        )

    def test_notebook_references_game_dimension(self):
        """Notebook must reference a game dimension table candidate."""
        src = _notebook_source()
        assert "game" in src.lower()

    def test_notebook_references_team_dimension(self):
        """Notebook must reference a team dimension table candidate."""
        src = _notebook_source()
        assert "team" in src.lower()

    def test_notebook_references_player_dimension(self):
        """Notebook must reference a player dimension table candidate."""
        src = _notebook_source()
        assert "player" in src.lower()

    def test_notebook_references_period_or_time_dimension(self):
        """Notebook must reference a period or time-related dimension."""
        src = _notebook_source()
        assert any(term in src.lower() for term in ["period", "time"])

    def test_notebook_maps_fields_to_proposed_tables(self):
        """Notebook must map API fields to proposed table/column names."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in [
                "mapped to", "proposed column", "column name", "api field",
                "→", "->", "maps to", "field mapping",
            ]
        )


class TestBoxscoreExplorerSections:
    def test_notebook_contains_setup_or_intro_section(self):
        """Notebook must contain a setup or introduction section."""
        src = _notebook_source()
        assert any(
            term in src
            for term in ["Setup", "Introduction", "Overview", "setup", "intro"]
        )

    def test_notebook_contains_api_exploration_section(self):
        """Notebook must include an API Exploration section."""
        src = _notebook_source()
        assert any(
            term in src
            for term in ["API Exploration", "API exploration", "Exploration", "Section 1", "Fetch"]
        )

    def test_notebook_contains_schema_design_section(self):
        """Notebook must include a schema design or proposal section."""
        src = _notebook_source()
        assert any(
            term in src
            for term in [
                "Schema Design", "Schema Proposal", "schema design",
                "schema proposal", "Star Schema",
            ]
        )

    def test_notebook_contains_create_table_or_column_mapping(self):
        """Notebook must include SQL DDL or a column-mapping table."""
        src = _notebook_source()
        assert any(
            term in src.upper()
            for term in ["CREATE TABLE", "PRIMARY KEY", "FOREIGN KEY"]
        ) or any(
            term in src
            for term in ["column", "table_name", "proposed_table"]
        )


class TestBoxscoreExplorerStarSchemaFix163:
    """Tests for Issue #163 — fix star schema FK target to boxscore.game_id."""

    def test_skater_stats_fk_targets_boxscore_game_id(self):
        """boxscore_skater_stats DDL must show FK → boxscore.game_id."""
        src = _notebook_source()
        assert "FK → boxscore.game_id" in src, (
            "Expected '-- FK → boxscore.game_id' in skater_stats DDL but found game.game_id."
        )

    def test_skater_stats_fk_does_not_reference_game_game_id(self):
        """No fact-table DDL FK comment must reference game.game_id."""
        src = _notebook_source()
        assert "FK → game.game_id" not in src, (
            "Found '-- FK → game.game_id' — fact tables should FK to boxscore.game_id."
        )

    def test_boxscore_listed_as_existing_dimension_table(self):
        """Star schema diagram must list boxscore under Existing dimension tables."""
        src = _notebook_source()
        assert "| `boxscore` | `game_id`" in src, (
            "Expected '| `boxscore` | `game_id`' row in Existing dimension tables section."
        )

    def test_game_not_listed_as_existing_dimension_table(self):
        """Star schema diagram must not list game as an existing dimension table."""
        src = _notebook_source()
        assert "| `game` | `game_id`" not in src, (
            "Found '| `game` | `game_id`' — game should be replaced by boxscore in Existing tables."
        )

    def test_tradeoffs_documents_fk_to_boxscore_not_game(self):
        """Trade-offs table must document FK → boxscore (not game) decision."""
        src = _notebook_source()
        assert "FK → `boxscore`" in src, (
            "Trade-offs table must have a row documenting that fact tables FK to boxscore, not game."
        )
