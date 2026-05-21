"""Tests for the GitHub Actions CI workflow file (Issue #48)."""

import os

WORKFLOW_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".github", "workflows", "ci.yml"
)


def _load_workflow() -> str:
    with open(WORKFLOW_PATH) as f:
        return f.read()


def test_ci_workflow_file_exists():
    """The workflow file must exist at .github/workflows/ci.yml."""
    assert os.path.isfile(WORKFLOW_PATH), f"Missing workflow file: {WORKFLOW_PATH}"


def test_ci_workflow_triggers_on_push():
    """Workflow must trigger on push events."""
    content = _load_workflow()
    assert "push:" in content or "push:" in content.replace(" ", "")


def test_ci_workflow_triggers_on_pull_request():
    """Workflow must trigger on pull_request events."""
    content = _load_workflow()
    assert "pull_request:" in content


def test_ci_workflow_targets_main_branch():
    """Workflow triggers must include the main branch."""
    content = _load_workflow()
    assert "main" in content


def test_ci_workflow_installs_dependencies():
    """Workflow must install Python dependencies via pip."""
    content = _load_workflow()
    assert "pip install" in content


def test_ci_workflow_runs_pytest():
    """Workflow must execute pytest."""
    content = _load_workflow()
    assert "pytest" in content
