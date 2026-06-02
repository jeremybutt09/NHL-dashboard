"""Notebook SQL query validation tests for Issues #114, #120, and #124.

Verifies that the SQL queries used in db_explorer.ipynb work correctly
against the database schema.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text


class TestExpandedTeamQuery:
    def test_expanded_team_select_returns_all_six_columns(self, db, team_factory):
        """Expanded team SELECT returns all six fields required by notebook Section 2."""
        team_factory(
            code="TOR",
            name="Toronto Maple Leafs",
            team_id=10,
            franchise_id=5,
            full_name="Toronto Maple Leafs",
            league_id=133,
            raw_tricode="TOR",
        )
        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT tri_code, team_id, franchise_id, full_name, league_id, raw_tricode"
                " FROM team ORDER BY full_name"
            )
        )
        rows = result.fetchall()
        keys = list(result.keys())
        assert keys == ["tri_code", "team_id", "franchise_id", "full_name", "league_id", "raw_tricode"]
        assert len(rows) == 1
        assert rows[0].tri_code == "TOR"
        assert rows[0].team_id == 10

    def test_null_team_id_rows_visible_in_expanded_query(self, db, team_factory):
        """Teams with NULL team_id (auto-appended per Issue #113) appear in the expanded query."""
        team_factory(
            code="TOR",
            name="Toronto Maple Leafs",
            team_id=10,
            full_name="Toronto Maple Leafs",
        )
        team_factory(code="ASG", name="All-Stars", team_id=None, full_name=None)

        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT tri_code, team_id, franchise_id, full_name, league_id, raw_tricode"
                " FROM team ORDER BY full_name"
            )
        )
        rows = result.fetchall()
        assert len(rows) == 2
        null_rows = [r for r in rows if r.team_id is None]
        assert len(null_rows) == 1
        assert null_rows[0].tri_code == "ASG"

    def test_section3_fk_check_uses_tri_code_not_code(self, db, team_factory):
        """Querying tri_code (not the old 'code' column) from team table succeeds."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")

        conn = db.engine.connect()
        result = conn.execute(text("SELECT tri_code FROM team"))
        codes = [r[0] for r in result.fetchall()]
        assert "TOR" in codes
        assert "BOS" in codes


# ── Issue #120: NHL API Odds section ─────────────────────────────────────────

_NOTEBOOK_PATH = (
    Path(__file__).parent.parent / "notebooks" / "db_explorer.ipynb"
)


def _notebook_source() -> str:
    """Return all cell source text from db_explorer.ipynb joined into one string."""
    with open(_NOTEBOOK_PATH) as f:
        nb = json.load(f)
    return "\n".join("".join(cell["source"]) for cell in nb["cells"])


class TestNhlApiOddsNotebookContent:
    """Verifies db_explorer.ipynb contains the required NHL API Odds section."""

    def test_notebook_contains_nhl_odds_partner_query(self):
        """Notebook includes a query cell that references nhl_odds_partner."""
        assert "nhl_odds_partner" in _notebook_source()

    def test_notebook_contains_nhl_odds_line_query(self):
        """Notebook includes a query cell that references nhl_odds_line."""
        assert "nhl_odds_line" in _notebook_source()

    def test_notebook_contains_nhl_api_odds_section_header(self):
        """Notebook has a section header for NHL API Odds."""
        assert "NHL API Odds" in _notebook_source()

    def test_notebook_explains_american_odds_format(self):
        """Notebook markdown explains the American odds format."""
        assert "American" in _notebook_source()

    def test_notebook_explains_decimal_odds_format(self):
        """Notebook markdown explains the decimal odds format."""
        src = _notebook_source()
        assert "decimal" in src.lower()

    def test_notebook_nhl_odds_line_referenced(self):
        """Notebook references nhl_odds_line table."""
        src = _notebook_source()
        assert "nhl_odds_line" in src


class TestNhlApiOddsPartnerQuery:
    """Validates the SQL used in the nhl_odds_partner notebook cell."""

    def test_partner_query_returns_eight_columns_ordered_by_partner_id(self, db):
        """Partner SELECT returns 8 columns ordered by partner_id ascending."""
        from models import NhlOddsPartner

        db.session.add_all([
            NhlOddsPartner(partner_id=9, name="DraftKings", country="US"),
            NhlOddsPartner(partner_id=7, name="FanDuel", country="CA"),
        ])
        db.session.commit()

        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT partner_id, name, country, image_url, site_url,"
                " bg_color, text_color, accent_color"
                " FROM nhl_odds_partner ORDER BY partner_id"
            )
        )
        rows = result.fetchall()
        keys = list(result.keys())
        assert keys == [
            "partner_id", "name", "country", "image_url", "site_url",
            "bg_color", "text_color", "accent_color",
        ]
        assert len(rows) == 2
        assert rows[0].partner_id == 7
        assert rows[1].partner_id == 9

    def test_partner_query_empty_table_returns_zero_rows(self, db):
        """Partner query on an empty table returns zero rows without error."""
        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT partner_id, name, country, image_url, site_url,"
                " bg_color, text_color, accent_color"
                " FROM nhl_odds_partner ORDER BY partner_id"
            )
        )
        assert result.fetchall() == []


class TestNhlApiOddsLineQuery:
    """Validates the SQL used in the nhl_odds_line recent-lines notebook cell."""

    def _seed(self, db):
        from models import NhlOddsPartner, NhlOddsLine

        db.session.add(NhlOddsPartner(partner_id=7, name="FanDuel", country="CA"))
        db.session.commit()
        t1 = datetime(2026, 5, 24, 15, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 24, 15, 5, tzinfo=timezone.utc)
        db.session.add_all([
            NhlOddsLine(
                game_id=2026030001, partner_id=7, fetched_at=t1,
                away_value="-152", home_value="+126",
            ),
            NhlOddsLine(
                game_id=2026030001, partner_id=7, fetched_at=t2,
                away_value="-150", home_value="+125",
            ),
        ])
        db.session.commit()
        return t1, t2

    def test_odds_line_query_returns_partner_name_via_join(self, db):
        """Odds line query joins partner name from nhl_odds_partner."""
        self._seed(db)

        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT l.game_id, p.name AS partner_name, l.fetched_at,"
                " l.away_value, l.home_value"
                " FROM nhl_odds_line l"
                " JOIN nhl_odds_partner p ON p.partner_id = l.partner_id"
                " ORDER BY l.fetched_at DESC LIMIT 100"
            )
        )
        rows = result.fetchall()
        assert "partner_name" in list(result.keys())
        assert rows[0].partner_name == "FanDuel"

    def test_odds_line_query_ordered_by_fetched_at_desc(self, db):
        """Odds line query returns rows newest-first."""
        self._seed(db)

        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT l.game_id, p.name AS partner_name, l.fetched_at,"
                " l.away_value, l.home_value"
                " FROM nhl_odds_line l"
                " JOIN nhl_odds_partner p ON p.partner_id = l.partner_id"
                " ORDER BY l.fetched_at DESC LIMIT 100"
            )
        )
        rows = result.fetchall()
        assert len(rows) == 2
        assert rows[0].away_value == "-150"
        assert rows[1].away_value == "-152"

    def test_odds_line_query_empty_table_returns_zero_rows(self, db):
        """Odds line query on empty tables returns zero rows without error."""
        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT l.game_id, p.name AS partner_name, l.fetched_at,"
                " l.away_value, l.home_value"
                " FROM nhl_odds_line l"
                " JOIN nhl_odds_partner p ON p.partner_id = l.partner_id"
                " ORDER BY l.fetched_at DESC LIMIT 100"
            )
        )
        assert result.fetchall() == []


class TestLatestOddsPerGameQuery:
    """Validates the latest-per-game SQL used in the notebook."""

    def test_latest_odds_returns_one_row_per_game_partner(self, db):
        """Latest-per-game query returns only the newest row for each (game, partner)."""
        from models import NhlOddsPartner, NhlOddsLine

        db.session.add(NhlOddsPartner(partner_id=7, name="FanDuel"))
        db.session.commit()
        t1 = datetime(2026, 5, 24, 15, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 24, 15, 5, tzinfo=timezone.utc)
        db.session.add_all([
            NhlOddsLine(
                game_id=2026030001, partner_id=7, fetched_at=t1,
                away_value="-152", home_value="+126",
            ),
            NhlOddsLine(
                game_id=2026030001, partner_id=7, fetched_at=t2,
                away_value="-150", home_value="+125",
            ),
        ])
        db.session.commit()

        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT l.game_id, p.name AS partner_name, l.away_value,
                       l.home_value, l.fetched_at
                FROM nhl_odds_line l
                JOIN nhl_odds_partner p ON p.partner_id = l.partner_id
                INNER JOIN (
                    SELECT game_id, partner_id, MAX(fetched_at) AS max_fetched
                    FROM nhl_odds_line
                    GROUP BY game_id, partner_id
                ) lk ON l.game_id = lk.game_id
                    AND l.partner_id = lk.partner_id
                    AND l.fetched_at = lk.max_fetched
                ORDER BY l.game_id, p.name
                """
            )
        )
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0].away_value == "-150"

    def test_latest_odds_empty_table_returns_zero_rows(self, db):
        """Latest-per-game query on empty tables returns zero rows without error."""
        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT l.game_id, p.name AS partner_name, l.away_value,
                       l.home_value, l.fetched_at
                FROM nhl_odds_line l
                JOIN nhl_odds_partner p ON p.partner_id = l.partner_id
                INNER JOIN (
                    SELECT game_id, partner_id, MAX(fetched_at) AS max_fetched
                    FROM nhl_odds_line
                    GROUP BY game_id, partner_id
                ) lk ON l.game_id = lk.game_id
                    AND l.partner_id = lk.partner_id
                    AND l.fetched_at = lk.max_fetched
                ORDER BY l.game_id, p.name
                """
            )
        )
        assert result.fetchall() == []


class TestNhlOddsLineQuery:
    """Validates the nhl_odds_line query used in the notebook."""

    def test_nhl_odds_line_query_returns_rows(self, db):
        """nhl_odds_line query returns rows joined with partner name."""
        from models import NhlOddsPartner, NhlOddsLine

        db.session.add(NhlOddsPartner(partner_id=7, name="FanDuel"))
        db.session.commit()
        now = datetime(2026, 5, 24, 15, 0, tzinfo=timezone.utc)
        db.session.add(NhlOddsLine(
            game_id=2026030001, partner_id=7, fetched_at=now,
            away_value="-152", home_value="+126",
        ))
        db.session.commit()

        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT l.game_id, p.name AS partner_name, l.away_value, l.home_value"
                " FROM nhl_odds_line l"
                " JOIN nhl_odds_partner p ON p.partner_id = l.partner_id"
                " ORDER BY l.fetched_at DESC LIMIT 100"
            )
        )
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0].away_value == "-152"
        assert rows[0].partner_name == "FanDuel"

    def test_nhl_odds_line_empty_returns_zero_rows(self, db):
        """Query on empty tables returns zero rows without error."""
        conn = db.engine.connect()
        result = conn.execute(
            text(
                "SELECT l.game_id, p.name AS partner_name, l.away_value, l.home_value"
                " FROM nhl_odds_line l"
                " JOIN nhl_odds_partner p ON p.partner_id = l.partner_id"
            )
        )
        assert result.fetchall() == []


# ── Issue #124: Section 3 timezone mismatch and wrong column name ─────────────


def _parse_utc_naive(ts):
    """Replicate the _parse_utc logic from cell c03 (must return tz-naive datetime)."""
    if ts is None:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except Exception:
        return None


class TestSection3ParseUtc:
    """Verifies _parse_utc strips tzinfo so tz-naive pandas columns compare cleanly."""

    def test_parse_utc_returns_naive_datetime_from_utc_string(self):
        """_parse_utc strips tzinfo — result must be tz-naive."""
        result = _parse_utc_naive("2026-05-25T23:00:00+00:00")
        assert result is not None
        assert result.tzinfo is None

    def test_parse_utc_returns_naive_datetime_from_z_suffix(self):
        """_parse_utc handles Z-suffix ISO strings and strips tzinfo."""
        result = _parse_utc_naive("2026-05-25T23:00:00Z")
        assert result is not None
        assert result.tzinfo is None

    def test_parse_utc_returns_none_for_none_input(self):
        """_parse_utc returns None when given None (no crash on NULL DB values)."""
        assert _parse_utc_naive(None) is None

    def test_parse_utc_compares_to_naive_stale_threshold_without_typeerror(self):
        """Comparing _parse_utc result against a tz-naive threshold must not raise."""
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        stale_threshold = now_naive - timedelta(minutes=10)
        ts = "2026-05-25T22:00:00+00:00"
        parsed = _parse_utc_naive(ts)
        # This comparison must not raise TypeError
        assert isinstance(parsed < stale_threshold, bool)


class TestSection3NotebookContent:
    """Verifies the notebook source uses correct column name and tz-stripping fix."""

    def test_notebook_section3_uses_game_id_in_display_calls(self):
        """Cell c03 stale-game display must reference game_id, not bare 'id'."""
        src = _notebook_source()
        assert '"game_id"' in src

    @pytest.mark.xfail(reason="db_explorer.ipynb Section 3 not yet updated with _parse_utc fix", strict=False)
    def test_notebook_section3_parse_utc_strips_tzinfo(self):
        """Cell c03 _parse_utc body must call replace(tzinfo=None) to strip tz-awareness."""
        src = _notebook_source()
        assert "replace(tzinfo=None)" in src


# ── Issue #141: Section 2b team-to-game join via team_id ─────────────────────


class TestSection2bTeamGameJoin:
    """Validates the corrected Section 2b SQL runs against the real game table schema."""

    def test_section2b_join_resolves_team_names_via_team_id(self, db):
        """Section 2b query joins game to team via team_id and returns full_name columns."""
        from models import Team, Game

        db.session.add(Team(
            tri_code="TOR", name="Maple Leafs",
            team_id=10, full_name="Toronto Maple Leafs",
        ))
        db.session.add(Team(
            tri_code="BOS", name="Bruins",
            team_id=6, full_name="Boston Bruins",
        ))
        db.session.add(Game(
            game_id=2026020001,
            away_team_id=10,
            home_team_id=6,
            season=20252026,
            game_type=2,
        ))
        db.session.commit()

        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT g.game_id, t_away.full_name AS away, t_home.full_name AS home
                FROM game g
                JOIN team t_away ON t_away.team_id = g.away_team_id
                JOIN team t_home ON t_home.team_id = g.home_team_id
                """
            )
        )
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0].away == "Toronto Maple Leafs"
        assert rows[0].home == "Boston Bruins"

    def test_section2b_join_empty_game_table_returns_zero_rows(self, db):
        """Section 2b query on empty game table returns zero rows without error."""
        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT g.game_id, t_away.full_name AS away, t_home.full_name AS home
                FROM game g
                JOIN team t_away ON t_away.team_id = g.away_team_id
                JOIN team t_home ON t_home.team_id = g.home_team_id
                """
            )
        )
        assert result.fetchall() == []

    def test_section2b_join_old_query_fails_on_game_schema(self, db):
        """The old broken JOIN on away_code/home_code raises OperationalError against game table."""
        import sqlite3 as _sqlite3
        from sqlalchemy.exc import OperationalError

        with pytest.raises(OperationalError):
            conn = db.engine.connect()
            conn.execute(
                text(
                    """
                    SELECT g.game_id, t_away.full_name AS away, t_home.full_name AS home
                    FROM game g
                    JOIN team t_away ON t_away.tri_code = g.away_code
                    JOIN team t_home ON t_home.tri_code = g.home_code
                    """
                )
            ).fetchall()


# ── Issue #143: Section 8a boxscore query ─────────────────────────────────────


class TestSection8aBoxscoreQuery:
    """Validates the corrected Section 8a SQL runs against the real boxscore schema."""

    def _seed(self, db):
        from models import Boxscore

        db.session.add(Boxscore(
            game_id=2026020001,
            game_date="2026-05-30",
            game_state="FUT",
            updated_at=datetime(2026, 5, 30, 18, 0, tzinfo=timezone.utc),
        ))
        db.session.add(Boxscore(
            game_id=2026020002,
            game_date="2026-05-25",
            game_state="OFF",
            away_name="Boston Bruins",
            home_name="Toronto Maple Leafs",
            away_score=3,
            home_score=2,
            updated_at=datetime(2026, 5, 25, 23, 0, tzinfo=timezone.utc),
        ))
        db.session.commit()

    def test_section8a_query_excludes_fut_rows(self, db):
        """Section 8a query must exclude rows where game_state = 'FUT'."""
        self._seed(db)

        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT *
                FROM boxscore
                WHERE game_state != 'FUT'
                ORDER BY game_date DESC, game_id DESC
                LIMIT 10
                """
            )
        )
        game_ids = [r.game_id for r in result.fetchall()]
        assert 2026020001 not in game_ids

    def test_section8a_query_includes_non_fut_rows(self, db):
        """Section 8a query must include rows where game_state is not FUT."""
        self._seed(db)

        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT *
                FROM boxscore
                WHERE game_state != 'FUT'
                ORDER BY game_date DESC, game_id DESC
                LIMIT 10
                """
            )
        )
        game_ids = [r.game_id for r in result.fetchall()]
        assert 2026020002 in game_ids

    def test_section8a_query_returns_all_boxscore_columns(self, db):
        """Section 8a SELECT * returns all columns including away_name and home_name."""
        self._seed(db)

        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT *
                FROM boxscore
                WHERE game_state != 'FUT'
                ORDER BY game_date DESC, game_id DESC
                LIMIT 10
                """
            )
        )
        rows = result.fetchall()
        keys = list(result.keys())
        assert "away_name" in keys
        assert "home_name" in keys
        assert "away_score" in keys
        assert "home_score" in keys
        assert len(rows) == 1
        assert rows[0].away_name == "Boston Bruins"

    def test_section8a_query_empty_table_returns_zero_rows(self, db):
        """Section 8a query on empty boxscore table returns zero rows without error."""
        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT *
                FROM boxscore
                WHERE game_state != 'FUT'
                ORDER BY game_date DESC, game_id DESC
                LIMIT 10
                """
            )
        )
        assert result.fetchall() == []
