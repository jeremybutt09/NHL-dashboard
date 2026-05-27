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


class TestGamesTodayEtDateFilter:
    """Verify /api/games/today filters by Eastern Time calendar date (Issue #150)."""

    def test_games_today_excludes_game_with_past_game_date(self, client, db, team_factory):
        """A LiveGame with a past game_date is excluded from today's response."""
        from datetime import datetime
        from models import LiveGame

        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')

        game = LiveGame(
            game_id=9001,
            away_code='TOR', home_code='BOS',
            game_date='2020-01-01',
            start_est=datetime(2020, 1, 1, 19, 0),
            status='scheduled',
        )
        db.session.add(game)
        db.session.commit()

        data = client.get('/api/games/today').get_json()
        assert 9001 not in [g['game_id'] for g in data['games']]

    def test_games_today_et_boundary_excludes_utc_next_day_game(self, client, db, team_factory):
        """A game dated ET-tomorrow is excluded when today_et() is mocked to return ET-today."""
        from datetime import datetime
        from models import LiveGame
        from unittest.mock import patch

        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')

        game = LiveGame(
            game_id=9002,
            away_code='TOR', home_code='BOS',
            game_date='2026-05-27',
            start_est=datetime(2026, 5, 27, 0, 30),
            status='scheduled',
        )
        db.session.add(game)
        db.session.commit()

        # Simulate: ET clock still shows May 26, UTC already shows May 27
        with patch("services.slate.today_et", return_value="2026-05-26"):
            data = client.get('/api/games/today').get_json()

        assert 9002 not in [g['game_id'] for g in data['games']]

    def test_games_today_et_boundary_includes_et_today_game(self, client, db, team_factory):
        """A game dated ET-today is included even when it's already past midnight UTC."""
        from datetime import datetime
        from models import LiveGame
        from unittest.mock import patch

        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')

        game = LiveGame(
            game_id=9003,
            away_code='TOR', home_code='BOS',
            game_date='2026-05-26',
            start_est=datetime(2026, 5, 26, 19, 0),
            status='scheduled',
        )
        db.session.add(game)
        db.session.commit()

        # Simulate: ET clock shows May 26 (23:30 ET), UTC shows May 27 (03:30 UTC)
        with patch("services.slate.today_et", return_value="2026-05-26"):
            data = client.get('/api/games/today').get_json()

        assert 9003 in [g['game_id'] for g in data['games']]


class TestGamesTodayFinalScores:
    """Scenario: final game shows actual scores in the live block (Issue #151)."""

    @pytest.fixture(autouse=True)
    def seed_db(self, team_factory, game_factory):
        """Seed DB with one final game that has real scores."""
        team_factory('CAR', 'Carolina Hurricanes')
        team_factory('MTL', 'Montreal Canadiens')
        self.game = game_factory(
            'CAR', 'MTL',
            status='final', away_score=3, home_score=2,
            period='3rd', clock='00:00',
        )

    def test_games_today_live_block_present_for_final_game(self, client):
        """A final game must have a non-null live block so the frontend can render scores."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'final'
        assert game['live'] is not None

    def test_games_today_final_game_shows_correct_away_score(self, client):
        """away_score in the live block must reflect the actual final score."""
        live = client.get('/api/games/today').get_json()['games'][0]['live']
        assert live['away_score'] == 3

    def test_games_today_final_game_shows_correct_home_score(self, client):
        """home_score in the live block must reflect the actual final score."""
        live = client.get('/api/games/today').get_json()['games'][0]['live']
        assert live['home_score'] == 2


class TestGamesTodayScheduledScores:
    """Scenario: scheduled game shows no scores (live block is null) (Issue #151)."""

    @pytest.fixture(autouse=True)
    def seed_db(self, team_factory, game_factory):
        """Seed DB with one scheduled game that has no score data yet."""
        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')
        self.game = game_factory(
            'TOR', 'BOS',
            status='scheduled', away_score=0, home_score=0,
            period=None, clock=None,
        )

    def test_games_today_scheduled_game_live_block_is_null(self, client):
        """A scheduled game with no score data must return live: null."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'scheduled'
        assert game['live'] is None


class TestGamesTodayDateParam:
    """Scenario: ?date=YYYY-MM-DD returns games for the specified date (Issue #152)."""

    @pytest.fixture(autouse=True)
    def seed_db(self, team_factory, game_factory):
        """Seed DB with games on two different dates."""
        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')
        team_factory('EDM', 'Edmonton Oilers')
        team_factory('VAN', 'Vancouver Canucks')

        self.past_game = game_factory(
            'TOR', 'BOS',
            status='final', away_score=3, home_score=2,
            game_date='2026-01-15',
        )
        self.today_game = game_factory(
            'EDM', 'VAN',
            status='scheduled', away_score=0, home_score=0,
        )

    def test_games_today_date_param_returns_game_for_specified_date(self, client):
        """?date=<past-date> returns games tagged with that date."""
        data = client.get('/api/games/today?date=2026-01-15').get_json()
        game_ids = [g['game_id'] for g in data['games']]
        assert self.past_game.game_id in game_ids

    def test_games_today_date_param_excludes_other_dates(self, client):
        """?date=<past-date> excludes games from other dates."""
        data = client.get('/api/games/today?date=2026-01-15').get_json()
        game_ids = [g['game_id'] for g in data['games']]
        assert self.today_game.game_id not in game_ids

    def test_games_today_no_date_param_excludes_past_games(self, client):
        """Without ?date=, games from past dates are still excluded."""
        data = client.get('/api/games/today').get_json()
        game_ids = [g['game_id'] for g in data['games']]
        assert self.past_game.game_id not in game_ids

    def test_games_today_no_date_param_returns_today_games(self, client):
        """Without ?date=, today's games are still returned (backward compat)."""
        data = client.get('/api/games/today').get_json()
        game_ids = [g['game_id'] for g in data['games']]
        assert self.today_game.game_id in game_ids

    def test_games_today_date_param_returns_200(self, client):
        """?date= with a valid date string responds 200."""
        assert client.get('/api/games/today?date=2026-01-15').status_code == 200

    def test_games_today_date_param_empty_for_unmatched_date(self, client):
        """?date= with a date that has no games returns an empty list."""
        data = client.get('/api/games/today?date=2000-01-01').get_json()
        assert data['games'] == []
