"""
Issue #174 — Weekly harness review: 2026-06-08.

Failing tests asserting the CORRECT state the harness must reach.
All tests should FAIL before implementation and PASS after.
"""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_HARNESS_PROGRESS = os.path.join(REPO_ROOT, "harness", "progress.md")
_CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")
_ISSUE_PROMPT = os.path.join(REPO_ROOT, "scripts", "issue-prompt.md")
_HANDOFF = os.path.join(REPO_ROOT, "session-handoff.md")


def _read(path):
    with open(path) as f:
        return f.read()


# ── H2: harness/progress.md must exist and be seeded ─────────────────────────

def test_harness_progress_md_exists():
    """harness/progress.md must exist as a human-readable progress log."""
    assert os.path.exists(_HARNESS_PROGRESS), (
        "harness/progress.md does not exist — create it with a seeded history "
        "of completed issues so every session has a changelog without re-deriving from git"
    )


def test_harness_progress_md_mentions_mvp_complete():
    """harness/progress.md must note that the three core MVP features are complete."""
    text = _read(_HARNESS_PROGRESS)
    assert "MVP complete" in text or "mvp complete" in text.lower(), (
        "harness/progress.md must state MVP is complete to prevent re-implementation"
    )


def test_harness_progress_md_mentions_active_endpoints():
    """harness/progress.md must name at least one active NHL API endpoint."""
    text = _read(_HARNESS_PROGRESS)
    assert "score/now" in text or "schedule/now" in text, (
        "harness/progress.md must name the active NHL API endpoints to orient new sessions"
    )


# ── L1: CLAUDE.md must surface the test-run command explicitly ───────────────

def test_claude_md_surfaces_pytest_command():
    """CLAUDE.md must include an explicit 'python3 -m pytest' command."""
    text = _read(_CLAUDE_MD)
    assert "python3 -m pytest" in text or "python -m pytest" in text, (
        "CLAUDE.md must surface the pytest run command so any session can verify "
        "green state without reading deep into memory docs"
    )


# ── M2: scripts/issue-prompt.md Step 0 must include memory/ ──────────────────

def test_issue_prompt_step0_includes_memory_dir():
    """scripts/issue-prompt.md Step 0 read list must include the memory/ directory."""
    text = _read(_ISSUE_PROMPT)
    assert "memory/" in text, (
        "scripts/issue-prompt.md Step 0 must tell automated sessions to read memory/ "
        "so established conventions are not re-derived from scratch each run"
    )


# ── LIFECYCLE: session-handoff.md must reflect completed issue ────────────────

def test_session_handoff_mentions_issue_174():
    """session-handoff.md must be updated to document the last closed issue #174."""
    text = _read(_HANDOFF)
    assert "#174" in text or "174" in text, (
        "session-handoff.md must document issue #174 as the last closed issue"
    )
