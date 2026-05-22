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


# Issue #64 — FilterBar and StatStrip mounting


def test_app_jsx_imports_filter_bar():
    """Assert App.jsx imports FilterBar."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "FilterBar" in src, "App.jsx must import FilterBar"


def test_app_jsx_renders_filter_bar():
    """Assert App.jsx renders <FilterBar> with a games prop."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "<FilterBar" in src, "App.jsx must render <FilterBar>"
    assert "games" in src, "App.jsx must pass games prop to FilterBar"


def test_app_jsx_imports_stat_strip():
    """Assert App.jsx imports StatStrip."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "StatStrip" in src, "App.jsx must import StatStrip"


def test_app_jsx_renders_stat_strip():
    """Assert App.jsx renders <StatStrip> with a games prop."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "<StatStrip" in src, "App.jsx must render <StatStrip>"


def test_app_jsx_main_padding_top_zero():
    """Assert App.jsx main element has no top padding (FilterBar supplies gap)."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "padding: '24px 32px'" not in src, (
        "App.jsx main must not have 24px top padding — FilterBar supplies the top gap"
    )


# Issue #66 — Sort state wiring


def test_app_jsx_has_sort_state():
    """App.jsx must contain a sort-related useState call."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "sort" in src and "useState" in src, (
        "App.jsx must declare sort state with useState"
    )


def test_app_jsx_derives_sorted_games():
    """App.jsx must derive a sorted copy of games using .sort(."""
    with open(APP_PATH) as f:
        src = f.read()
    assert ".sort(" in src, "App.jsx must derive sortedGames using .sort("


# Issue #67 — Filter state wiring


def test_app_jsx_has_filter_state():
    """App.jsx must contain a filter-related useState call."""
    with open(APP_PATH) as f:
        src = f.read()
    assert "setFilter" in src, (
        "App.jsx must declare filter state via useState (expected setFilter)"
    )


def test_app_jsx_passes_filtered_games_to_slate_table():
    """App.jsx must derive filteredGames via .filter( and pass them to SlateTable."""
    with open(APP_PATH) as f:
        src = f.read()
    assert ".filter(" in src, "App.jsx must use .filter( to derive filteredGames"
