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
        assert 'visiting_team_id' in col_names
        assert 'home_team_id' in col_names

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
            visiting_score=2,
            visiting_team_id=15,
        )
        db.session.add(row)
        db.session.commit()
        retrieved = db.session.get(Game, 2026020001)
        assert retrieved.season == 20252026
        assert retrieved.home_score == 3
        assert retrieved.game_date == '2026-05-25'
