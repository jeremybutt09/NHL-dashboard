"""Tests for the PostToolUse hook in .claude/settings.local.json.

This file validates that the personal harness config is correctly structured to
auto-upload user stories to GitHub Issues. settings.local.json is gitignored
(personal to the harness engineer), so these tests fail when the file is absent
and pass once it is created locally.
"""

import json
import os

import pytest

SETTINGS_LOCAL_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", ".claude", "settings.local.json")
)


@pytest.fixture
def settings_local():
    """Load .claude/settings.local.json, failing the test if the file is absent."""
    if not os.path.exists(SETTINGS_LOCAL_PATH):
        pytest.fail(
            f"{SETTINGS_LOCAL_PATH} not found — "
            "create it with the PostToolUse hook for the 'user-story' skill. "
            "See Issue #62 for the required structure."
        )
    with open(SETTINGS_LOCAL_PATH) as f:
        return json.load(f)


def test_settings_local_has_post_tool_use_hooks(settings_local):
    """settings.local.json must define a non-empty PostToolUse hooks array."""
    assert "hooks" in settings_local, "Missing top-level 'hooks' key"
    assert "PostToolUse" in settings_local["hooks"], "Missing 'PostToolUse' under hooks"
    assert isinstance(settings_local["hooks"]["PostToolUse"], list)
    assert len(settings_local["hooks"]["PostToolUse"]) >= 1


def test_settings_local_has_skill_matcher(settings_local):
    """A PostToolUse entry must use 'Skill' as its matcher."""
    entries = settings_local["hooks"]["PostToolUse"]
    matchers = [e.get("matcher") for e in entries]
    assert "Skill" in matchers, f"Expected 'Skill' matcher, found {matchers}"


def test_settings_local_skill_entry_has_command(settings_local):
    """The Skill PostToolUse entry must include at least one command-type hook."""
    entries = settings_local["hooks"]["PostToolUse"]
    skill_entry = next((e for e in entries if e.get("matcher") == "Skill"), None)
    assert skill_entry is not None, "No PostToolUse entry with matcher 'Skill'"
    inner = skill_entry.get("hooks", [])
    assert len(inner) >= 1, "Skill PostToolUse entry has no inner hooks"
    types = [h.get("type") for h in inner]
    assert "command" in types, f"Expected a 'command' hook type, got {types}"


def test_settings_local_command_references_user_story(settings_local):
    """The hook command must filter on the 'user-story' skill name."""
    entries = settings_local["hooks"]["PostToolUse"]
    skill_entry = next((e for e in entries if e.get("matcher") == "Skill"), None)
    assert skill_entry is not None
    commands = [
        h.get("command", "")
        for h in skill_entry.get("hooks", [])
        if h.get("type") == "command"
    ]
    assert any("user-story" in cmd for cmd in commands), (
        f"No command references 'user-story': {commands}"
    )
