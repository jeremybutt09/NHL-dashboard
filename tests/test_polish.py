"""Tests for Issue #46 polish features: empty state, loading skeletons, error toast, density CSS."""
import os

FRONTEND_SRC = os.path.join(
    os.path.dirname(__file__), "..", "nhl-dashboard", "frontend", "src"
)

SLATE_TABLE_PATH = os.path.join(FRONTEND_SRC, "components", "SlateTable.jsx")
APP_PATH = os.path.join(FRONTEND_SRC, "App.jsx")
APP_CSS_PATH = os.path.join(FRONTEND_SRC, "styles", "app.css")
TOPBAR_PATH = os.path.join(FRONTEND_SRC, "components", "Topbar.jsx")
COMPONENTS_DIR = os.path.join(FRONTEND_SRC, "components")


def test_slate_table_jsx_has_empty_state():
    """Assert SlateTable.jsx contains a conditional branch for empty games array."""
    with open(SLATE_TABLE_PATH) as f:
        src = f.read()
    has_empty_check = (
        "No games" in src
        or "games.length" in src
        or "games?.length" in src
        or "length === 0" in src
    )
    assert has_empty_check, "SlateTable.jsx must contain a conditional branch for empty games array"


def test_app_jsx_renders_loading_skeleton():
    """Assert App.jsx or SlateTable.jsx references 'loading' and 'shimmer' (or 'skeleton')."""
    with open(APP_PATH) as f:
        app_src = f.read()
    with open(SLATE_TABLE_PATH) as f:
        slate_src = f.read()
    combined = app_src + slate_src
    assert "loading" in combined, "App.jsx or SlateTable.jsx must reference 'loading'"
    assert "shimmer" in combined or "skeleton" in combined.lower(), (
        "App.jsx or SlateTable.jsx must reference 'shimmer' or 'skeleton'"
    )


def test_error_toast_component_exists():
    """Assert ErrorToast.jsx exists in the components/ directory."""
    toast_path = os.path.join(COMPONENTS_DIR, "ErrorToast.jsx")
    assert os.path.isfile(toast_path), f"ErrorToast.jsx not found at {toast_path}"


def test_app_css_has_density_overrides():
    """Assert app.css contains [data-density='compact'] and [data-density='comfy'] selectors."""
    with open(APP_CSS_PATH) as f:
        src = f.read()
    assert 'data-density="compact"' in src or "data-density='compact'" in src, (
        'app.css must contain [data-density="compact"] selector'
    )
    assert 'data-density="comfy"' in src or "data-density='comfy'" in src, (
        'app.css must contain [data-density="comfy"] selector'
    )


def test_topbar_density_toggle_has_three_values():
    """Assert Topbar.jsx references all three density values: compact, regular, and comfy."""
    with open(TOPBAR_PATH) as f:
        src = f.read()
    assert "compact" in src, "Topbar.jsx must reference 'compact'"
    assert "regular" in src, "Topbar.jsx must reference 'regular'"
    assert "comfy" in src, "Topbar.jsx must reference 'comfy'"
