"""Tests for memory/ gitignore exclusion (Issue #52)."""

import os
import subprocess

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
GITIGNORE_PATH = os.path.join(REPO_ROOT, ".gitignore")


def _load_gitignore() -> str:
    with open(GITIGNORE_PATH) as f:
        return f.read()


def test_gitignore_contains_memory_entry():
    """The .gitignore must contain an entry that excludes the memory/ directory."""
    content = _load_gitignore()
    lines = [line.strip() for line in content.splitlines()]
    assert "memory/" in lines, "memory/ entry missing from .gitignore"


def test_memory_files_not_in_git_index():
    """No files under memory/ should be tracked in the git index."""
    result = subprocess.run(
        ["git", "ls-files", "memory/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.strip()
    assert tracked == "", f"memory/ files still tracked by git:\n{tracked}"


def test_agents_md_documents_memory_gitignore():
    """harness/AGENTS.md or CLAUDE.md must mention that memory/ is gitignored."""
    agents_path = os.path.join(REPO_ROOT, "harness", "AGENTS.md")
    claude_path = os.path.join(REPO_ROOT, "CLAUDE.md")

    agents_content = open(agents_path).read() if os.path.isfile(agents_path) else ""
    claude_content = open(claude_path).read() if os.path.isfile(claude_path) else ""

    combined = agents_content + claude_content
    assert "memory/" in combined and (
        "gitignore" in combined.lower() or "git-ignored" in combined.lower()
    ), "No documentation found in AGENTS.md or CLAUDE.md explaining that memory/ is gitignored"
