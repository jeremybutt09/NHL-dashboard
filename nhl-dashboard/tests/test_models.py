"""Unit tests for SQLAlchemy models: Team, Game (Issue #90), DimPlayer (Issue #164)."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models import Team, Game, DimPlayer


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


class TestDimPlayerModel:
    """Tests for the DimPlayer model (Issue #164)."""

    def test_dim_player_create_and_retrieve_by_pk(self, db):
        """Create a DimPlayer row and retrieve it by player_id primary key."""
        player = DimPlayer(
            player_id=8478402,
            first_name="Connor",
            last_name="McDavid",
            position="C",
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(player)
        db.session.commit()

        retrieved = db.session.get(DimPlayer, 8478402)
        assert retrieved is not None
        assert retrieved.first_name == "Connor"
        assert retrieved.last_name == "McDavid"

    def test_dim_player_stores_all_biographical_fields(self, db):
        """All biographical columns are persisted and retrieved correctly."""
        now = datetime(2026, 6, 1, 12, 0, 0)
        player = DimPlayer(
            player_id=8478402,
            first_name="Connor",
            last_name="McDavid",
            sweater_number=97,
            position="C",
            shoots_catches="L",
            height_in_inches=73,
            weight_in_pounds=193,
            birth_date="1997-01-13",
            birth_country="CAN",
            headshot_url="https://assets.nhle.com/mugs/nhl/20252026/EDM/8478402.png",
            updated_at=now,
        )
        db.session.add(player)
        db.session.commit()

        row = db.session.get(DimPlayer, 8478402)
        assert row.sweater_number == 97
        assert row.position == "C"
        assert row.shoots_catches == "L"
        assert row.height_in_inches == 73
        assert row.weight_in_pounds == 193
        assert row.birth_date == "1997-01-13"
        assert row.birth_country == "CAN"
        assert "nhle.com" in row.headshot_url
        assert row.updated_at == now

    def test_dim_player_upsert_overwrites_sweater_number(self, db):
        """db.session.merge() on player_id overwrites changed fields; row count stays 1."""
        db.session.add(DimPlayer(
            player_id=8478402,
            first_name="Connor",
            last_name="McDavid",
            sweater_number=97,
            updated_at=datetime.now(timezone.utc),
        ))
        db.session.commit()

        updated = DimPlayer(
            player_id=8478402,
            first_name="Connor",
            last_name="McDavid",
            sweater_number=99,
            updated_at=datetime.now(timezone.utc),
        )
        db.session.merge(updated)
        db.session.commit()

        rows = DimPlayer.query.filter_by(player_id=8478402).all()
        assert len(rows) == 1
        assert rows[0].sweater_number == 99

    def test_dim_player_primary_key_not_autoincrement(self, db):
        """player_id is caller-supplied (NHL ID), not auto-generated."""
        player = DimPlayer(
            player_id=8471675,
            first_name="Sidney",
            last_name="Crosby",
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(player)
        db.session.commit()

        assert db.session.get(DimPlayer, 8471675).player_id == 8471675

    def test_dim_player_table_name(self, db):
        """The SQLAlchemy model maps to the 'dim_player' table in SQLite."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        assert "dim_player" in inspector.get_table_names()
