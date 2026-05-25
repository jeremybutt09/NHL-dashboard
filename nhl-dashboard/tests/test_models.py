"""Unit tests for SQLAlchemy models: Team, Game, OddsSnapshot, ModelFair (Issue #90)."""
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models import Team, Game, OddsSnapshot, ModelFair


class TestTeamModel:
    def test_team_create_and_retrieve_by_pk(self, db, team_factory):
        """Create a Team and retrieve it by its primary-key code."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        retrieved = Team.query.get("TOR")
        assert retrieved is not None
        assert retrieved.name == "Toronto Maple Leafs"

    def test_team_stores_all_nhl_stats_api_fields(self, db):
        """Team row persists all new NHL Stats API fields from the stats endpoint."""
        team = Team(
            tri_code="TOR",
            name="Toronto Maple Leafs",
            team_id=10,
            franchise_id=5,
            full_name="Toronto Maple Leafs",
            league_id=133,
            raw_tricode="TOR",
        )
        db.session.add(team)
        db.session.commit()

        retrieved = db.session.get(Team, "TOR")
        assert retrieved.team_id == 10
        assert retrieved.franchise_id == 5
        assert retrieved.full_name == "Toronto Maple Leafs"
        assert retrieved.league_id == 133
        assert retrieved.raw_tricode == "TOR"

    def test_team_id_unique_constraint_rejects_duplicate(self, db):
        """Two Team rows with the same non-NULL team_id raise IntegrityError."""
        db.session.add(Team(tri_code="TOR", name="Toronto Maple Leafs", team_id=10))
        db.session.add(Team(tri_code="BOS", name="Boston Bruins", team_id=10))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

    def test_team_id_allows_null_before_stats_api_seed(self, db):
        """team_id may be NULL until the stats API seeding job (Issue #112) runs."""
        team = Team(tri_code="TOR", name="Toronto Maple Leafs")
        db.session.add(team)
        db.session.commit()
        assert db.session.get(Team, "TOR").team_id is None

    def test_team_repr_includes_team_id(self, db):
        """Team.__repr__ includes team_id for easier debugging."""
        team = Team(tri_code="TOR", name="Toronto Maple Leafs", team_id=10)
        db.session.add(team)
        db.session.commit()
        assert "10" in repr(team)

    def test_team_upsert_replaces_duplicate(self, db, team_factory):
        """Upserting a Team with an existing code updates the name; row count stays 1."""
        team_factory(code="TOR", name="Toronto Maple Leafs")

        updated = Team(tri_code="TOR", name="Leafs Updated", team_id=1)
        db.session.merge(updated)
        db.session.commit()

        rows = Team.query.filter_by(tri_code="TOR").all()
        assert len(rows) == 1
        assert rows[0].name == "Leafs Updated"


class TestGameModel:
    def test_game_primary_key_attribute_is_game_id(self, db, team_factory, game_factory):
        """Game instance exposes game_id (not id) as its primary key attribute."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS")
        assert game.game_id is not None
        assert isinstance(game.game_id, int)

    def test_game_sqlite_column_is_named_game_id(self, db, team_factory, game_factory):
        """SQLite column backing the primary key is literally named 'game_id'."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game_factory(away_code="TOR", home_code="BOS")
        row = db.session.execute(text("SELECT game_id FROM game LIMIT 1")).fetchone()
        assert row is not None

    def test_game_create_and_retrieve_by_pk(self, db, team_factory, game_factory):
        """Create a Game and retrieve it by its integer primary key."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS")

        retrieved = db.session.get(Game, game.game_id)
        assert retrieved is not None
        assert retrieved.away_code == "TOR"
        assert retrieved.home_code == "BOS"

    def test_game_fk_constraint_raises_integrity_error(self, db):
        """Game referencing a nonexistent team code raises IntegrityError when FKs are enforced.

        SQLite foreign-key enforcement must be enabled explicitly via PRAGMA.
        """
        db.session.execute(text("PRAGMA foreign_keys = ON"))

        game = Game(
            away_code="XXX",
            home_code="YYY",
            status="scheduled",
            start_utc=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(game)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


class TestOddsSnapshotModel:
    def test_odds_snapshot_queryable_by_game_ordered_chronologically(
        self, db, team_factory, game_factory
    ):
        """Three OddsSnapshot rows for the same game are returned in ascending fetch order."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS")

        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        moneylines = [(-110, 100), (-120, 110), (-130, 120)]
        for i, (away_ml, home_ml) in enumerate(moneylines):
            db.session.add(OddsSnapshot(
                game_id=game.game_id,
                fetched_at=base_time + timedelta(minutes=i),
                book="consensus",
                away_ml=away_ml,
                home_ml=home_ml,
                away_implied=52.38,
                home_implied=50.0,
            ))
        db.session.commit()

        rows = (
            OddsSnapshot.query
            .filter_by(game_id=game.game_id)
            .order_by(OddsSnapshot.fetched_at)
            .all()
        )
        assert len(rows) == 3
        assert rows[0].away_ml == -110
        assert rows[1].away_ml == -120
        assert rows[2].away_ml == -130

    def test_odds_snapshot_fk_requires_valid_game(self, db):
        """OddsSnapshot with a nonexistent game_id raises IntegrityError when FKs are enforced."""
        db.session.execute(text("PRAGMA foreign_keys = ON"))

        db.session.add(OddsSnapshot(
            game_id=9999,
            fetched_at=datetime.now(timezone.utc),
            book="consensus",
            away_ml=-110,
            home_ml=100,
            away_implied=52.38,
            home_implied=50.0,
        ))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


class TestModelFairModel:
    def test_model_fair_upsert_replaces_per_game(
        self, db, team_factory, game_factory, model_fair_factory
    ):
        """Upserting ModelFair on the same game_id updates probabilities; row count stays 1."""
        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS")
        model_fair_factory(game_id=game.game_id, home_fair=55.0, away_fair=45.0)

        updated = ModelFair(
            game_id=game.game_id,
            home_fair=60.0,
            away_fair=40.0,
            computed_at=datetime.now(timezone.utc),
        )
        db.session.merge(updated)
        db.session.commit()

        rows = ModelFair.query.filter_by(game_id=game.game_id).all()
        assert len(rows) == 1
        assert rows[0].home_fair == pytest.approx(60.0)
        assert rows[0].away_fair == pytest.approx(40.0)

    def test_model_fair_fk_requires_valid_game(self, db):
        """ModelFair with a nonexistent game_id raises IntegrityError when FKs are enforced."""
        db.session.execute(text("PRAGMA foreign_keys = ON"))

        db.session.add(ModelFair(
            game_id=9999,
            home_fair=55.0,
            away_fair=45.0,
            computed_at=datetime.now(timezone.utc),
        ))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


class TestCascadeBehavior:
    def test_game_deletion_with_linked_rows_raises_integrity_error(
        self, db, team_factory, game_factory, odds_snapshot_factory, model_fair_factory
    ):
        """Deleting a Game that has child rows raises IntegrityError when FKs are enforced.

        The FK columns on OddsSnapshot and ModelFair define no ON DELETE CASCADE, so SQLite
        blocks the parent deletion rather than removing child rows automatically.
        """
        db.session.execute(text("PRAGMA foreign_keys = ON"))

        team_factory(code="TOR", name="Toronto Maple Leafs")
        team_factory(code="BOS", name="Boston Bruins")
        game = game_factory(away_code="TOR", home_code="BOS")
        odds_snapshot_factory(game_id=game.game_id)
        model_fair_factory(game_id=game.game_id)

        db.session.delete(game)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
