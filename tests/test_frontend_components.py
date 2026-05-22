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
