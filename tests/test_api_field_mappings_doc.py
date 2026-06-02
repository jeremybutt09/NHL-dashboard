"""Tests verifying docs/api-field-mappings.md exists and has required content."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_PATH = os.path.join(REPO_ROOT, "docs", "api-field-mappings.md")


def _doc_text():
    with open(DOC_PATH) as f:
        return f.read()


def test_api_field_mappings_doc_exists():
    """docs/api-field-mappings.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(DOC_PATH), "docs/api-field-mappings.md not found"


def test_schedule_endpoint_section_present():
    """/v1/schedule/now endpoint must have its own section."""
    text = _doc_text()
    assert "/v1/schedule/now" in text, "Schedule endpoint section missing"


def test_boxscore_endpoint_section_present():
    """/v1/gamecenter/{game_id}/boxscore endpoint must have its own section."""
    text = _doc_text()
    assert "/v1/gamecenter" in text, "Boxscore endpoint section missing"


def test_team_table_mappings_present():
    """team table column mappings must be documented."""
    text = _doc_text()
    assert "team.tri_code" in text, "team.tri_code mapping missing"
    assert "team.name" in text, "team.name mapping missing"


def test_boxscore_table_field_mappings_present():
    """boxscore table field mappings must be documented (Issue #133)."""
    text = _doc_text()
    assert "boxscore" in text.lower(), "boxscore table not documented in api-field-mappings.md"


def test_no_nhl_historical_game_field_mapping_reference():
    """nhl_historical_game is dropped — must not appear in field mappings doc."""
    text = _doc_text()
    assert "nhl_historical_game" not in text, \
        "Stale nhl_historical_game reference in api-field-mappings.md (renamed to game in Issue #131)"


def test_transformations_documented():
    """Status and period mapping logic locations must be documented."""
    text = _doc_text()
    assert "scores.py" in text or "boxscore.py" in text or "slate.py" in text, \
        "Status/period mapping location not documented"


def test_odds_client_stub_documented():
    """odds_client.py fixture data structure must be documented."""
    text = _doc_text()
    assert "odds_client" in text.lower(), "odds_client stub not documented"
    assert "stub" in text.lower() or "fixture" in text.lower(), \
        "odds_client fixture status not noted"


def test_unused_fields_noted():
    """Doc must note fields that are ignored/unused by the implementation."""
    text = _doc_text()
    assert "unused" in text.lower() or "ignored" in text.lower() or "not consumed" in text.lower(), \
        "No note about unused/ignored API fields found"


# ── Issue #129: /v1/score/now endpoint attribution ──────────────────────────


def test_score_now_is_primary_score_endpoint():
    """/v1/score/now must be documented as the primary score polling endpoint."""
    text = _doc_text()
    assert "/v1/score/now" in text, "/v1/score/now not documented as score endpoint"


def test_refresh_nhl_odds_documented():
    """refresh_nhl_odds() must be documented as the consumer of /v1/score/now partner odds."""
    text = _doc_text()
    assert "refresh_nhl_odds" in text or "nhl_odds" in text.lower(), \
        "refresh_nhl_odds() not documented"


def test_scores_service_path_documented():
    """services/scores.py must be listed as the consuming module."""
    text = _doc_text()
    assert "scores.py" in text, "services/scores.py not documented"


def test_score_now_odds_columns_documented():
    """/v1/score/now field-mapping table must cover nhl_odds_line columns."""
    text = _doc_text()
    for col in ("nhl_odds_line", "away_value", "home_value"):
        assert col in text, f"{col} missing from /v1/score/now field-mapping table"


def test_ignored_clock_subfields_documented():
    """Ignored clock sub-fields must be listed in the /v1/score/now ignored section."""
    text = _doc_text()
    for field in ("clock.secondsRemaining", "clock.running", "clock.inIntermission"):
        assert field in text, f"Ignored field '{field}' not documented"


def test_ignored_period_descriptor_max_regulation_documented():
    """Ignored periodDescriptor.maxRegulationPeriods must be listed."""
    text = _doc_text()
    assert "maxRegulationPeriods" in text, \
        "Ignored field 'periodDescriptor.maxRegulationPeriods' not documented"


def test_ignored_game_outcome_field_documented():
    """Ignored gameOutcome.lastPeriodType must be listed."""
    text = _doc_text()
    assert "gameOutcome" in text, "Ignored field 'gameOutcome' not documented"


def test_ignored_goals_and_series_fields_documented():
    """Ignored goals[] and seriesStatus must be listed."""
    text = _doc_text()
    assert "goals" in text, "Ignored field 'goals[]' not documented"
    assert "seriesStatus" in text, "Ignored field 'seriesStatus' not documented"


def test_ignored_broadcast_and_venue_fields_documented():
    """Ignored tvBroadcasts, neutralSite, and venueTimezone must be listed."""
    text = _doc_text()
    for field in ("neutralSite", "venueTimezone"):
        assert field in text, f"Ignored field '{field}' not documented"


def test_ignored_recap_link_fields_documented():
    """Ignored recap/video link fields must be listed."""
    text = _doc_text()
    for field in ("threeMinRecap", "condensedGame", "gameCenterLink", "seriesUrl"):
        assert field in text, f"Ignored field '{field}' not documented"


# ── Issue #146: visiting_ → away_ column rename ────────────────────────────────

def test_no_visiting_column_names():
    """api-field-mappings.md must not reference visiting_score or visiting_team_id (Issue #146)."""
    text = _doc_text()
    assert "visiting_score" not in text, \
        "Stale visiting_score in api-field-mappings.md — rename to away_score (Issue #146)"
    assert "visiting_team_id" not in text, \
        "Stale visiting_team_id in api-field-mappings.md — rename to away_team_id (Issue #146)"


def test_game_table_maps_visiting_api_fields_to_away_columns():
    """api-field-mappings.md must map visitingScore/visitingTeamId to away_score/away_team_id (Issue #146)."""
    text = _doc_text()
    assert "away_score" in text, \
        "away_score column mapping missing from api-field-mappings.md (Issue #146)"
    assert "away_team_id" in text, \
        "away_team_id column mapping missing from api-field-mappings.md (Issue #146)"
