"""Tests for AGENTS.md consolidation into a single source of truth (Issue #49)."""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_AGENTS = os.path.join(REPO_ROOT, "AGENTS.md")
HARNESS_AGENTS = os.path.join(REPO_ROOT, "harness", "AGENTS.md")
CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")


def test_agents_canonical_file_exists():
    """harness/AGENTS.md must exist as the single canonical instructions file."""
    assert os.path.isfile(HARNESS_AGENTS), "harness/AGENTS.md must exist"


def test_agents_root_is_stub_redirect():
    """Root AGENTS.md must be a short redirect stub, not a full spec."""
    with open(ROOT_AGENTS) as f:
        non_empty = [ln for ln in f.readlines() if ln.strip()]
    assert len(non_empty) <= 5, (
        f"Root AGENTS.md has {len(non_empty)} non-empty lines — "
        "expected a stub redirect of ≤5 lines"
    )


def test_agents_root_redirect_points_to_canonical():
    """Root AGENTS.md stub must reference harness/AGENTS.md."""
    with open(ROOT_AGENTS) as f:
        content = f.read()
    assert "harness/AGENTS.md" in content, (
        "Root AGENTS.md stub must point to harness/AGENTS.md"
    )


def test_claude_md_references_only_one_agents_file():
    """CLAUDE.md must not list both AGENTS.md files as separate reading items."""
    with open(CLAUDE_MD) as f:
        content = f.read()
    both_listed = ("- `AGENTS.md`" in content) and ("- `harness/AGENTS.md`" in content)
    assert not both_listed, (
        "CLAUDE.md still lists both AGENTS.md and harness/AGENTS.md as separate read items"
    )


def test_canonical_agents_contains_naming_conventions():
    """Canonical harness/AGENTS.md must document all naming conventions."""
    with open(HARNESS_AGENTS) as f:
        content = f.read()
    for term in ("snake_case", "PascalCase", "UPPER_SNAKE_CASE"):
        assert term in content, f"harness/AGENTS.md missing naming convention: {term}"


def test_canonical_agents_contains_tdd_workflow():
    """Canonical harness/AGENTS.md must describe the Red/Green/Refactor TDD workflow."""
    with open(HARNESS_AGENTS) as f:
        content = f.read()
    for step in ("Red", "Green", "Refactor"):
        assert step in content, f"harness/AGENTS.md missing TDD step: {step}"


def test_canonical_agents_contains_ambiguity_guidance():
    """Canonical harness/AGENTS.md must contain the 'document the assumption' rule."""
    with open(HARNESS_AGENTS) as f:
        content = f.read()
    assert "document the assumption" in content, (
        "harness/AGENTS.md missing 'document the assumption' guidance from root AGENTS.md"
    )


def test_canonical_agents_contains_modular_data_fetching():
    """Canonical harness/AGENTS.md must mention modular data-fetching."""
    with open(HARNESS_AGENTS) as f:
        content = f.read()
    assert "modular" in content.lower(), (
        "harness/AGENTS.md missing modular data-fetching guidance from root AGENTS.md"
    )
