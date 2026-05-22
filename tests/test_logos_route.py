"""Tests for GET /api/logos/<code> — CDN proxy route."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

import routes.logos as logos_module
from app import create_app


@pytest.fixture(autouse=True)
def clear_logo_cache():
    """Ensure the module-level logo cache is empty before and after each test."""
    logos_module._logo_cache.clear()
    yield
    logos_module._logo_cache.clear()


@pytest.fixture
def client():
    """Flask test client with TESTING config and scheduler disabled."""
    app = create_app({"TESTING": True, "ENV": "testing"})
    with app.test_client() as c:
        yield c


def _svg_response(content=b"<svg><path/></svg>"):
    """Return a mock httpx response with SVG content and status 200."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = content
    resp.raise_for_status.return_value = None
    return resp


def _error_response():
    """Return a mock httpx response whose raise_for_status raises."""
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("HTTP 403 Forbidden")
    return resp


def test_get_logo_returns_svg_content_type(client):
    """GET /api/logos/TOR returns 200 with Content-Type image/svg+xml."""
    with patch("routes.logos.httpx.get", return_value=_svg_response()):
        response = client.get("/api/logos/TOR")
    assert response.status_code == 200
    assert response.content_type == "image/svg+xml"


def test_get_logo_returns_svg_body(client):
    """GET /api/logos/TOR response body matches the upstream SVG bytes."""
    svg_bytes = b"<svg><circle r='10'/></svg>"
    with patch("routes.logos.httpx.get", return_value=_svg_response(svg_bytes)):
        response = client.get("/api/logos/TOR")
    assert response.data == svg_bytes


def test_get_logo_caches_response(client):
    """Second request for the same code does not hit the CDN again."""
    with patch("routes.logos.httpx.get", return_value=_svg_response()) as mock_get:
        client.get("/api/logos/BOS")
        client.get("/api/logos/BOS")
    mock_get.assert_called_once()


def test_get_logo_returns_404_for_failed_fetch(client):
    """GET /api/logos/XXX returns 404 when the CDN fetch fails."""
    with patch("routes.logos.httpx.get", return_value=_error_response()):
        response = client.get("/api/logos/XXX")
    assert response.status_code == 404
