"""
Issue #123 — Weekly harness review: 2026-05-25.

Failing tests asserting the CORRECT state the harness must reach.
All tests should FAIL before implementation and PASS after.
"""

import json
import os
import stat

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_FEATURE_LIST = os.path.join(REPO_ROOT, "feature_list.json")
_INIT_SH = os.path.join(REPO_ROOT, "init.sh")
_HANDOFF = os.path.join(REPO_ROOT, "session-handoff.md")
_RESUME = os.path.join(REPO_ROOT, "RESUME-GUIDE.md")
_HARNESS_AGENTS = os.path.join(REPO_ROOT, "harness", "AGENTS.md")
_CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")
_ISSUE_PROMPT = os.path.join(REPO_ROOT, "scripts", "issue-prompt.md")


def _read(path):
    with open(path) as f:
        return f.read()


# ── feature_list.json ─────────────────────────────────────────────────────────

def test_feature_list_json_exists():
    """feature_list.json must exist at the project root."""
    assert os.path.isfile(_FEATURE_LIST), (
        "feature_list.json not found at project root"
    )


def test_feature_list_json_is_valid_json():
    """feature_list.json must be valid JSON containing a list."""
    with open(_FEATURE_LIST) as f:
        data = json.load(f)
    assert isinstance(data, list), "feature_list.json must be a JSON array"


def test_feature_list_json_entries_have_required_keys():
    """Each entry in feature_list.json must have id, title, status, and issues keys."""
    with open(_FEATURE_LIST) as f:
        data = json.load(f)
    assert data, "feature_list.json must not be empty"
    for entry in data:
        for key in ("id", "title", "status", "issues"):
            assert key in entry, f"feature_list.json entry missing key '{key}': {entry}"


def test_feature_list_json_has_live_scoreboard():
    """feature_list.json must list the Live Scoreboard feature."""
    with open(_FEATURE_LIST) as f:
        data = json.load(f)
    titles = [e.get("title", "").lower() for e in data]
    assert any("scoreboard" in t or "live score" in t for t in titles), (
        "Live Scoreboard feature not found in feature_list.json"
    )


def test_feature_list_json_has_betting_odds():
    """feature_list.json must list the Betting Odds feature."""
    with open(_FEATURE_LIST) as f:
        data = json.load(f)
    titles = [e.get("title", "").lower() for e in data]
    assert any("odds" in t or "betting" in t for t in titles), (
        "Betting Odds feature not found in feature_list.json"
    )


def test_feature_list_json_done_items_have_issues():
    """All done feature entries in feature_list.json must have a non-empty issues list."""
    with open(_FEATURE_LIST) as f:
        data = json.load(f)
    for entry in data:
        if entry.get("status") == "done":
            assert entry.get("issues"), (
                f"Done feature '{entry.get('title')}' has no issues list"
            )


# ── init.sh ───────────────────────────────────────────────────────────────────

def test_init_sh_exists():
    """init.sh must exist at the project root."""
    assert os.path.isfile(_INIT_SH), "init.sh not found at project root"


def test_init_sh_is_executable():
    """init.sh must be marked executable."""
    mode = os.stat(_INIT_SH).st_mode
    assert mode & stat.S_IXUSR, "init.sh is not marked executable (chmod +x required)"


def test_init_sh_has_pip_install():
    """init.sh must run pip install -r requirements.txt."""
    text = _read(_INIT_SH)
    assert "pip install" in text and "requirements.txt" in text, (
        "init.sh must include 'pip install -r requirements.txt'"
    )


def test_init_sh_has_pytest():
    """init.sh must invoke pytest as the quality gate."""
    text = _read(_INIT_SH)
    assert "pytest" in text, "init.sh must invoke pytest"


# ── session-handoff.md ────────────────────────────────────────────────────────

def test_session_handoff_exists():
    """session-handoff.md must exist at the project root."""
    assert os.path.isfile(_HANDOFF), "session-handoff.md not found at project root"


def test_session_handoff_mentions_last_issue():
    """session-handoff.md must document the last closed issue (≥ #122)."""
    text = _read(_HANDOFF)
    assert "#122" in text or "122" in text, (
        "session-handoff.md must document the last closed issue (#122)"
    )


def test_session_handoff_has_next_steps():
    """session-handoff.md must have a next steps or open work section."""
    text = _read(_HANDOFF).lower()
    assert "next" in text or "open" in text or "backlog" in text, (
        "session-handoff.md must document next steps or open work"
    )


# ── RESUME-GUIDE.md ───────────────────────────────────────────────────────────

def test_resume_guide_exists():
    """RESUME-GUIDE.md must exist at the project root."""
    assert os.path.isfile(_RESUME), "RESUME-GUIDE.md not found at project root"


def test_resume_guide_references_init_sh():
    """RESUME-GUIDE.md must reference init.sh as the first setup step."""
    text = _read(_RESUME)
    assert "init.sh" in text, "RESUME-GUIDE.md must reference init.sh"


def test_resume_guide_references_session_handoff():
    """RESUME-GUIDE.md must reference session-handoff.md for resuming context."""
    text = _read(_RESUME)
    assert "session-handoff" in text, (
        "RESUME-GUIDE.md must reference session-handoff.md"
    )


def test_resume_guide_references_feature_list():
    """RESUME-GUIDE.md must reference feature_list.json for finding next work."""
    text = _read(_RESUME)
    assert "feature_list" in text, (
        "RESUME-GUIDE.md must reference feature_list.json"
    )


# ── harness/AGENTS.md — Definition of Done ───────────────────────────────────

def test_harness_agents_has_definition_of_done():
    """harness/AGENTS.md must include a Definition of Done section."""
    text = _read(_HARNESS_AGENTS)
    assert "Definition of Done" in text or "## DoD" in text, (
        "harness/AGENTS.md missing '## Definition of Done' section"
    )


def test_harness_agents_dod_mentions_tests_pass():
    """DoD checklist must require tests to pass."""
    text = _read(_HARNESS_AGENTS)
    assert "tests pass" in text.lower() or "all tests" in text.lower(), (
        "harness/AGENTS.md DoD must require tests to pass"
    )


def test_harness_agents_dod_mentions_issue_close():
    """DoD checklist must require closing the GitHub issue."""
    text = _read(_HARNESS_AGENTS)
    assert "issue" in text.lower() and ("close" in text.lower() or "closed" in text.lower()), (
        "harness/AGENTS.md DoD must require closing the GitHub issue"
    )


# ── CLAUDE.md project summary ─────────────────────────────────────────────────

def test_claude_md_mentions_odds_api():
    """CLAUDE.md project summary must mention the-odds-api as the odds source."""
    text = _read(_CLAUDE_MD)
    assert "the-odds-api" in text or "odds-api" in text, (
        "CLAUDE.md project summary must mention the-odds-api"
    )


def test_claude_md_mentions_active_api_endpoint():
    """CLAUDE.md must mention at least one active API endpoint."""
    text = _read(_CLAUDE_MD)
    assert "/api/games/today" in text or "/api/health" in text or "/api/games" in text, (
        "CLAUDE.md must mention an active API endpoint (/api/games/today etc.)"
    )


def test_claude_md_mentions_apscheduler():
    """CLAUDE.md must mention APScheduler (background polling)."""
    text = _read(_CLAUDE_MD)
    assert "APScheduler" in text or "scheduler" in text.lower(), (
        "CLAUDE.md must mention APScheduler / background polling"
    )


# ── scripts/issue-prompt.md ───────────────────────────────────────────────────

def test_issue_prompt_step2_no_app_dir():
    """scripts/issue-prompt.md Step 2 must not direct agents to write code in app/."""
    text = _read(_ISSUE_PROMPT)
    # "in `app/`" or "in app/" but not as part of nhl-dashboard/backend/app.py
    import re
    matches = re.findall(r"\bin `app/`", text)
    assert not matches, (
        "scripts/issue-prompt.md Step 2 still says 'in `app/`' — "
        "update to 'nhl-dashboard/backend/' or 'nhl-dashboard/frontend/'"
    )


def test_issue_prompt_step0_includes_models():
    """scripts/issue-prompt.md Step 0 must list nhl-dashboard/backend/models.py."""
    text = _read(_ISSUE_PROMPT)
    assert "nhl-dashboard/backend/models.py" in text, (
        "scripts/issue-prompt.md Step 0 reading list must include "
        "nhl-dashboard/backend/models.py"
    )


def test_issue_prompt_step0_includes_nhl_client():
    """scripts/issue-prompt.md Step 0 must list nhl-dashboard/backend/nhl_client.py."""
    text = _read(_ISSUE_PROMPT)
    assert "nhl-dashboard/backend/nhl_client.py" in text, (
        "scripts/issue-prompt.md Step 0 reading list must include "
        "nhl-dashboard/backend/nhl_client.py"
    )
