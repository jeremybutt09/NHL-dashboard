"""Tests for FilterBar.jsx sort wiring (Issue #66)."""
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
