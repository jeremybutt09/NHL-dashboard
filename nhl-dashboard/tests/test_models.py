"""Unit tests for SQLAlchemy models: Team, Game (Issue #90)."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models import Team, Game


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
