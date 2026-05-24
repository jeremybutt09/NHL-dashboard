"""Tests for structured JSON error responses from Flask routes (Issue #103)."""
import logging
import pytest


class TestGamesTodayInternalError:
    """Scenario: unhandled exception in /api/games/today returns JSON 500."""

    @pytest.fixture(autouse=True)
    def patch_build(self, monkeypatch):
        def _raise():
            raise RuntimeError("boom")
        monkeypatch.setattr('routes.games.build_today_response', _raise)

    def test_games_today_exception_returns_500(self, client):
        assert client.get('/api/games/today').status_code == 500

    def test_games_today_exception_returns_json_content_type(self, client):
        response = client.get('/api/games/today')
        assert 'application/json' in response.content_type

    def test_games_today_exception_body_has_error_key(self, client):
        data = client.get('/api/games/today').get_json()
        assert data['error'] == 'internal_server_error'

    def test_games_today_exception_body_has_message_key(self, client):
        data = client.get('/api/games/today').get_json()
        assert 'message' in data
        assert isinstance(data['message'], str)
        assert len(data['message']) > 0

    def test_games_today_exception_no_html_in_body(self, client):
        response = client.get('/api/games/today')
        assert b'<!DOCTYPE html' not in response.data
        assert b'<html' not in response.data

    def test_games_today_exception_logged_at_error_level(self, client, caplog):
        with caplog.at_level(logging.ERROR):
            client.get('/api/games/today')
        assert any(r.levelno == logging.ERROR for r in caplog.records)


class TestInvalidGameId:
    """Scenario: non-integer game_id returns JSON 400."""

    def test_invalid_game_id_returns_400(self, client):
        assert client.get('/api/games/not-a-number').status_code == 400

    def test_invalid_game_id_returns_json_content_type(self, client):
        response = client.get('/api/games/not-a-number')
        assert 'application/json' in response.content_type

    def test_invalid_game_id_body_has_error_key(self, client):
        data = client.get('/api/games/not-a-number').get_json()
        assert data['error'] == 'bad_request'

    def test_invalid_game_id_body_has_message_key(self, client):
        data = client.get('/api/games/not-a-number').get_json()
        assert 'message' in data
        assert isinstance(data['message'], str)

    def test_invalid_game_id_no_html_in_body(self, client):
        response = client.get('/api/games/not-a-number')
        assert b'<!DOCTYPE html' not in response.data
        assert b'<html' not in response.data


class TestUnknownRoute:
    """Scenario: unknown route returns JSON 404."""

    def test_unknown_route_returns_404(self, client):
        assert client.get('/api/nonexistent').status_code == 404

    def test_unknown_route_returns_json_content_type(self, client):
        response = client.get('/api/nonexistent')
        assert 'application/json' in response.content_type

    def test_unknown_route_body_has_error_key(self, client):
        data = client.get('/api/nonexistent').get_json()
        assert data['error'] == 'not_found'

    def test_unknown_route_body_has_message_key(self, client):
        data = client.get('/api/nonexistent').get_json()
        assert 'message' in data
        assert isinstance(data['message'], str)

    def test_unknown_route_no_html_in_body(self, client):
        response = client.get('/api/nonexistent')
        assert b'<!DOCTYPE html' not in response.data
        assert b'<html' not in response.data
