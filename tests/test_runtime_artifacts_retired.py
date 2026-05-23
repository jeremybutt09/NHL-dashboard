"""Tests verifying memory/, logs/, and other gitignored runtime artifacts are removed (Issue #80)."""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_memory_directory_does_not_exist():
    """The memory/ directory should be deleted as part of project retirement."""
    memory_dir = os.path.join(REPO_ROOT, "memory")
    assert not os.path.exists(memory_dir), (
        f"memory/ directory still exists at {memory_dir} — delete it for retirement"
    )


def test_logs_directory_does_not_exist():
    """The logs/ directory and all issue log files should be deleted for retirement."""
    logs_dir = os.path.join(REPO_ROOT, "logs")
    assert not os.path.exists(logs_dir), (
        f"logs/ directory still exists at {logs_dir} — delete it for retirement"
    )


def test_no_log_files_under_project_root():
    """No .log files should remain anywhere under the project root."""
    result = subprocess.run(
        ["find", ".", "-not", "-path", "./.git/*", "-name", "*.log"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    found = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert found == [], (
        "Log files found under project root (must be deleted):\n" + "\n".join(found)
    )


def test_memory_not_tracked_in_git():
    """No files under memory/ should be tracked in the git index."""
    result = subprocess.run(
        ["git", "ls-files", "memory/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.strip()
    assert tracked == "", f"memory/ files still tracked by git:\n{tracked}"


def test_logs_not_tracked_in_git():
    """No files under logs/ should be tracked in the git index."""
    result = subprocess.run(
        ["git", "ls-files", "logs/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.strip()
    assert tracked == "", f"logs/ files still tracked by git:\n{tracked}"


def test_gitignore_covers_memory_and_logs():
    """.gitignore must contain entries for both memory/ and logs/issues/."""
    gitignore_path = os.path.join(REPO_ROOT, ".gitignore")
    with open(gitignore_path) as fh:
        content = fh.read()
    required = ["memory/", "logs/issues/"]
    missing = [p for p in required if p not in content]
    assert missing == [], f"Patterns missing from .gitignore: {missing}"
