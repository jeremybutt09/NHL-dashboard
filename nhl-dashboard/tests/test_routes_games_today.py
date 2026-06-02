"""Integration tests for GET /api/games/today endpoint (Issue #92)."""
import pytest
from datetime import datetime, timezone


class TestGamesTodayPopulated:
    """Scenario: populated live game in boxscore table."""

    @pytest.fixture(autouse=True)
    def seed_db(self, boxscore_factory):
        """Seed DB with one live boxscore game."""
        self.game = boxscore_factory(
            'TOR', 'BOS',
            away_name='Toronto Maple Leafs',
            home_name='Boston Bruins',
            game_state='LIVE', away_score=2, home_score=1, period='2', clock='10:00',
        )

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

    def test_games_today_ml_is_null_without_partner_id(self, client):
        """ml is null when no partner_id is provided (no consensus odds source)."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['ml'] is None

    def test_games_today_fair_is_null(self, client):
        """fair is null — no odds data to compute from."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['fair'] is None

    def test_games_today_edge_is_null(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['edge'] is None

    def test_games_today_sparkline_is_empty_list(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['movement_24h'] == []

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


class TestGamesTodayEmpty:
    """Scenario: no game rows in DB returns empty games list."""

    def test_games_today_empty_returns_200(self, client):
        assert client.get('/api/games/today').status_code == 200

    def test_games_today_empty_returns_empty_games_list(self, client):
        data = client.get('/api/games/today').get_json()
        assert data['games'] == []


class TestGamesTodayMissingOdds:
    """Scenario: game with no partner odds returns null ml/edge and empty sparkline."""

    @pytest.fixture(autouse=True)
    def seed_db(self, boxscore_factory):
        """Seed DB with one boxscore game but no odds or fair rows."""
        self.game = boxscore_factory('TOR', 'BOS')

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

    def test_games_today_excludes_game_with_past_game_date(self, client, db):
        """A Boxscore with a past game_date is excluded from today's response."""
        from datetime import datetime
        from models import Boxscore

        bs = Boxscore(
            game_id=9001,
            away_abbrev='TOR', home_abbrev='BOS',
            game_date='2020-01-01',
            start_time_est=datetime(2020, 1, 1, 19, 0),
            game_state='FUT',
        )
        db.session.add(bs)
        db.session.commit()

        data = client.get('/api/games/today').get_json()
        assert 9001 not in [g['game_id'] for g in data['games']]

    def test_games_today_et_boundary_excludes_utc_next_day_game(self, client, db):
        """A game dated ET-tomorrow is excluded when today_et() is mocked to return ET-today."""
        from datetime import datetime
        from models import Boxscore
        from unittest.mock import patch

        bs = Boxscore(
            game_id=9002,
            away_abbrev='TOR', home_abbrev='BOS',
            game_date='2026-05-27',
            start_time_est=datetime(2026, 5, 27, 0, 30),
            game_state='FUT',
        )
        db.session.add(bs)
        db.session.commit()

        # Simulate: ET clock still shows May 26, UTC already shows May 27
        with patch("services.slate.today_et", return_value="2026-05-26"):
            data = client.get('/api/games/today').get_json()

        assert 9002 not in [g['game_id'] for g in data['games']]

    def test_games_today_et_boundary_includes_et_today_game(self, client, db):
        """A game dated ET-today is included even when it's already past midnight UTC."""
        from datetime import datetime
        from models import Boxscore
        from unittest.mock import patch

        bs = Boxscore(
            game_id=9003,
            away_abbrev='TOR', home_abbrev='BOS',
            game_date='2026-05-26',
            start_time_est=datetime(2026, 5, 26, 19, 0),
            game_state='FUT',
        )
        db.session.add(bs)
        db.session.commit()

        # Simulate: ET clock shows May 26 (23:30 ET), UTC shows May 27 (03:30 UTC)
        with patch("services.slate.today_et", return_value="2026-05-26"):
            data = client.get('/api/games/today').get_json()

        assert 9003 in [g['game_id'] for g in data['games']]


class TestGamesTodayFinalScores:
    """Scenario: final game shows actual scores in the live block (Issue #151)."""

    @pytest.fixture(autouse=True)
    def seed_db(self, boxscore_factory):
        """Seed DB with one final boxscore game that has real scores."""
        self.game = boxscore_factory(
            'CAR', 'MTL',
            away_name='Carolina Hurricanes',
            home_name='Montreal Canadiens',
            game_state='FINAL', away_score=3, home_score=2,
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
    def seed_db(self, boxscore_factory):
        """Seed DB with one scheduled boxscore game that has no score data yet."""
        self.game = boxscore_factory(
            'TOR', 'BOS',
            game_state='FUT', away_score=0, home_score=0,
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
    def seed_db(self, boxscore_factory):
        """Seed DB with boxscore games on two different dates."""
        self.past_game = boxscore_factory(
            'TOR', 'BOS',
            game_state='FINAL', away_score=3, home_score=2,
            game_date='2026-01-15',
        )
        self.today_game = boxscore_factory(
            'EDM', 'VAN',
            game_state='FUT', away_score=0, home_score=0,
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


# ── Issue #154: read from boxscore, not live_game ─────────────────────────────

class TestGamesTodayBoxscoreSource:
    """Verify /api/games/today returns games seeded in boxscore (Issue #154)."""

    @pytest.fixture(autouse=True)
    def seed_db(self, boxscore_factory):
        self.bs = boxscore_factory(
            'TOR', 'BOS',
            away_name='Toronto Maple Leafs',
            home_name='Boston Bruins',
            game_state='LIVE',
            away_score=2, home_score=1,
            period='2nd', clock='10:00',
        )

    def test_games_today_returns_boxscore_game(self, client):
        """A game seeded only in boxscore must appear in the response."""
        data = client.get('/api/games/today').get_json()
        assert self.bs.game_id in [g['game_id'] for g in data['games']]

    def test_games_today_boxscore_game_has_required_fields(self, client):
        """Response game must include all required top-level fields."""
        game = client.get('/api/games/today').get_json()['games'][0]
        for field in ('game_id', 'away', 'home', 'status', 'ml', 'fair', 'edge', 'movement_24h'):
            assert field in game, f"Missing field: {field}"

    def test_games_today_boxscore_team_codes_correct(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['away']['code'] == 'TOR'
        assert game['home']['code'] == 'BOS'

    def test_games_today_boxscore_team_names_correct(self, client):
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['away']['name'] == 'Toronto Maple Leafs'
        assert game['home']['name'] == 'Boston Bruins'

    def test_games_today_boxscore_live_block_present(self, client):
        """A LIVE boxscore game must include a non-null live block."""
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['live'] is not None

    def test_games_today_boxscore_live_block_has_scores(self, client):
        live = client.get('/api/games/today').get_json()['games'][0]['live']
        assert live['away_score'] == 2
        assert live['home_score'] == 1


class TestGamesTodayGameStateTranslation:
    """game_state raw values map to correct status strings (Issue #154)."""

    def test_game_state_live_maps_to_live(self, client, boxscore_factory):
        boxscore_factory('TOR', 'BOS', game_state='LIVE')
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'live'

    def test_game_state_crit_maps_to_live(self, client, boxscore_factory):
        boxscore_factory('TOR', 'BOS', game_state='CRIT')
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'live'

    def test_game_state_final_maps_to_final(self, client, boxscore_factory):
        boxscore_factory('TOR', 'BOS', game_state='FINAL')
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'final'

    def test_game_state_off_maps_to_final(self, client, boxscore_factory):
        boxscore_factory('TOR', 'BOS', game_state='OFF')
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'final'

    def test_game_state_fut_maps_to_scheduled(self, client, boxscore_factory):
        boxscore_factory('TOR', 'BOS', game_state='FUT')
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'scheduled'

    def test_game_state_pre_maps_to_scheduled(self, client, boxscore_factory):
        boxscore_factory('TOR', 'BOS', game_state='PRE')
        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['status'] == 'scheduled'


class TestGamesTodayBoxscoreOnly:
    """Route serves games from boxscore table only (Issue #154)."""

    def test_games_today_boxscore_only_returns_game(self, client, boxscore_factory):
        """A game seeded only in the boxscore table appears in the response."""
        bs = boxscore_factory('EDM', 'VAN', game_state='FUT')
        data = client.get('/api/games/today').get_json()
        assert bs.game_id in [g['game_id'] for g in data['games']]

    def test_games_today_boxscore_only_returns_200(self, client, boxscore_factory):
        boxscore_factory('EDM', 'VAN', game_state='FUT')
        assert client.get('/api/games/today').status_code == 200
