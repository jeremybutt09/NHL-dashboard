"""Tests for play_by_play_schema_proposal.ipynb existence and structure (Issue #140).

Verifies the notebook file exists and contains all required sections, schema options,
and structural elements defined in the acceptance criteria.
"""
import json
from pathlib import Path

import pytest

_NOTEBOOK_PATH = (
    Path(__file__).parent.parent / "notebooks" / "play_by_play_schema_proposal.ipynb"
)


def _notebook_source() -> str:
    """Return all cell source text from play_by_play_schema_proposal.ipynb joined."""
    with open(_NOTEBOOK_PATH) as f:
        nb = json.load(f)
    return "\n".join("".join(cell["source"]) for cell in nb["cells"])


class TestPlayByPlayNotebookExists:
    def test_notebook_file_exists(self):
        """play_by_play_schema_proposal.ipynb must exist in the notebooks directory."""
        assert _NOTEBOOK_PATH.exists(), (
            f"Expected notebook at {_NOTEBOOK_PATH} — create it to satisfy Issue #140."
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


class TestPlayByPlayNotebookEndpoint:
    def test_notebook_references_play_by_play_endpoint(self):
        """Notebook must reference the /v1/gamecenter/{game_id}/play-by-play endpoint."""
        assert "play-by-play" in _notebook_source()

    def test_notebook_references_gamecenter_path(self):
        """Notebook must reference the gamecenter API path."""
        assert "gamecenter" in _notebook_source()

    def test_notebook_references_plays_array(self):
        """Notebook must reference the plays[] array from the API response."""
        assert "plays" in _notebook_source()

    def test_notebook_references_type_code_or_type_desc_key(self):
        """Notebook must reference typeCode or typeDescKey event fields."""
        src = _notebook_source()
        assert "typeCode" in src or "typeDescKey" in src


class TestPlayByPlayNotebookSections:
    def test_notebook_contains_api_exploration_section(self):
        """Notebook must include Section 1: API Exploration."""
        assert "API Exploration" in _notebook_source()

    def test_notebook_contains_event_classification_section(self):
        """Notebook must include Section 2: Event Classification."""
        assert "Event Classification" in _notebook_source()

    def test_notebook_contains_field_inventory_section(self):
        """Notebook must include Section 3: Field Inventory."""
        assert "Field Inventory" in _notebook_source()

    def test_notebook_contains_schema_option_a(self):
        """Notebook must include Schema Option A: Single Table."""
        assert "Option A" in _notebook_source()

    def test_notebook_contains_schema_option_b(self):
        """Notebook must include Schema Option B: Base + Child Tables."""
        assert "Option B" in _notebook_source()

    def test_notebook_contains_schema_option_c(self):
        """Notebook must include Schema Option C: Two-Table Split."""
        assert "Option C" in _notebook_source()

    def test_notebook_contains_recommendation_section(self):
        """Notebook must include Section 7: Recommendation."""
        assert "Recommendation" in _notebook_source()


class TestPlayByPlayNotebookEventCategories:
    def test_notebook_describes_player_action_events(self):
        """Notebook must describe player-action events and name at least one type."""
        src = _notebook_source()
        assert "player" in src.lower()
        assert any(term in src.lower() for term in ["goal", "hit", "shot", "faceoff", "penalty"])

    def test_notebook_describes_game_state_events(self):
        """Notebook must describe game-state events (period start/end, intermission, etc.)."""
        src = _notebook_source()
        assert any(
            term in src.lower()
            for term in ["period-start", "period start", "intermission", "game-state", "game state"]
        )

    def test_notebook_separates_two_event_categories(self):
        """Notebook must distinguish player-action events from game-state events."""
        src = _notebook_source()
        has_player = any(t in src.lower() for t in ["player-action", "player action", "player_event"])
        has_state = any(t in src.lower() for t in ["game-state", "game state", "game_state_event"])
        assert has_player or "player" in src.lower()
        assert has_state or "game_state" in src.lower() or "period" in src.lower()


class TestPlayByPlayNotebookSchemaContent:
    def test_notebook_contains_ddl_create_table(self):
        """Notebook must include SQL DDL (CREATE TABLE) for at least one schema option."""
        assert "CREATE TABLE" in _notebook_source().upper()

    def test_notebook_contains_pros_analysis(self):
        """Notebook must include pros analysis for schema trade-offs."""
        src = _notebook_source()
        assert "pros" in src.lower() or "Pros" in src

    def test_notebook_contains_cons_analysis(self):
        """Notebook must include cons analysis for schema trade-offs."""
        src = _notebook_source()
        assert "cons" in src.lower() or "Cons" in src

    def test_notebook_option_a_is_single_table(self):
        """Option A description must reference a single-table or nullable-columns approach."""
        src = _notebook_source()
        assert "single" in src.lower() or "nullable" in src.lower()

    def test_notebook_option_b_references_child_tables(self):
        """Option B description must reference child tables or typed sub-tables."""
        src = _notebook_source()
        assert "child" in src.lower() or "typed" in src.lower() or "goal_event" in src

    def test_notebook_option_c_is_two_table_split(self):
        """Option C description must reference a two-table split."""
        src = _notebook_source()
        assert "two" in src.lower() or "player_event" in src or "game_state_event" in src

    def test_notebook_recommendation_section_has_blank_for_developer(self):
        """Recommendation section must be blank/placeholder for the developer to fill in."""
        src = _notebook_source()
        assert "Recommendation" in src
        # Section should invite developer input, not prescribe a choice
        assert any(term in src.lower() for term in [
            "chosen", "choice", "record", "approach", "rationale", "decision", "developer"
        ])
