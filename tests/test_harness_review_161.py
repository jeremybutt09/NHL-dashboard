"""
Issue #161 — Weekly harness review: 2026-06-01.

Failing tests asserting the CORRECT state the harness must reach.
All tests should FAIL before implementation and PASS after.
"""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_AGENTS_ROOT = os.path.join(REPO_ROOT, "AGENTS.md")
_HARNESS_AGENTS = os.path.join(REPO_ROOT, "harness", "AGENTS.md")
_CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")
_SPEC_MD = os.path.join(REPO_ROOT, "harness", "SPEC.md")
_PROJECT_STRUCTURE = os.path.join(REPO_ROOT, "memory", "project_structure.md")
_HANDOFF = os.path.join(REPO_ROOT, "session-handoff.md")


def _read(path):
    with open(path) as f:
        return f.read()


# ── H3: harness/AGENTS.md must have explicit pytest run command ───────────────

def test_harness_agents_md_has_pytest_run_command():
    """harness/AGENTS.md must include the explicit 'python -m pytest' run command."""
    text = _read(_HARNESS_AGENTS)
    assert "python -m pytest" in text, (
        "harness/AGENTS.md Testing section must include 'python -m pytest tests/' "
        "so agents know exactly which command to run"
    )


def test_harness_agents_md_pytest_command_references_tests_dir():
    """harness/AGENTS.md pytest command must target the tests/ directory."""
    text = _read(_HARNESS_AGENTS)
    assert "python -m pytest tests/" in text or ("python -m pytest" in text and "tests/" in text), (
        "harness/AGENTS.md must specify 'python -m pytest tests/' (not just 'pytest')"
    )


# ── M2: CLAUDE.md "Read these first" must list memory/ and issue-prompt.md ───

def test_claude_md_read_first_mentions_memory_dir():
    """CLAUDE.md 'Read these first' section must mention the memory/ directory."""
    text = _read(_CLAUDE_MD)
    assert "memory/" in text or "`memory/`" in text, (
        "CLAUDE.md 'Read these first' must mention the memory/ directory for context"
    )


def test_claude_md_read_first_mentions_issue_prompt():
    """CLAUDE.md must mention scripts/issue-prompt.md as a reading source."""
    text = _read(_CLAUDE_MD)
    assert "issue-prompt.md" in text or "scripts/issue-prompt" in text, (
        "CLAUDE.md must reference scripts/issue-prompt.md so agents see the per-session driver"
    )


# ── M3: harness/SPEC.md must declare MVP complete ─────────────────────────────

def test_spec_md_has_status_section():
    """harness/SPEC.md must have a ## Status section near the top."""
    text = _read(_SPEC_MD)
    assert "## Status" in text, (
        "harness/SPEC.md must have a '## Status' section so agents know MVP is shipped"
    )


def test_spec_md_status_marks_mvp_complete():
    """harness/SPEC.md Status section must state MVP is complete."""
    text = _read(_SPEC_MD)
    assert "MVP complete" in text or "mvp complete" in text.lower(), (
        "harness/SPEC.md ## Status section must say 'MVP complete' to prevent re-implementing shipped features"
    )


# ── M1: memory/project_structure.md must reflect current test suite ───────────

def test_project_structure_md_includes_test_boxscore():
    """memory/project_structure.md must list test_boxscore.py."""
    text = _read(_PROJECT_STRUCTURE)
    assert "test_boxscore.py" in text, (
        "memory/project_structure.md is missing test_boxscore.py from the test list"
    )


def test_project_structure_md_includes_test_time_utils():
    """memory/project_structure.md must list test_time_utils.py."""
    text = _read(_PROJECT_STRUCTURE)
    assert "test_time_utils.py" in text, (
        "memory/project_structure.md is missing test_time_utils.py from the test list"
    )


def test_project_structure_md_includes_test_routes_partners():
    """memory/project_structure.md must list test_routes_partners.py."""
    text = _read(_PROJECT_STRUCTURE)
    assert "test_routes_partners.py" in text, (
        "memory/project_structure.md is missing test_routes_partners.py from the test list"
    )


def test_project_structure_md_no_stale_test_slate():
    """memory/project_structure.md must not list the non-existent test_slate.py."""
    text = _read(_PROJECT_STRUCTURE)
    assert "test_slate.py" not in text, (
        "memory/project_structure.md still lists test_slate.py which does not exist"
    )


def test_project_structure_md_no_stale_models():
    """memory/project_structure.md must not list models removed in the surgical schema cleanup."""
    text = _read(_PROJECT_STRUCTURE)
    stale_models = ["OddsSnapshot", "ModelFair", "NhlHistoricalGame"]
    for model in stale_models:
        assert model not in text, (
            f"memory/project_structure.md still lists removed model '{model}' — "
            "update to reflect current models.py"
        )


# ── L2: CLAUDE.md must document the ai-skills submodule ─────────────────────

def test_claude_md_mentions_ai_skills_submodule():
    """CLAUDE.md must document the ai-skills submodule so agents know it exists."""
    text = _read(_CLAUDE_MD)
    assert "ai-skills" in text or ".claude/skills" in text, (
        "CLAUDE.md must mention the ai-skills submodule (symlinked to .claude/skills)"
    )


# ── session-handoff.md must reflect completed issue ──────────────────────────

def test_session_handoff_mentions_issue_161():
    """session-handoff.md must document a closed issue at or after #161."""
    import re
    text = _read(_HANDOFF)
    issue_numbers = [int(n) for n in re.findall(r"#(\d+)", text)]
    assert any(n >= 161 for n in issue_numbers), (
        "session-handoff.md must document a recent closed issue (≥ #161)"
    )
