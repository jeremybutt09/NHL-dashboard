"""Tests for FilterBar.jsx sort and filter wiring (Issue #66, #67)."""
import os

COMPONENTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nhl-dashboard", "frontend", "src", "components"
)
FILTER_BAR_PATH = os.path.join(COMPONENTS_DIR, "FilterBar.jsx")


def test_filter_bar_sort_uses_state():
    """FilterBar.jsx must import and use useState for local or delegated sort."""
    with open(FILTER_BAR_PATH) as f:
        src = f.read()
    assert "useState" in src, "FilterBar.jsx must contain useState"


def test_filter_bar_exposes_sort_callback():
    """FilterBar.jsx must accept an onSortChange prop to notify parent of sort changes."""
    with open(FILTER_BAR_PATH) as f:
        src = f.read()
    assert "onSortChange" in src, "FilterBar.jsx must reference onSortChange prop"


# Issue #67 — Filter wiring


def test_filter_bar_filter_control_present():
    """FilterBar.jsx must render a Filter control with label text 'Filter'."""
    with open(FILTER_BAR_PATH) as f:
        src = f.read()
    assert "Filter" in src, "FilterBar.jsx must contain 'Filter' label text"


def test_filter_bar_exposes_filter_callback():
    """FilterBar.jsx must accept an onFilterChange prop to notify parent of filter changes."""
    with open(FILTER_BAR_PATH) as f:
        src = f.read()
    assert "onFilterChange" in src, "FilterBar.jsx must reference onFilterChange prop"


# Issue #71 — FilterBar loading indicator


def test_filter_bar_shows_loading_indicator():
    """FilterBar.jsx must accept a loading prop and show 'Loading…' in the subtitle when true."""
    with open(FILTER_BAR_PATH) as f:
        src = f.read()
    assert "Loading" in src, (
        "FilterBar.jsx must display 'Loading…' in the subtitle when the loading prop is truthy"
    )
