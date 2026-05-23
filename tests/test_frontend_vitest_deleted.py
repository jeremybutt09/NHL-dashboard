"""Tests verifying nhl-dashboard/frontend/src/__tests__/ Vitest files are removed (Issue #83)."""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(REPO_ROOT, "nhl-dashboard", "frontend", "src", "__tests__")


def test_vitest_tests_directory_does_not_exist():
    """__tests__/ directory must be deleted — no orphaned Vitest test files."""
    assert not os.path.exists(TESTS_DIR), (
        f"nhl-dashboard/frontend/src/__tests__/ still exists at {TESTS_DIR} — delete it"
    )


def test_edge_cell_test_file_does_not_exist():
    """EdgeCell.test.jsx must be removed along with the frontend cleanup."""
    path = os.path.join(TESTS_DIR, "EdgeCell.test.jsx")
    assert not os.path.exists(path), (
        f"EdgeCell.test.jsx still exists at {path} — delete it"
    )


def test_error_toast_test_file_does_not_exist():
    """ErrorToast.test.jsx must be removed along with the frontend cleanup."""
    path = os.path.join(TESTS_DIR, "ErrorToast.test.jsx")
    assert not os.path.exists(path), (
        f"ErrorToast.test.jsx still exists at {path} — delete it"
    )


def test_filter_bar_test_file_does_not_exist():
    """FilterBar.test.jsx must be removed along with the frontend cleanup."""
    path = os.path.join(TESTS_DIR, "FilterBar.test.jsx")
    assert not os.path.exists(path), (
        f"FilterBar.test.jsx still exists at {path} — delete it"
    )


def test_stat_strip_test_file_does_not_exist():
    """StatStrip.test.jsx must be removed along with the frontend cleanup."""
    path = os.path.join(TESTS_DIR, "StatStrip.test.jsx")
    assert not os.path.exists(path), (
        f"StatStrip.test.jsx still exists at {path} — delete it"
    )
