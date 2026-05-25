"""Tests verifying the frontend-design skill is installed in .claude/skills/ (Issue #125)."""

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILL_DIR = os.path.join(REPO_ROOT, ".claude", "skills", "frontend-design")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
LICENSE_TXT = os.path.join(SKILL_DIR, "LICENSE.txt")


def test_frontend_design_skill_directory_exists():
    """frontend-design skill directory must exist at .claude/skills/frontend-design/."""
    assert os.path.isdir(SKILL_DIR), (
        f"frontend-design skill directory not found at {SKILL_DIR}"
    )


def test_frontend_design_skill_md_exists():
    """SKILL.md must be present inside the frontend-design skill directory."""
    assert os.path.isfile(SKILL_MD), f"SKILL.md not found at {SKILL_MD}"


def test_frontend_design_skill_md_has_name_frontmatter():
    """SKILL.md must declare name: frontend-design in its frontmatter."""
    with open(SKILL_MD) as f:
        content = f.read()
    assert "name: frontend-design" in content, (
        "SKILL.md frontmatter missing 'name: frontend-design'"
    )


def test_frontend_design_skill_md_has_description():
    """SKILL.md must include a non-empty description field."""
    with open(SKILL_MD) as f:
        content = f.read()
    assert "description:" in content, "SKILL.md frontmatter missing 'description' field"


def test_frontend_design_license_exists():
    """LICENSE.txt must be present alongside SKILL.md."""
    assert os.path.isfile(LICENSE_TXT), f"LICENSE.txt not found at {LICENSE_TXT}"
