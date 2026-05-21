"""Tests that React components read the Flask API shape, not the prototype shape (Issue #58)."""
import pathlib

COMPONENTS_DIR = (
    pathlib.Path(__file__).parent.parent
    / "nhl-dashboard"
    / "frontend"
    / "src"
    / "components"
)


def _read(name):
    return (COMPONENTS_DIR / name).read_text()


# ---- MatchupCell ----

def test_matchup_cell_uses_away_code():
    assert "g.away.code" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_away_name():
    assert "g.away.name" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_away_record():
    assert "g.away.record" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_home_code():
    assert "g.home.code" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_home_name():
    assert "g.home.name" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_home_record():
    assert "g.home.record" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_live_away_score():
    assert "away_score" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_live_home_score():
    assert "home_score" in _read("MatchupCell.jsx")


def test_matchup_cell_uses_status():
    assert "g.status" in _read("MatchupCell.jsx")


def test_matchup_cell_no_away_name_prototype():
    assert "g.awayName" not in _read("MatchupCell.jsx")


def test_matchup_cell_no_away_rec_prototype():
    assert "g.awayRec" not in _read("MatchupCell.jsx")


def test_matchup_cell_no_home_name_prototype():
    assert "g.homeName" not in _read("MatchupCell.jsx")


def test_matchup_cell_no_final_prototype():
    assert "g.final" not in _read("MatchupCell.jsx")


# ---- StatusCell ----

def test_status_cell_uses_status_final():
    assert 'g.status === "final"' in _read("StatusCell.jsx")


def test_status_cell_no_final_prototype():
    assert "g.final" not in _read("StatusCell.jsx")


# ---- MoneylineCell ----

def test_moneyline_cell_uses_ml_away():
    assert "ml.away" in _read("MoneylineCell.jsx")


def test_moneyline_cell_uses_ml_home():
    assert "ml.home" in _read("MoneylineCell.jsx")


def test_moneyline_cell_uses_ml_open_snake():
    assert "ml_open" in _read("MoneylineCell.jsx")


def test_moneyline_cell_no_source_prototype():
    assert "g.__source" not in _read("MoneylineCell.jsx")


def test_moneyline_cell_no_books_map_prototype():
    assert "g.booksMap" not in _read("MoneylineCell.jsx")


def test_moneyline_cell_no_ml_open_camel_prototype():
    assert "g.mlOpen" not in _read("MoneylineCell.jsx")


def test_moneyline_cell_passes_away_code_to_implied_bar():
    assert "g.away.code" in _read("MoneylineCell.jsx")


def test_moneyline_cell_passes_home_code_to_implied_bar():
    assert "g.home.code" in _read("MoneylineCell.jsx")
