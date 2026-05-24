"""Tests verifying docs/testing-guide.md exists and has required sections."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
TESTING_GUIDE = os.path.join(REPO_ROOT, "docs", "testing-guide.md")


def _doc_text():
    with open(TESTING_GUIDE) as f:
        return f.read()


def test_testing_guide_doc_exists():
    """docs/testing-guide.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(TESTING_GUIDE), "docs/testing-guide.md not found"


def test_backend_tests_section_present():
    """Doc must contain a 'Backend Tests' section."""
    text = _doc_text()
    assert "Backend Tests" in text, "'Backend Tests' section missing from testing-guide.md"


def test_frontend_tests_section_present():
    """Doc must contain a 'Frontend Tests' section."""
    text = _doc_text()
    assert "Frontend Tests" in text, "'Frontend Tests' section missing from testing-guide.md"


def test_coverage_section_present():
    """Doc must contain a 'Coverage' section."""
    text = _doc_text()
    assert "Coverage" in text, "'Coverage' section missing from testing-guide.md"


def test_fixtures_section_present():
    """Doc must contain a 'Fixtures' section."""
    text = _doc_text()
    assert "Fixtures" in text, "'Fixtures' section missing from testing-guide.md"
