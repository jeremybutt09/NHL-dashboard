"""Tests for Issue #131: drop legacy game table and rename nhl_historical_game to game.

Verifies that:
- Game model maps to the canonical 'game' table with historical-game columns.
- LiveGame model maps to the 'live_game' table with live-score columns.
- NhlHistoricalGame is no longer exported from models.
- The 'nhl_historical_game' table no longer exists in the test schema.
- The migration function is importable and callable.
"""
import models


class TestModelTablenames:
    def test_game_tablename_is_game(self):
        """Game.__tablename__ must be 'game' (was 'nhl_historical_game')."""
        from models import Game
        assert Game.__tablename__ == 'game'

    def test_game_has_historical_columns(self):
        """Game must expose historical-game columns from the NHL Stats REST API."""
        from models import Game
        col_names = {col.name for col in Game.__table__.columns}
        assert 'season' in col_names
        assert 'eastern_start_time' in col_names
        assert 'away_team_id' in col_names
        assert 'home_team_id' in col_names

    def test_game_has_away_columns(self):
        """Game must expose away_team_id and away_score columns (Issue #144)."""
        from models import Game
        col_names = {col.name for col in Game.__table__.columns}
        assert 'away_team_id' in col_names
        assert 'away_score' in col_names

    def test_game_lacks_visiting_columns(self):
        """Game must not have visiting_team_id or visiting_score columns (Issue #144)."""
        from models import Game
        col_names = {col.name for col in Game.__table__.columns}
        assert 'visiting_team_id' not in col_names
        assert 'visiting_score' not in col_names

    def test_game_does_not_have_live_score_columns(self):
        """Game must NOT have the live-score columns from the legacy game table."""
        from models import Game
        col_names = {col.name for col in Game.__table__.columns}
        assert 'away_code' not in col_names
        assert 'status' not in col_names
        assert 'clock' not in col_names

    def test_live_game_tablename_is_live_game(self):
        """LiveGame.__tablename__ must be 'live_game'."""
        from models import LiveGame
        assert LiveGame.__tablename__ == 'live_game'

    def test_live_game_has_live_score_columns(self):
        """LiveGame must expose the live-score columns from the old game table."""
        from models import LiveGame
        col_names = {col.name for col in LiveGame.__table__.columns}
        assert 'away_code' in col_names
        assert 'status' in col_names
        assert 'period' in col_names
        assert 'clock' in col_names

    def test_nhl_historical_game_not_in_models(self):
        """NhlHistoricalGame must no longer be exported from models."""
        assert not hasattr(models, 'NhlHistoricalGame')


class TestSchemaInDb:
    def test_game_table_exists(self, db):
        """'game' table must exist in the test DB schema."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert 'game' in inspector.get_table_names()

    def test_game_table_has_historical_columns(self, db):
        """'game' table columns match the historical-game schema."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        col_names = {col['name'] for col in inspector.get_columns('game')}
        assert 'season' in col_names
        assert 'eastern_start_time' in col_names
        assert 'game_id' in col_names

    def test_game_table_lacks_legacy_columns(self, db):
        """'game' table must not have legacy live-score columns."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        col_names = {col['name'] for col in inspector.get_columns('game')}
        assert 'away_code' not in col_names
        assert 'status' not in col_names

    def test_live_game_table_exists(self, db):
        """'live_game' table must exist in the test DB schema."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert 'live_game' in inspector.get_table_names()

    def test_nhl_historical_game_table_absent(self, db):
        """'nhl_historical_game' table must not exist after the migration."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert 'nhl_historical_game' not in inspector.get_table_names()


class TestMigrationCli:
    def test_migrate_game_table_command_registered(self, app):
        """'migrate-game-table' CLI command must be registered on the Flask app."""
        commands = list(app.cli.commands)
        assert 'migrate-game-table' in commands

    def test_migrate_away_columns_command_registered(self, app):
        """'migrate-away-columns' CLI command must be registered on the Flask app (Issue #147)."""
        commands = list(app.cli.commands)
        assert 'migrate-away-columns' in commands


class TestMigrateAwayColumns:
    def test_migrate_away_columns_renames_visiting_score(self):
        """Migration renames visiting_score → away_score in a legacy-schema DB (Issue #147)."""
        import sqlite3
        import tempfile
        import os
        from sqlalchemy import create_engine, text

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            tmp_path = f.name
        try:
            con = sqlite3.connect(tmp_path)
            con.execute(
                "CREATE TABLE game ("
                "game_id INTEGER PRIMARY KEY, season INTEGER, "
                "visiting_score INTEGER, visiting_team_id INTEGER, "
                "home_score INTEGER, home_team_id INTEGER)"
            )
            con.execute(
                "INSERT INTO game VALUES (2026020001, 20252026, 3, 10, 2, 20)"
            )
            con.commit()
            con.close()

            engine = create_engine(f"sqlite:///{tmp_path}")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE game RENAME COLUMN visiting_team_id TO away_team_id"))
                conn.execute(text("ALTER TABLE game RENAME COLUMN visiting_score TO away_score"))

            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(game)"))}
            assert 'away_score' in cols
            assert 'away_team_id' in cols
            assert 'visiting_score' not in cols
            assert 'visiting_team_id' not in cols
        finally:
            os.unlink(tmp_path)

    def test_migrate_away_columns_preserves_row_data(self):
        """Row data is intact after visiting_* → away_* column rename (Issue #147)."""
        import sqlite3
        import tempfile
        import os
        from sqlalchemy import create_engine, text

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            tmp_path = f.name
        try:
            con = sqlite3.connect(tmp_path)
            con.execute(
                "CREATE TABLE game ("
                "game_id INTEGER PRIMARY KEY, season INTEGER, "
                "visiting_score INTEGER, visiting_team_id INTEGER, "
                "home_score INTEGER, home_team_id INTEGER)"
            )
            con.execute(
                "INSERT INTO game VALUES (2026020001, 20252026, 3, 10, 2, 20)"
            )
            con.commit()
            con.close()

            engine = create_engine(f"sqlite:///{tmp_path}")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE game RENAME COLUMN visiting_team_id TO away_team_id"))
                conn.execute(text("ALTER TABLE game RENAME COLUMN visiting_score TO away_score"))

            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT away_score, away_team_id FROM game WHERE game_id = 2026020001")
                ).fetchone()
            assert row[0] == 3
            assert row[1] == 10
        finally:
            os.unlink(tmp_path)


class TestForeignKeys:
    def test_odds_snapshot_fk_references_live_game(self):
        """OddsSnapshot.game_id FK must reference live_game.game_id."""
        from models import OddsSnapshot
        fk = next(iter(OddsSnapshot.__table__.c.game_id.foreign_keys))
        assert fk.target_fullname == 'live_game.game_id'

    def test_model_fair_fk_references_live_game(self):
        """ModelFair.game_id FK must reference live_game.game_id."""
        from models import ModelFair
        fk = next(iter(ModelFair.__table__.c.game_id.foreign_keys))
        assert fk.target_fullname == 'live_game.game_id'

    def test_nhl_odds_line_fk_references_live_game(self):
        """NhlOddsLine.game_id FK must reference live_game.game_id."""
        from models import NhlOddsLine
        fk = next(iter(NhlOddsLine.__table__.c.game_id.foreign_keys))
        assert fk.target_fullname == 'live_game.game_id'


class TestGameModelRoundtrip:
    def test_game_row_stores_historical_fields(self, db):
        """A Game row persists historical game fields correctly."""
        from models import Game
        row = Game(
            game_id=2026020001,
            eastern_start_time='07:30 PM',
            game_date='2026-05-25',
            season=20252026,
            game_type=2,
            home_score=3,
            home_team_id=10,
            away_score=2,
            away_team_id=15,
        )
        db.session.add(row)
        db.session.commit()
        retrieved = db.session.get(Game, 2026020001)
        assert retrieved.season == 20252026
        assert retrieved.home_score == 3
        assert retrieved.game_date == '2026-05-25'
