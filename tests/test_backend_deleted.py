"""Tests verifying nhl-dashboard/backend/ source directory is removed (Issue #81)."""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_nhl_dashboard_backend_directory_does_not_exist():
    """nhl-dashboard/backend/ must be deleted — no orphaned Flask app code."""
    backend_dir = os.path.join(REPO_ROOT, "nhl-dashboard", "backend")
    assert not os.path.exists(backend_dir), (
        f"nhl-dashboard/backend/ still exists at {backend_dir} — delete it"
    )
