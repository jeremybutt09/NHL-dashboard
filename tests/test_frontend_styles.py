"""Tests for extracted frontend CSS tokens and component styles (Issue #43)."""
import re
import pathlib

STYLES_DIR = (
    pathlib.Path(__file__).parent.parent
    / "nhl-dashboard"
    / "frontend"
    / "src"
    / "styles"
)


def test_tokens_css_contains_root_block():
    tokens = (STYLES_DIR / "tokens.css").read_text()
    assert ":root" in tokens
    assert "--bg" in tokens
    assert "--ink" in tokens


def test_tokens_css_contains_dark_block():
    tokens = (STYLES_DIR / "tokens.css").read_text()
    assert ".dark" in tokens


def test_app_css_contains_game_row():
    app_css = (STYLES_DIR / "app.css").read_text()
    assert ".game-row" in app_css


def test_app_css_contains_shimmer_keyframes():
    app_css = (STYLES_DIR / "app.css").read_text()
    assert "@keyframes" in app_css
    assert "bar-shimmer" in app_css


def test_no_hardcoded_hex_in_app_css():
    app_css = (STYLES_DIR / "app.css").read_text()
    no_comments = re.sub(r"/\*.*?\*/", "", app_css, flags=re.DOTALL)
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", no_comments), (
        "app.css contains hardcoded hex color values"
    )
