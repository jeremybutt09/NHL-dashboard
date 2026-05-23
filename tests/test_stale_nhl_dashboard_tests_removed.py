"""Tests verifying stale test files referencing nhl-dashboard/ are removed (Issue #86)."""

import os

TESTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))


def test_app_shell_test_file_does_not_exist():
    """test_app_shell.py must be removed — it references deleted nhl-dashboard/frontend/ paths."""
    path = os.path.join(TESTS_DIR, "test_app_shell.py")
    assert not os.path.exists(path), (
        f"test_app_shell.py still exists at {path} — delete it"
    )


def test_polish_test_file_does_not_exist():
    """test_polish.py must be removed — it references deleted nhl-dashboard/frontend/ paths."""
    path = os.path.join(TESTS_DIR, "test_polish.py")
    assert not os.path.exists(path), (
        f"test_polish.py still exists at {path} — delete it"
    )
