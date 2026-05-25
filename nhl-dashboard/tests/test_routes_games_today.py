"""Integration tests for GET /api/games/today endpoint (Issue #92)."""
import pytest
from datetime import datetime, timezone

from models import OddsSnapshot


class TestGamesTodayPopulated:
    """Scenario: populated game with odds, fair probabilities, edge, and sparkline."""

    @pytest.fixture(autouse=True)
    def seed_db(self, team_factory, game_factory, odds_snapshot_factory, model_fair_factory):
        """Seed DB with one live game, one odds snapshot, and one fair-probability row."""
        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')
        self.game = game_factory(
            'TOR', 'BOS',
            status='live', away_score=2, home_score=1, period='2', clock='10:00',
        )
        odds_snapshot_factory(self.game.game_id, away_ml=-110, home_ml=100)
        model_fair_factory(self.game.game_id, home_fair=55.0, away_fair=45.0)

    def test_games_today_returns_200(self, client):
        assert client.get('/api/games/today').status_code == 200

    def test_games_today_returns_json(self, client):
        assert client.get('/api/games/today').content_type == 'application/json'

    def test_games_today_body_has_games_array(self, client):
        data = client.get('/api/games/today').get_json()
        assert isinstance(data.get('games'), list)

    def test_games_today_contains_one_game(self, client):
        data = client.get('/api/games/today').get_json()
        assert len(data['games']) == 1

    def test_games_today_game_has_required_fields(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        for field in ('game_id', 'away', 'home', 'status', 'ml', 'fair', 'edge', 'movement_24h'):
            assert field in game, f"Missing field: {field}"

    def test_games_today_game_id_key_not_id(self, client):
        """Response uses 'game_id' key; the bare 'id' key must not be present."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert 'game_id' in game
        assert 'id' not in game

    def test_games_today_game_has_correct_team_codes(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['away']['code'] == 'TOR'
        assert game['home']['code'] == 'BOS'

    def test_games_today_game_has_correct_team_names(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['away']['name'] == 'Toronto Maple Leafs'
        assert game['home']['name'] == 'Boston Bruins'

    def test_games_today_ml_away_is_integer(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['ml'] is not None
        assert isinstance(game['ml']['away'], int)

    def test_games_today_ml_home_is_integer(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert isinstance(game['ml']['home'], int)

    def test_games_today_fair_values_are_floats(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert isinstance(game['fair']['away'], float)
        assert isinstance(game['fair']['home'], float)

    def test_games_today_fair_probs_sum_to_one_hundred(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        total = game['fair']['away'] + game['fair']['home']
        assert total == pytest.approx(100.0, abs=0.01)

    def test_games_today_edge_is_signed_float(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert isinstance(game['edge'], float)

    def test_games_today_sparkline_is_list(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert isinstance(game['movement_24h'], list)

    def test_games_today_sparkline_length_matches_snapshot_count(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert len(game['movement_24h']) == 1

    def test_games_today_live_block_present_for_live_game(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'live'
        assert game['live'] is not None

    def test_games_today_live_block_has_period_and_clock(self, client):
        live = client.get('/api/games/today').get_json()['games'][0]['live']
        assert live['period'] == '2'
        assert live['clock'] == '10:00'

    def test_games_today_live_block_has_scores(self, client):
        live = client.get('/api/games/today').get_json()['games'][0]['live']
        assert live['away_score'] == 2
        assert live['home_score'] == 1

    def test_games_today_game_has_start_est_field(self, client):
        """Response includes start_est field with Eastern Time ISO string."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert 'start_est' in game

    def test_games_today_game_has_game_date_field(self, client):
        """Response includes game_date field from the API's gameDate."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert 'game_date' in game

    def test_games_today_sparkline_ordered_ascending(self, client, db):
        """Entries with earlier fetched_at timestamps appear before later ones."""
        t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        snap1 = OddsSnapshot(
            game_id=self.game.game_id, fetched_at=t1, book='test',
            away_ml=-120, home_ml=110, away_implied=45.0, home_implied=55.0,
        )
        snap2 = OddsSnapshot(
            game_id=self.game.game_id, fetched_at=t2, book='test',
            away_ml=-130, home_ml=120, away_implied=60.0, home_implied=40.0,
        )
        db.session.add_all([snap1, snap2])
        db.session.commit()

        sparkline = client.get('/api/games/today').get_json()['games'][0]['movement_24h']
        idx1 = sparkline.index(45.0)
        idx2 = sparkline.index(60.0)
        assert idx1 < idx2


class TestGamesTodayEmpty:
    """Scenario: no game rows in DB returns empty games list."""

    def test_games_today_empty_returns_200(self, client):
        assert client.get('/api/games/today').status_code == 200

    def test_games_today_empty_returns_empty_games_list(self, client):
        data = client.get('/api/games/today').get_json()
        assert data['games'] == []


class TestGamesTodayMissingOdds:
    """Scenario: game with no OddsSnapshot rows returns safely without a 500 error."""

    @pytest.fixture(autouse=True)
    def seed_db(self, team_factory, game_factory):
        """Seed DB with one game but no odds or fair rows."""
        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')
        self.game = game_factory('TOR', 'BOS')

    def test_games_today_missing_odds_returns_200(self, client):
        assert client.get('/api/games/today').status_code == 200

    def test_games_today_missing_odds_game_present_in_response(self, client):
        data = client.get('/api/games/today').get_json()
        assert len(data['games']) == 1

    def test_games_today_missing_odds_ml_is_null(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['ml'] is None

    def test_games_today_missing_odds_edge_is_null(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['edge'] is None

    def test_games_today_missing_odds_sparkline_is_empty(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['movement_24h'] == []
