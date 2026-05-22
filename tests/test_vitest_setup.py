"""Proxy tests confirming Vitest + Testing Library are wired up (Issue #74)."""
import json
import pathlib

FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "nhl-dashboard" / "frontend"
PKG_PATH = FRONTEND_DIR / "package.json"
VITE_CONFIG_PATH = FRONTEND_DIR / "vite.config.js"
VITEST_CONFIG_PATH = FRONTEND_DIR / "vitest.config.js"
TESTS_DIR = FRONTEND_DIR / "src" / "__tests__"
WORKFLOW_PATH = pathlib.Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"


def _pkg() -> dict:
    return json.loads(PKG_PATH.read_text())


def _config_content() -> str:
    """Return jsdom-bearing config file content (vite or vitest)."""
    if VITEST_CONFIG_PATH.exists():
        return VITEST_CONFIG_PATH.read_text()
    return VITE_CONFIG_PATH.read_text()


def test_vitest_in_devdependencies():
    """vitest must be listed in devDependencies."""
    pkg = _pkg()
    assert "vitest" in pkg.get("devDependencies", {}), (
        "vitest must be in devDependencies"
    )


def test_testing_library_react_in_devdependencies():
    """@testing-library/react must be listed in devDependencies."""
    pkg = _pkg()
    assert "@testing-library/react" in pkg.get("devDependencies", {}), (
        "@testing-library/react must be in devDependencies"
    )


def test_npm_test_script_exists():
    """package.json must have a 'test' script running vitest."""
    pkg = _pkg()
    scripts = pkg.get("scripts", {})
    assert "test" in scripts, "package.json must have a 'test' script"
    assert "vitest" in scripts["test"], "the 'test' script must invoke vitest"


def test_jsdom_test_environment_configured():
    """vite.config.js or vitest.config.js must configure test environment as jsdom."""
    content = _config_content()
    assert "jsdom" in content, (
        "vite.config.js or vitest.config.js must set test environment to jsdom"
    )


def test_filter_bar_test_file_exists():
    """FilterBar.test.jsx must exist in src/__tests__/."""
    assert (TESTS_DIR / "FilterBar.test.jsx").exists(), (
        "FilterBar.test.jsx must exist in src/__tests__/"
    )


def test_stat_strip_test_file_exists():
    """StatStrip.test.jsx must exist in src/__tests__/."""
    assert (TESTS_DIR / "StatStrip.test.jsx").exists(), (
        "StatStrip.test.jsx must exist in src/__tests__/"
    )


def test_edge_cell_test_file_exists():
    """EdgeCell.test.jsx must exist in src/__tests__/."""
    assert (TESTS_DIR / "EdgeCell.test.jsx").exists(), (
        "EdgeCell.test.jsx must exist in src/__tests__/"
    )


def test_error_toast_test_file_exists():
    """ErrorToast.test.jsx must exist in src/__tests__/."""
    assert (TESTS_DIR / "ErrorToast.test.jsx").exists(), (
        "ErrorToast.test.jsx must exist in src/__tests__/"
    )


def test_ci_has_frontend_test_job():
    """ci.yml must contain a frontend-test job."""
    content = WORKFLOW_PATH.read_text()
    assert "frontend-test" in content, "ci.yml must define a frontend-test job"


def test_ci_frontend_test_job_runs_npm_test():
    """The frontend-test CI job must run npm test or npm run test."""
    content = WORKFLOW_PATH.read_text()
    assert "npm test" in content or "npm run test" in content, (
        "ci.yml frontend-test job must run npm test or npm run test"
    )
