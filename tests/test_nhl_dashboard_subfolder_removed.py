"""Tests verifying the nhl-dashboard/ subfolder is fully removed (Issue #85)."""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EXEMPT_PREFIXES = (
    os.path.join(REPO_ROOT, "memory"),
    os.path.join(REPO_ROOT, "docs"),
    os.path.join(REPO_ROOT, "tests"),
    os.path.join(REPO_ROOT, "logs"),
)


def test_nhl_dashboard_directory_does_not_exist():
    """nhl-dashboard/ must be deleted — no ambiguous parallel app structure."""
    nhl_dir = os.path.join(REPO_ROOT, "nhl-dashboard")
    assert not os.path.exists(nhl_dir), (
        f"nhl-dashboard/ still exists at {nhl_dir} — delete the entire directory tree"
    )


def test_no_non_exempt_files_reference_nhl_dashboard():
    """No file outside memory/, docs/, or tests/ may reference nhl-dashboard/ paths."""
    offenders = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # Skip hidden dirs, __pycache__, and exempt prefixes
        dirnames[:] = [
            d for d in dirnames
            if d not in {".git", "__pycache__", "node_modules", ".venv"}
        ]
        if any(dirpath.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            continue
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    if "nhl-dashboard/" in fh.read():
                        offenders.append(os.path.relpath(filepath, REPO_ROOT))
            except (OSError, PermissionError):
                pass

    assert offenders == [], (
        "These non-exempt files still reference nhl-dashboard/:\n"
        + "\n".join(f"  {f}" for f in offenders)
    )
