"""Tests for .claude/settings.json tool allowlist (Issue #50)."""

import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SETTINGS_PATH = os.path.join(REPO_ROOT, ".claude", "settings.json")
CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")

DESTRUCTIVE_PATTERNS = [
    "rm -rf",
    "git push --force",
    "git reset --hard",
]

EXPECTED_ALLOWED_TOOLS = [
    "Read",
    "Edit",
    "Write",
    "Glob",
    "Grep",
]


def _load_settings():
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def test_settings_file_exists():
    """`.claude/settings.json` must exist in the repository."""
    assert os.path.isfile(SETTINGS_PATH), ".claude/settings.json does not exist"


def test_settings_file_is_valid_json():
    """`.claude/settings.json` must be valid JSON."""
    try:
        _load_settings()
    except json.JSONDecodeError as exc:
        raise AssertionError(f".claude/settings.json is not valid JSON: {exc}") from exc


def test_settings_has_permissions_block():
    """settings.json must contain a top-level 'permissions' key."""
    data = _load_settings()
    assert "permissions" in data, "settings.json missing 'permissions' key"


def test_settings_has_allow_list():
    """settings.json permissions must contain an 'allow' list."""
    data = _load_settings()
    assert "allow" in data["permissions"], "settings.json missing permissions.allow"
    assert isinstance(data["permissions"]["allow"], list), (
        "permissions.allow must be a list"
    )


def test_settings_allow_list_covers_file_tools():
    """Allow list must pre-approve Read, Edit, Write, Glob, and Grep tools."""
    data = _load_settings()
    allowed = data["permissions"]["allow"]
    for tool in EXPECTED_ALLOWED_TOOLS:
        assert tool in allowed, f"permissions.allow missing expected tool: {tool}"


def test_settings_allow_list_covers_pytest():
    """Allow list must include a pattern for running pytest."""
    data = _load_settings()
    allowed = " ".join(data["permissions"]["allow"])
    assert "pytest" in allowed, "permissions.allow has no entry covering pytest"


def test_settings_allow_list_covers_git_read_commands():
    """Allow list must include patterns for safe git read commands."""
    data = _load_settings()
    allowed = " ".join(data["permissions"]["allow"])
    for cmd in ("git status", "git diff", "git log"):
        assert cmd in allowed, f"permissions.allow missing safe git command: {cmd}"


def test_settings_does_not_blanket_approve_bash():
    """Allow list must not contain a bare 'Bash' entry (blanket approval)."""
    data = _load_settings()
    allowed = data["permissions"]["allow"]
    assert "Bash" not in allowed, (
        "permissions.allow contains bare 'Bash' — this blanket-approves all shell commands"
    )


def test_settings_no_destructive_bash_patterns():
    """Allow list must not pre-approve destructive shell operations."""
    data = _load_settings()
    allowed_str = " ".join(data["permissions"]["allow"])
    for pattern in DESTRUCTIVE_PATTERNS:
        assert pattern not in allowed_str, (
            f"permissions.allow must not approve destructive pattern: {pattern!r}"
        )


def test_claude_md_references_settings_json():
    """CLAUDE.md must mention .claude/settings.json so developers know it exists."""
    with open(CLAUDE_MD) as f:
        content = f.read()
    assert "settings.json" in content, (
        "CLAUDE.md does not reference .claude/settings.json"
    )
