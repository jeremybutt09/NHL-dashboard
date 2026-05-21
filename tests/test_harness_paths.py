"""Tests that file paths in scripts/issue-prompt.md resolve to real files."""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROMPT_PATH = os.path.join(REPO_ROOT, "scripts", "issue-prompt.md")


def _extract_step0_paths(content):
    """Return file paths listed in the Step 0 section of issue-prompt.md.

    Args:
        content: Full text of the prompt file.

    Returns:
        List of path strings found inside backticks in the Step 0 section.
    """
    step0_match = re.search(r"## Step 0.*?## Step 1", content, re.DOTALL)
    if not step0_match:
        return []
    step0_text = step0_match.group(0)
    candidates = re.findall(r"`([^`]+)`", step0_text)
    return [c for c in candidates if "/" in c or "." in c]


def test_issue_prompt_step0_has_paths():
    """Step 0 section must list at least one file path."""
    with open(PROMPT_PATH) as f:
        content = f.read()
    paths = _extract_step0_paths(content)
    assert paths, "No file paths found in Step 0 section of scripts/issue-prompt.md"


def test_issue_prompt_step0_paths_all_exist():
    """Every file path listed in Step 0 of scripts/issue-prompt.md must exist."""
    with open(PROMPT_PATH) as f:
        content = f.read()
    paths = _extract_step0_paths(content)
    missing = [p for p in paths if not os.path.exists(os.path.join(REPO_ROOT, p))]
    assert missing == [], (
        f"Broken paths in scripts/issue-prompt.md Step 0: {missing}"
    )


def test_no_scripts_file_references_old_app_init():
    """No file in scripts/ should reference the non-existent app/__init__.py path."""
    scripts_dir = os.path.join(REPO_ROOT, "scripts")
    for fname in os.listdir(scripts_dir):
        fpath = os.path.join(scripts_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath) as f:
            text = f.read()
        assert "app/__init__.py" not in text, (
            f"{fname} still references the broken path 'app/__init__.py'"
        )


def test_no_scripts_file_references_old_agents_path():
    """No file in scripts/ should reference the non-existent app/agents/nhl_client.py."""
    scripts_dir = os.path.join(REPO_ROOT, "scripts")
    for fname in os.listdir(scripts_dir):
        fpath = os.path.join(scripts_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath) as f:
            text = f.read()
        assert "app/agents/nhl_client.py" not in text, (
            f"{fname} still references the broken path 'app/agents/nhl_client.py'"
        )
