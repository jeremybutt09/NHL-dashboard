"""Integration tests for GET /api/health endpoint (Issue #91)."""
import pytest


class TestHealthSuccess:
    def test_health_returns_200_when_db_reachable(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200

    def test_health_returns_json_content_type(self, client):
        response = client.get('/api/health')
        assert response.content_type == 'application/json'

    def test_health_body_contains_required_keys(self, client):
        data = client.get('/api/health').get_json()
        assert 'status' in data
        assert 'db' in data
        assert 'last_poll' in data

    def test_health_status_equals_ok(self, client):
        data = client.get('/api/health').get_json()
        assert data['status'] == 'ok'

    def test_health_db_equals_connected(self, client):
        data = client.get('/api/health').get_json()
        assert data['db'] == 'connected'


class TestHealthDbFailure:
    def test_health_returns_500_when_db_unreachable(self, client, monkeypatch):
        from extensions import db
        monkeypatch.setattr(
            db.session,
            'execute',
            lambda *a, **kw: (_ for _ in ()).throw(Exception("DB down")),
        )
        response = client.get('/api/health')
        assert response.status_code == 500

    def test_health_returns_json_content_type_on_error(self, client, monkeypatch):
        from extensions import db
        monkeypatch.setattr(
            db.session,
            'execute',
            lambda *a, **kw: (_ for _ in ()).throw(Exception("DB down")),
        )
        response = client.get('/api/health')
        assert response.content_type == 'application/json'

    def test_health_status_is_error_when_db_unreachable(self, client, monkeypatch):
        from extensions import db
        monkeypatch.setattr(
            db.session,
            'execute',
            lambda *a, **kw: (_ for _ in ()).throw(Exception("DB down")),
        )
        data = client.get('/api/health').get_json()
        assert data['status'] == 'error'

    def test_health_no_html_returned_on_error(self, client, monkeypatch):
        from extensions import db
        monkeypatch.setattr(
            db.session,
            'execute',
            lambda *a, **kw: (_ for _ in ()).throw(Exception("DB down")),
        )
        response = client.get('/api/health')
        assert b'<!DOCTYPE html' not in response.data
        assert b'<html' not in response.data
