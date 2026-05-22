"""Tests for extracted frontend CSS tokens and component styles (Issues #43, #60)."""
import re
import pathlib

STYLES_DIR = (
    pathlib.Path(__file__).parent.parent
    / "nhl-dashboard"
    / "frontend"
    / "src"
    / "styles"
)

COMPONENTS_DIR = (
    pathlib.Path(__file__).parent.parent
    / "nhl-dashboard"
    / "frontend"
    / "src"
    / "components"
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


# ── Issue #60 design-match tests ─────────────────────────────────────────────

def test_app_css_game_row_has_default_background():
    """`.game-row` must declare `background: var(--paper)` so the CSS hover rule
    can override it without being beaten by an always-on inline style."""
    app_css = (STYLES_DIR / "app.css").read_text()
    assert "background: var(--paper)" in app_css, (
        ".game-row must set background: var(--paper) in app.css"
    )


def test_app_css_game_row_has_cursor_pointer():
    """`.game-row` must declare `cursor: pointer` so the whole row shows
    the pointer cursor, matching the reference prototype."""
    app_css = (STYLES_DIR / "app.css").read_text()
    assert "cursor: pointer" in app_css, (
        ".game-row must include cursor: pointer in app.css"
    )


def test_app_css_has_pulse_dot_keyframes():
    """The `@keyframes pulse-dot` animation must exist for the live indicator dot."""
    app_css = (STYLES_DIR / "app.css").read_text()
    assert "@keyframes pulse-dot" in app_css


def test_slate_table_edge_header_right_aligned():
    """The 'Edge' and 'Details' column headers in SlateTable must use
    textAlign right to match the reference prototype."""
    content = (COMPONENTS_DIR / "SlateTable.jsx").read_text()
    assert "textAlign: 'right'" in content, (
        "SlateTable.jsx must use textAlign: 'right' for Edge/Details column headers"
    )


def test_game_row_no_unconditional_paper_background():
    """GameRow must not apply background: var(--paper) as an unconditional
    inline style — the default background must come from the CSS class so
    hover can override it."""
    content = (COMPONENTS_DIR / "GameRow.jsx").read_text()
    assert "background: 'var(--paper)'" not in content, (
        "GameRow.jsx must not set background: 'var(--paper)' as an inline style; "
        "use the CSS class instead so hover works correctly"
    )


def test_topbar_sets_data_density_on_mount():
    """Topbar must call setAttribute('data-density', ...) on initial mount so
    the CSS [data-density] density rules apply from the first render."""
    content = (COMPONENTS_DIR / "Topbar.jsx").read_text()
    assert "setAttribute('data-density'" in content, (
        "Topbar.jsx must set data-density attribute on mount"
    )


def test_index_html_has_geist_font_links():
    """index.html must include Geist and Geist Mono font preconnect/stylesheet
    links from Google Fonts."""
    index_html = (
        pathlib.Path(__file__).parent.parent
        / "nhl-dashboard"
        / "frontend"
        / "index.html"
    ).read_text()
    assert "Geist" in index_html, "index.html must link Geist font"
    assert "Geist+Mono" in index_html, "index.html must link Geist Mono font"
    assert "fonts.googleapis.com" in index_html


# ── Issue #65 FilterBar and StatStrip className refactor ─────────────────────

_FILTER_BAR_CLASSES = [
    ".filter-bar",
    ".filter-bar-title",
    ".filter-bar-controls",
    ".segment-btn",
]

_STAT_STRIP_CLASSES = [
    ".stat-strip",
    ".stat-card",
    ".stat-card-label",
    ".stat-card-value",
]


def test_app_css_contains_filter_bar_classes():
    """app.css must define all FilterBar layout classes."""
    app_css = (STYLES_DIR / "app.css").read_text()
    for cls in _FILTER_BAR_CLASSES:
        assert cls in app_css, f"app.css must contain {cls}"


def test_app_css_contains_stat_strip_classes():
    """app.css must define all StatStrip layout classes."""
    app_css = (STYLES_DIR / "app.css").read_text()
    for cls in _STAT_STRIP_CLASSES:
        assert cls in app_css, f"app.css must contain {cls}"


# ── Issue #68 sticky header top offset ───────────────────────────────────────

def test_tokens_css_defines_topbar_height():
    """tokens.css must define --topbar-h so the SlateTable header offset
    can be adjusted in one place."""
    tokens = (STYLES_DIR / "tokens.css").read_text()
    assert "--topbar-h" in tokens, "tokens.css must define the --topbar-h CSS variable"
