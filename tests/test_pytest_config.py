"""Tests for pytest.ini configuration (Issue #51).

Verifies that pytest.ini includes fail-fast, short tracebacks, and a minimum
coverage threshold so failures are obvious and coverage cannot silently erode.
"""

import os
import configparser

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTEST_INI = os.path.join(REPO_ROOT, "pytest.ini")


def _load_addopts() -> str:
    """Return the addopts string from pytest.ini, or empty string if absent."""
    cfg = configparser.ConfigParser()
    cfg.read(PYTEST_INI)
    return cfg.get("pytest", "addopts", fallback="")


def test_pytest_ini_exists():
    """pytest.ini must exist at the repository root."""
    assert os.path.isfile(PYTEST_INI), "pytest.ini not found at repo root"


def test_pytest_ini_has_fail_fast():
    """addopts must include -x so pytest stops on the first failure."""
    addopts = _load_addopts()
    assert "-x" in addopts.split(), (
        f"pytest.ini addopts missing -x (fail-fast); got: {addopts!r}"
    )


def test_pytest_ini_has_short_tracebacks():
    """addopts must include --tb=short for compact failure output."""
    addopts = _load_addopts()
    assert "--tb=short" in addopts, (
        f"pytest.ini addopts missing --tb=short; got: {addopts!r}"
    )


def test_pytest_ini_has_coverage_minimum():
    """addopts must include --cov-fail-under to enforce a coverage floor."""
    addopts = _load_addopts()
    assert "--cov-fail-under" in addopts, (
        f"pytest.ini addopts missing --cov-fail-under; got: {addopts!r}"
    )


def test_pytest_ini_coverage_floor_is_at_least_80():
    """Coverage floor must be set to 80 or higher."""
    addopts = _load_addopts()
    for token in addopts.split():
        if token.startswith("--cov-fail-under="):
            floor = int(token.split("=", 1)[1])
            assert floor >= 80, (
                f"Coverage floor is {floor}; must be at least 80"
            )
            return
    raise AssertionError(
        "--cov-fail-under=N not found in pytest.ini addopts; "
        f"got: {addopts!r}"
    )
