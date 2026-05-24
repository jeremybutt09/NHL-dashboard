"""Tests for .gitignore consolidation (Issue #104)."""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_GITIGNORE = os.path.join(REPO_ROOT, ".gitignore")
SUBDIR_GITIGNORE = os.path.join(REPO_ROOT, "nhl-dashboard", ".gitignore")

REQUIRED_PATTERNS = [
    "*.db",
    "nhl-dashboard/backend/instance/nhl.db",
    "node_modules/",
    "nhl-dashboard/frontend/.vite/",
    ".env.local",
    ".env.*.local",
    ".DS_Store",
    "Thumbs.db",
    "nhl-dashboard/frontend/coverage/",
]


def _load_root_gitignore() -> list[str]:
    with open(ROOT_GITIGNORE) as f:
        return [line.strip() for line in f.read().splitlines()]


def test_root_gitignore_contains_sqlite_db_pattern():
    """Root .gitignore must ignore *.db files."""
    lines = _load_root_gitignore()
    assert "*.db" in lines, "*.db missing from root .gitignore"


def test_root_gitignore_contains_explicit_nhl_db_path():
    """Root .gitignore must explicitly ignore the app's runtime SQLite database."""
    lines = _load_root_gitignore()
    assert "nhl-dashboard/backend/instance/nhl.db" in lines, (
        "nhl-dashboard/backend/instance/nhl.db missing from root .gitignore"
    )


def test_root_gitignore_contains_node_modules():
    """Root .gitignore must ignore node_modules/."""
    lines = _load_root_gitignore()
    assert "node_modules/" in lines, "node_modules/ missing from root .gitignore"


def test_root_gitignore_contains_vite_cache():
    """Root .gitignore must ignore the Vite dev-server cache directory."""
    lines = _load_root_gitignore()
    assert "nhl-dashboard/frontend/.vite/" in lines, (
        "nhl-dashboard/frontend/.vite/ missing from root .gitignore"
    )


def test_root_gitignore_contains_env_local():
    """Root .gitignore must ignore .env.local files."""
    lines = _load_root_gitignore()
    assert ".env.local" in lines, ".env.local missing from root .gitignore"


def test_root_gitignore_contains_env_local_variants():
    """Root .gitignore must ignore .env.*.local pattern."""
    lines = _load_root_gitignore()
    assert ".env.*.local" in lines, ".env.*.local missing from root .gitignore"


def test_root_gitignore_contains_ds_store():
    """Root .gitignore must ignore macOS .DS_Store metadata files."""
    lines = _load_root_gitignore()
    assert ".DS_Store" in lines, ".DS_Store missing from root .gitignore"


def test_root_gitignore_contains_thumbs_db():
    """Root .gitignore must ignore Windows Thumbs.db metadata files."""
    lines = _load_root_gitignore()
    assert "Thumbs.db" in lines, "Thumbs.db missing from root .gitignore"


def test_root_gitignore_contains_frontend_coverage():
    """Root .gitignore must ignore the frontend Jest/Vitest coverage output directory."""
    lines = _load_root_gitignore()
    assert "nhl-dashboard/frontend/coverage/" in lines, (
        "nhl-dashboard/frontend/coverage/ missing from root .gitignore"
    )


def test_subdirectory_gitignore_deleted():
    """nhl-dashboard/.gitignore must not exist — root is the single source of truth."""
    assert not os.path.exists(SUBDIR_GITIGNORE), (
        "nhl-dashboard/.gitignore still exists; it should be deleted after merging entries"
    )


def test_frontend_coverage_not_tracked_by_git():
    """nhl-dashboard/frontend/coverage/ must not appear as an untracked path in git status."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "nhl-dashboard/frontend/coverage/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", (
        "nhl-dashboard/frontend/coverage/ still surfaced by git status"
    )
