"""Tests for App.jsx shell and Topbar.jsx component."""
import os

FRONTEND_SRC = os.path.join(
    os.path.dirname(__file__), "..", "nhl-dashboard", "frontend", "src"
)

APP_PATH = os.path.join(FRONTEND_SRC, "App.jsx")
TOPBAR_PATH = os.path.join(FRONTEND_SRC, "components", "Topbar.jsx")


def test_app_jsx_calls_use_polling():
    """Assert App.jsx imports and calls usePolling."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "usePolling" in src, "App.jsx must call usePolling"


def test_app_jsx_renders_topbar_and_slate_table():
    """Assert App.jsx references both Topbar and SlateTable."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "Topbar" in src, "App.jsx must render <Topbar>"
    assert "SlateTable" in src, "App.jsx must render <SlateTable>"


def test_topbar_jsx_toggles_dark_class():
    """Assert Topbar.jsx toggles dark class and uses localStorage."""
    with open(TOPBAR_PATH) as f:
        src = f.read()
    assert "dark" in src, "Topbar.jsx must reference 'dark' class toggle"
    assert "localStorage" in src, "Topbar.jsx must persist dark mode in localStorage"


def test_topbar_jsx_density_toggle_present():
    """Assert Topbar.jsx includes a density toggle."""
    with open(TOPBAR_PATH) as f:
        src = f.read()
    assert "density" in src, "Topbar.jsx must reference density toggle"
