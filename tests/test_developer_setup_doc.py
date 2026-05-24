"""Tests verifying docs/developer-setup.md exists and has required sections."""

import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SETUP_GUIDE = os.path.join(REPO_ROOT, "docs", "developer-setup.md")


def _doc_text():
    with open(SETUP_GUIDE) as f:
        return f.read()


def test_developer_setup_doc_exists():
    """docs/developer-setup.md must exist at the repo root docs/ directory."""
    assert os.path.isfile(SETUP_GUIDE), "docs/developer-setup.md not found"


def test_backend_setup_section_present():
    """Doc must contain a 'Backend Setup' section."""
    text = _doc_text()
    assert "Backend Setup" in text, "'Backend Setup' section missing from developer-setup.md"


def test_frontend_setup_section_present():
    """Doc must contain a 'Frontend Setup' section."""
    text = _doc_text()
    assert "Frontend Setup" in text, "'Frontend Setup' section missing from developer-setup.md"


def test_troubleshooting_section_present():
    """Doc must contain a 'Troubleshooting' section."""
    text = _doc_text()
    assert "Troubleshooting" in text, "'Troubleshooting' section missing from developer-setup.md"


def test_configuration_section_present():
    """Doc must contain a 'Configuration' section."""
    text = _doc_text()
    assert "Configuration" in text, "'Configuration' section missing from developer-setup.md"
