"""Tests for React component files ported from handoff 2 Dashboard.html (Issue #44)."""
import pathlib

COMPONENTS_DIR = (
    pathlib.Path(__file__).parent.parent
    / "nhl-dashboard"
    / "frontend"
    / "src"
    / "components"
)

COMPONENT_FILES = [
    "TeamGlyph.jsx",
    "LiveDot.jsx",
    "Sparkline.jsx",
    "ImpliedBar.jsx",
    "StatusCell.jsx",
    "MatchupCell.jsx",
    "MoneylineCell.jsx",
    "SparklineCell.jsx",
    "EdgeCell.jsx",
    "SlateTable.jsx",
    "GameRow.jsx",
]


def test_all_component_files_exist():
    for name in COMPONENT_FILES:
        path = COMPONENTS_DIR / name
        assert path.exists(), f"Missing component: {name}"
        content = path.read_text()
        assert "export default function" in content, (
            f"{name} must contain a default exported function"
        )


def test_slate_table_jsx_imports_game_row():
    content = (COMPONENTS_DIR / "SlateTable.jsx").read_text()
    assert "GameRow" in content, "SlateTable.jsx must reference GameRow"


def test_game_row_jsx_imports_all_cells():
    content = (COMPONENTS_DIR / "GameRow.jsx").read_text()
    for cell in ["StatusCell", "MatchupCell", "MoneylineCell", "SparklineCell", "EdgeCell"]:
        assert cell in content, f"GameRow.jsx must reference {cell}"


def test_sparkline_jsx_uses_svg():
    content = (COMPONENTS_DIR / "Sparkline.jsx").read_text()
    assert "svg" in content, "Sparkline.jsx must use an SVG element"


def test_team_glyph_uses_proxy_url():
    content = (COMPONENTS_DIR / "TeamGlyph.jsx").read_text()
    assert "/api/logos/" in content, (
        "TeamGlyph.jsx must use the backend proxy URL instead of the direct CDN"
    )


# Issue #61 — StatusCell ET time formatting
STATUS_CELL = COMPONENTS_DIR / "StatusCell.jsx"


def test_status_cell_uses_intl_date_time_format():
    content = STATUS_CELL.read_text()
    assert "Intl.DateTimeFormat" in content, (
        "StatusCell.jsx must use Intl.DateTimeFormat to format start time"
    )


def test_status_cell_uses_america_new_york_timezone():
    content = STATUS_CELL.read_text()
    assert "America/New_York" in content, (
        "StatusCell.jsx must use America/New_York timezone for ET formatting"
    )


def test_status_cell_shows_et_label():
    content = STATUS_CELL.read_text()
    assert "ET" in content, (
        "StatusCell.jsx must display 'ET' timezone label next to the time"
    )


def test_status_cell_shows_tonight_label():
    content = STATUS_CELL.read_text()
    assert "TONIGHT" in content, (
        "StatusCell.jsx must display 'TONIGHT' for same-day games"
    )


def test_status_cell_shows_tomorrow_label():
    content = STATUS_CELL.read_text()
    assert "TOMORROW" in content, (
        "StatusCell.jsx must display 'TOMORROW' for next-day games"
    )


def test_status_cell_handles_null_start():
    content = STATUS_CELL.read_text()
    assert "null" in content or "g.start" in content, (
        "StatusCell.jsx must guard against null g.start"
    )
    # The fallback dash character must be present
    assert "—" in content or '"—"' in content or "'—'" in content, (
        "StatusCell.jsx must show em-dash for null start time"
    )


def test_status_cell_no_g_tz_reference():
    content = STATUS_CELL.read_text()
    assert "g.tz" not in content, (
        "StatusCell.jsx must not reference g.tz (field does not exist in API shape)"
    )


# Issue #64 — FilterBar and StatStrip component files exist


def test_filter_bar_component_exists():
    path = COMPONENTS_DIR / "FilterBar.jsx"
    assert path.exists(), "FilterBar.jsx must exist in components/"
    content = path.read_text()
    assert "export default function FilterBar" in content, (
        "FilterBar.jsx must export a default FilterBar function"
    )


def test_stat_strip_component_exists():
    path = COMPONENTS_DIR / "StatStrip.jsx"
    assert path.exists(), "StatStrip.jsx must exist in components/"
    content = path.read_text()
    assert "export default function StatStrip" in content, (
        "StatStrip.jsx must export a default StatStrip function"
    )
