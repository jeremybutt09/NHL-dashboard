"""Tests verifying docs/api-response-examples.md exists and has required sections (Issue #100)."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_PATH = os.path.join(REPO_ROOT, "docs", "api-response-examples.md")


def _doc_text():
    with open(DOC_PATH) as f:
        return f.read()


def test_api_response_examples_doc_exists():
    """docs/api-response-examples.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(DOC_PATH), "docs/api-response-examples.md not found"


def test_health_section_present():
    """Doc must contain a section for /api/health."""
    text = _doc_text()
    assert "/api/health" in text, "/api/health section missing from api-response-examples.md"


def test_games_today_section_present():
    """Doc must contain a section for /api/games/today."""
    text = _doc_text()
    assert "/api/games/today" in text, "/api/games/today section missing from api-response-examples.md"


def test_error_responses_section_present():
    """Doc must contain an Error Responses section."""
    text = _doc_text()
    assert "Error Responses" in text, "'Error Responses' section missing from api-response-examples.md"


def test_live_game_example_present():
    """Games/today section must include at least one live game example."""
    text = _doc_text()
    assert '"live"' in text, "No live game example found in api-response-examples.md"


def test_final_game_example_present():
    """Games/today section must include at least one final game example."""
    text = _doc_text()
    assert '"final"' in text, "No final game example found in api-response-examples.md"


def test_sparkline_t_field_explained():
    """Doc must explain the sparkline t field (timestamp)."""
    text = _doc_text()
    assert "movement_24h" in text, "movement_24h sparkline field not explained in api-response-examples.md"


def test_sparkline_home_ml_defined():
    """Doc must define home_ml as American odds integer in sparkline context."""
    text = _doc_text()
    assert "home_ml" in text, "home_ml field not defined in api-response-examples.md"


def test_sparkline_away_ml_defined():
    """Doc must define away_ml as American odds integer in sparkline context."""
    text = _doc_text()
    assert "away_ml" in text, "away_ml field not defined in api-response-examples.md"


def test_http_500_documented():
    """Error Responses section must show HTTP 500 JSON body."""
    text = _doc_text()
    assert "500" in text, "HTTP 500 error response not documented in api-response-examples.md"


def test_http_404_documented():
    """Error Responses section must show HTTP 404 JSON body."""
    text = _doc_text()
    assert "404" in text, "HTTP 404 error response not documented in api-response-examples.md"


def test_health_field_status_annotated():
    """Health section must annotate the status field."""
    text = _doc_text()
    assert "status" in text, "'status' field not annotated in health section"


def test_health_field_db_annotated():
    """Health section must annotate the db field."""
    text = _doc_text()
    assert '"db"' in text, "'db' field not annotated in health section"


def test_health_field_last_poll_annotated():
    """Health section must annotate the last_poll field."""
    text = _doc_text()
    assert "last_poll" in text, "'last_poll' field not annotated in health section"


def test_games_today_id_field_annotated():
    """Games/today section must annotate the id field."""
    text = _doc_text()
    assert '"id"' in text, "'id' field not annotated in games/today section"


def test_games_today_edge_field_annotated():
    """Games/today section must annotate the edge field."""
    text = _doc_text()
    assert "edge" in text, "'edge' field not annotated in games/today section"


def test_no_nhl_historical_game_reference():
    """nhl_historical_game is a dropped name — must not appear in the response examples doc."""
    text = _doc_text()
    assert "nhl_historical_game" not in text, \
        "Stale nhl_historical_game reference found in api-response-examples.md"


# ── Issue #146: visiting_ → away_ column rename ────────────────────────────────

def test_no_visiting_db_column_names():
    """api-response-examples.md must not reference visiting_score or visiting_team_id as DB columns (Issue #146)."""
    text = _doc_text()
    assert "visiting_score" not in text, \
        "Stale visiting_score DB column name in api-response-examples.md — rename to away_score (Issue #146)"
    assert "visiting_team_id" not in text, \
        "Stale visiting_team_id DB column name in api-response-examples.md — rename to away_team_id (Issue #146)"


def test_nhl_stats_api_section_uses_away_column_names():
    """api-response-examples.md must document away_score and away_team_id as DB columns (Issue #146)."""
    text = _doc_text()
    assert "away_score" in text, \
        "away_score DB column missing from api-response-examples.md (Issue #146)"
    assert "away_team_id" in text, \
        "away_team_id DB column missing from api-response-examples.md (Issue #146)"
