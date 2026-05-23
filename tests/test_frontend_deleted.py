"""Tests verifying nhl-dashboard/frontend/ source directory is removed (Issue #82)."""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_nhl_dashboard_frontend_directory_does_not_exist():
    """nhl-dashboard/frontend/ must be deleted — no orphaned React application code."""
    frontend_dir = os.path.join(REPO_ROOT, "nhl-dashboard", "frontend")
    assert not os.path.exists(frontend_dir), (
        f"nhl-dashboard/frontend/ still exists at {frontend_dir} — delete it"
    )


def test_nhl_dashboard_readme_does_not_exist():
    """nhl-dashboard/README.md must be deleted along with the frontend cleanup."""
    readme = os.path.join(REPO_ROOT, "nhl-dashboard", "README.md")
    assert not os.path.exists(readme), (
        f"nhl-dashboard/README.md still exists at {readme} — delete it"
    )


def test_nhl_dashboard_gitignore_does_not_exist():
    """nhl-dashboard/.gitignore must be deleted along with the frontend cleanup."""
    gitignore = os.path.join(REPO_ROOT, "nhl-dashboard", ".gitignore")
    assert not os.path.exists(gitignore), (
        f"nhl-dashboard/.gitignore still exists at {gitignore} — delete it"
    )


def test_nhl_dashboard_directory_is_empty_or_removed():
    """nhl-dashboard/ directory must be empty or fully removed after frontend deletion."""
    nhl_dir = os.path.join(REPO_ROOT, "nhl-dashboard")
    if not os.path.exists(nhl_dir):
        return
    remaining = list(os.listdir(nhl_dir))
    assert remaining == [], (
        f"nhl-dashboard/ still contains files: {remaining} — remove them"
    )
