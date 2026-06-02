"""Tests verifying pytest infrastructure fixtures (Issue #87)."""


def test_app_testing_flag_is_set(app):
    """TESTING config flag must be True."""
    assert app.config["TESTING"] is True


def test_app_uses_in_memory_sqlite(app):
    """Database URI must point to in-memory SQLite."""
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_database_starts_empty(db):
    """Each test receives a fresh, empty database."""
    from models import Team
    assert Team.query.count() == 0


def test_team_factory_creates_committed_row(team_factory, db):
    """team_factory(code, name) creates and persists a Team row."""
    from models import Team
    team = team_factory(code="TOR", name="Toronto Maple Leafs")
    assert team.tri_code == "TOR"
    assert team.name == "Toronto Maple Leafs"
    assert Team.query.get("TOR") is not None




def test_client_get_health_returns_response(client):
    """Flask test client issues requests without starting a real server."""
    response = client.get("/api/health")
    assert response.status_code == 200
