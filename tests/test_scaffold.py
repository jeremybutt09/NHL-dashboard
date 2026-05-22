"""Tests for the handoff 2 scaffold: Flask app factory and health endpoint."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402


@pytest.fixture
def client():
    """Flask test client with TESTING config and in-memory SQLite."""
    app = create_app({
        "TESTING": True,
        "ENV": "testing",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.test_client() as c:
        yield c


def test_health_returns_200(client):
    """GET /api/health must respond with HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_response_shape(client):
    """GET /api/health body must contain ok=true and a db key."""
    response = client.get("/api/health")
    data = response.get_json()
    assert data["ok"] is True
    assert "db" in data


def test_health_db_field_is_connected(client):
    """GET /api/health db field must equal 'connected' when DB is reachable."""
    response = client.get("/api/health")
    data = response.get_json()
    assert data["db"] == "connected"


def test_undefined_route_returns_json_404(client):
    """GET to an undefined route must return JSON with error key and 404 status."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    data = response.get_json()
    assert data is not None
    assert data["error"] == "not_found"
