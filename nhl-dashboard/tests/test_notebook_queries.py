"""Notebook SQL query validation tests for Issue #114.

Verifies that the SQL queries used in db_explorer.ipynb Section 2 work
correctly against the expanded team schema introduced in Issue #111.
"""
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

    def test_team_game_join_resolves_full_names(self, db, team_factory, game_factory):
        """Join query resolves away/home full_name via tri_code FK as required by notebook Section 2."""
        team_factory(
            code="TOR",
            name="Toronto Maple Leafs",
            full_name="Toronto Maple Leafs",
        )
        team_factory(
            code="BOS",
            name="Boston Bruins",
            full_name="Boston Bruins",
        )
        game = game_factory(away_code="TOR", home_code="BOS")

        conn = db.engine.connect()
        result = conn.execute(
            text(
                """
                SELECT g.game_id, t_away.full_name AS away, t_home.full_name AS home
                FROM game g
                JOIN team t_away ON t_away.tri_code = g.away_code
                JOIN team t_home ON t_home.tri_code = g.home_code
                """
            )
        )
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0].away == "Toronto Maple Leafs"
        assert rows[0].home == "Boston Bruins"

    def test_section3_fk_check_uses_tri_code_not_code(self, db, team_factory):
        """Querying tri_code (not the old 'code' column) from team table succeeds."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")

        conn = db.engine.connect()
        result = conn.execute(text("SELECT tri_code FROM team"))
        codes = [r[0] for r in result.fetchall()]
        assert "TOR" in codes
        assert "BOS" in codes
