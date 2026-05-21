"""Tests for the handoff 2 scaffold: Flask app factory and health endpoint."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402


@pytest.fixture
def client():
    """Flask test client with TESTING config and scheduler disabled."""
    app = create_app({"TESTING": True, "ENV": "testing"})
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
