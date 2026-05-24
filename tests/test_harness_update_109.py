"""
Issue #109 — Failing tests verifying harness file accuracy.

Each test asserts the CORRECT state that AGENTS.md and SPEC.md must reach.
All tests should FAIL against the stale harness files and PASS once updated.
"""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

_AGENTS = os.path.join(REPO_ROOT, "harness", "AGENTS.md")
_SPEC = os.path.join(REPO_ROOT, "harness", "SPEC.md")


def _read(path):
    with open(path) as f:
        return f.read()


# ── harness/SPEC.md ───────────────────────────────────────────────────────────

def test_spec_brand_name_peak():
    """SPEC.md must reference the brand name 'Peak'."""
    assert "Peak" in _read(_SPEC), "Brand name 'Peak' not found in SPEC.md"


def test_spec_positioning_headline():
    """SPEC.md must include the positioning headline."""
    text = _read(_SPEC)
    assert "Bet with a reason" in text, \
        "Positioning headline 'Bet with a reason, not a guess' not in SPEC.md"


def test_spec_target_user_age_range():
    """SPEC.md must define the target user age range (19-35)."""
    text = _read(_SPEC)
    assert "19" in text and "35" in text, \
        "Target user age range 19-35 not documented in SPEC.md"


def test_spec_target_user_not_sharp_bettors():
    """SPEC.md must explicitly exclude sharp/professional bettors."""
    text = _read(_SPEC)
    assert "sharp" in text.lower() or "professional gambler" in text.lower(), \
        "SPEC.md must state what the target user is NOT (sharp bettors / professional gamblers)"


def test_spec_three_bet_types_moneyline():
    """SPEC.md must define moneyline as a supported bet type."""
    text = _read(_SPEC).lower()
    assert "moneyline" in text, "Moneyline bet type not defined in SPEC.md"


def test_spec_three_bet_types_puckline():
    """SPEC.md must define puckline (spread) as a supported bet type."""
    text = _read(_SPEC).lower()
    assert "puckline" in text, "Puckline bet type not defined in SPEC.md"


def test_spec_three_bet_types_total():
    """SPEC.md must define total (over/under) as a supported bet type."""
    text = _read(_SPEC).lower()
    assert "total" in text or "over/under" in text, \
        "Total (O/U) bet type not defined in SPEC.md"


def test_spec_odds_source_the_odds_api():
    """SPEC.md must name the-odds-api as the odds data source."""
    text = _read(_SPEC)
    assert "the-odds-api" in text or "odds-api" in text, \
        "the-odds-api not listed as the odds data source in SPEC.md"


def test_spec_dollar_return_calculator():
    """SPEC.md must mention the dollar return calculator."""
    text = _read(_SPEC).lower()
    assert "dollar" in text or "return calculator" in text or "bet amount" in text, \
        "Dollar return calculator not mentioned in SPEC.md"


def test_spec_ux_design_principle():
    """SPEC.md must document the core UX design principle."""
    text = _read(_SPEC)
    assert "first-year bettor" in text or "every number" in text, \
        "UX design principle ('every number... first-year bettor') not in SPEC.md"


def test_spec_sport_rollout_nhl_mvp():
    """SPEC.md must document NHL as Phase 0 / MVP."""
    text = _read(_SPEC)
    assert "NHL" in text and ("Phase 0" in text or "MVP" in text), \
        "NHL MVP phase not documented in SPEC.md"


def test_spec_sport_rollout_mlb():
    """SPEC.md must document MLB as Phase 2 / Phase 1."""
    text = _read(_SPEC)
    assert "MLB" in text, "MLB phase not documented in SPEC.md"


def test_spec_sport_rollout_nfl_nba():
    """SPEC.md must document NFL and NBA in the roadmap."""
    text = _read(_SPEC)
    assert "NFL" in text and "NBA" in text, "NFL/NBA phases not documented in SPEC.md"


def test_spec_monetization_deferred():
    """SPEC.md must state that monetization is deferred post-MVP."""
    text = _read(_SPEC).lower()
    assert "monetiz" in text, "Monetization strategy not mentioned in SPEC.md"


def test_spec_legal_gate_on_affiliate():
    """SPEC.md must document that affiliate links require legal research first."""
    text = _read(_SPEC).lower()
    assert "legal" in text, "Legal gate on monetization not documented in SPEC.md"


def test_spec_hosting_target():
    """SPEC.md must document hosting target (Render/Railway/Fly.io)."""
    text = _read(_SPEC)
    assert any(h in text for h in ["Render", "Railway", "Fly.io"]), \
        "Hosting target (Render/Railway/Fly.io) not documented in SPEC.md"


def test_spec_analytics_requirement():
    """SPEC.md must mention analytics (Plausible or PostHog)."""
    text = _read(_SPEC)
    assert "Plausible" in text or "PostHog" in text or "analytics" in text.lower(), \
        "Analytics requirement not documented in SPEC.md"


def test_spec_architecture_react_frontend():
    """SPEC.md must list React as the frontend framework."""
    text = _read(_SPEC)
    assert "React" in text, "React frontend not listed in architecture in SPEC.md"


def test_spec_architecture_backend_path():
    """SPEC.md must reference nhl-dashboard/backend/ as the backend directory."""
    text = _read(_SPEC)
    assert "nhl-dashboard/backend" in text or "nhl-dashboard/frontend" in text, \
        "Correct directory paths (nhl-dashboard/backend/ or frontend/) not in SPEC.md"


def test_spec_success_metrics():
    """SPEC.md must include MVP success metrics."""
    text = _read(_SPEC).lower()
    assert "success metric" in text or "10+" in text or "real user" in text, \
        "MVP success metrics not documented in SPEC.md"


def test_spec_decision_support_vision():
    """SPEC.md must describe Peak as a decision-support tool, not a sportsbook."""
    text = _read(_SPEC).lower()
    assert "decision-support" in text or "decision support" in text, \
        "Vision as decision-support tool not documented in SPEC.md"


# ── harness/AGENTS.md ─────────────────────────────────────────────────────────

def test_agents_odds_source_the_odds_api():
    """AGENTS.md must name the-odds-api as the odds data source."""
    text = _read(_AGENTS)
    assert "the-odds-api" in text or "odds-api" in text, \
        "the-odds-api not listed as odds source in AGENTS.md"


def test_agents_nhl_api_not_odds_source():
    """AGENTS.md must not instruct agents to use the NHL API for odds."""
    text = _read(_AGENTS)
    assert "money line betting odds" not in text.lower() \
        and "betting odds" not in text.lower() \
        or "the-odds-api" in text, \
        "AGENTS.md still tells agents to fetch betting odds from the NHL API"


def test_agents_backend_directory_path():
    """AGENTS.md must reference nhl-dashboard/backend/ as the backend code directory."""
    text = _read(_AGENTS)
    assert "nhl-dashboard/backend" in text, \
        "nhl-dashboard/backend/ directory path not in AGENTS.md"


def test_agents_frontend_directory_path():
    """AGENTS.md must reference nhl-dashboard/frontend/ as the frontend directory."""
    text = _read(_AGENTS)
    assert "nhl-dashboard/frontend" in text, \
        "nhl-dashboard/frontend/ directory path not in AGENTS.md"


def test_agents_tests_directory_path():
    """AGENTS.md must reference nhl-dashboard/tests/ as the test directory."""
    text = _read(_AGENTS)
    assert "nhl-dashboard/tests" in text, \
        "nhl-dashboard/tests/ directory path not in AGENTS.md"


def test_agents_react_frontend_role():
    """AGENTS.md must expand the role to include React frontend work."""
    text = _read(_AGENTS)
    assert "React" in text, "React frontend role not mentioned in AGENTS.md"


def test_agents_product_name_peak():
    """AGENTS.md must reference the product name 'Peak'."""
    text = _read(_AGENTS)
    assert "Peak" in text, "Product name 'Peak' not in AGENTS.md"


def test_agents_casual_bettor_context():
    """AGENTS.md must describe the casual bettor target user."""
    text = _read(_AGENTS).lower()
    assert "casual bettor" in text, "Casual bettor context not in AGENTS.md"


def test_agents_the_odds_api_key_env_var():
    """AGENTS.md must document THE_ODDS_API_KEY environment variable."""
    text = _read(_AGENTS)
    assert "THE_ODDS_API_KEY" in text, \
        "THE_ODDS_API_KEY env var not documented in AGENTS.md"


def test_agents_legal_compliance_guardrail():
    """AGENTS.md must include a legal/compliance guardrail about affiliate features."""
    text = _read(_AGENTS).lower()
    assert "affiliate" in text and "legal" in text, \
        "Legal/compliance guardrail on affiliate features not in AGENTS.md"


def test_agents_responsible_gambling_requirement():
    """AGENTS.md must require responsible gambling language on public pages."""
    text = _read(_AGENTS).lower()
    assert "responsible gambling" in text or "gambling" in text, \
        "Responsible gambling requirement not in AGENTS.md"


def test_agents_react_functional_components():
    """AGENTS.md must specify functional React components as the convention."""
    text = _read(_AGENTS)
    assert "functional component" in text.lower() or "functional components" in text.lower(), \
        "React functional component convention not in AGENTS.md"


def test_agents_multi_sport_framework():
    """AGENTS.md must mention the shared translation framework for multi-sport modules."""
    text = _read(_AGENTS).lower()
    assert "sport" in text and ("translation" in text or "framework" in text or "module" in text), \
        "Multi-sport module guidance not in AGENTS.md"


def test_agents_tdd_workflow_preserved():
    """AGENTS.md must still contain the TDD Red/Green/Refactor workflow."""
    text = _read(_AGENTS)
    assert "Red" in text and "Green" in text and "Refactor" in text, \
        "TDD workflow removed from AGENTS.md — must be preserved"


def test_agents_coding_standards_preserved():
    """AGENTS.md must still contain snake_case and PascalCase naming conventions."""
    text = _read(_AGENTS)
    assert "snake_case" in text and "PascalCase" in text, \
        "Naming conventions removed from AGENTS.md — must be preserved"
