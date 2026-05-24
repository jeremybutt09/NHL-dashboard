"""Tests verifying docs/frontend-architecture.md exists and has required sections."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
FRONTEND_DOC = os.path.join(REPO_ROOT, "docs", "frontend-architecture.md")


def _doc_text():
    with open(FRONTEND_DOC) as f:
        return f.read()


def test_frontend_architecture_doc_exists():
    """docs/frontend-architecture.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(FRONTEND_DOC), "docs/frontend-architecture.md not found"


def test_component_tree_heading_present():
    """Doc must contain a 'Component Tree' heading."""
    text = _doc_text()
    assert "Component Tree" in text, "'Component Tree' heading missing from frontend-architecture.md"


def test_props_reference_heading_present():
    """Doc must contain a 'Props Reference' heading."""
    text = _doc_text()
    assert "Props Reference" in text, "'Props Reference' heading missing from frontend-architecture.md"


def test_polling_behavior_heading_present():
    """Doc must contain a 'Polling Behavior' heading."""
    text = _doc_text()
    assert "Polling Behavior" in text, "'Polling Behavior' heading missing from frontend-architecture.md"


def test_css_variables_heading_present():
    """Doc must contain a 'CSS Variables' heading."""
    text = _doc_text()
    assert "CSS Variables" in text, "'CSS Variables' heading missing from frontend-architecture.md"
