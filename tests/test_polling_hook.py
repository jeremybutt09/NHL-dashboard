"""Tests for the usePolling hook source file."""
import os

HOOK_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "nhl-dashboard", "frontend", "src", "hooks", "usePolling.js"
)


def test_use_polling_js_exists():
    """Assert usePolling.js exists at the expected path."""
    assert os.path.isfile(HOOK_PATH), f"usePolling.js not found at {HOOK_PATH}"


def test_use_polling_pauses_on_hidden():
    """Assert usePolling.js references visibilityState or visibilitychange."""
    with open(HOOK_PATH) as f:
        src = f.read()
    assert "visibilityState" in src or "visibilitychange" in src, (
        "usePolling.js must pause polling when tab is hidden "
        "(reference visibilityState or visibilitychange)"
    )
