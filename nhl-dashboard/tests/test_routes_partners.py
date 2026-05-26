"""Tests for GET /api/partners endpoint (Issue #137)."""
import pytest
from models import NhlOddsPartner, NhlOddsLine, LiveGame
from datetime import datetime, timezone


class TestGetPartnersEmpty:
    """Scenario: no partner rows in DB returns empty list."""

    def test_get_partners_returns_200(self, client):
        assert client.get('/api/partners').status_code == 200

    def test_get_partners_returns_json(self, client):
        assert client.get('/api/partners').content_type == 'application/json'

    def test_get_partners_returns_empty_list_when_no_partners(self, client):
        data = client.get('/api/partners').get_json()
        assert data == []


class TestGetPartnersPopulated:
    """Scenario: two partners in DB returns both in response."""

    @pytest.fixture(autouse=True)
    def seed_partners(self, db):
        db.session.add(NhlOddsPartner(partner_id=7, name='FanDuel', country='US'))
        db.session.add(NhlOddsPartner(partner_id=9, name='DraftKings', country='US'))
        db.session.commit()

    def test_get_partners_returns_list_of_two(self, client):
        data = client.get('/api/partners').get_json()
        assert len(data) == 2

    def test_get_partners_each_item_has_partner_id(self, client):
        data = client.get('/api/partners').get_json()
        for item in data:
            assert 'partner_id' in item

    def test_get_partners_each_item_has_name(self, client):
        data = client.get('/api/partners').get_json()
        for item in data:
            assert 'name' in item

    def test_get_partners_returns_correct_names(self, client):
        data = client.get('/api/partners').get_json()
        names = {item['name'] for item in data}
        assert names == {'FanDuel', 'DraftKings'}

    def test_get_partners_ordered_by_partner_id(self, client):
        data = client.get('/api/partners').get_json()
        ids = [item['partner_id'] for item in data]
        assert ids == sorted(ids)


class TestGamesTodayWithPartnerId:
    """Scenario: GET /api/games/today?partner_id=X returns partner-specific odds from nhl_odds_line."""

    @pytest.fixture(autouse=True)
    def seed_db(self, db, team_factory, game_factory):
        team_factory('TOR', 'Toronto Maple Leafs')
        team_factory('BOS', 'Boston Bruins')
        self.game = game_factory('TOR', 'BOS', status='scheduled')

        db.session.add(NhlOddsPartner(partner_id=7, name='FanDuel'))
        db.session.add(NhlOddsPartner(partner_id=9, name='DraftKings'))
        db.session.commit()

        db.session.add(NhlOddsLine(
            game_id=self.game.game_id,
            partner_id=7,
            fetched_at=datetime(2026, 5, 26, 15, 0, 0),
            away_value='-152',
            home_value='+126',
        ))
        db.session.commit()

    def test_games_today_with_partner_id_returns_200(self, client):
        assert client.get('/api/games/today?partner_id=7').status_code == 200

    def test_games_today_with_partner_id_uses_nhl_odds_line(self, client):
        game = client.get('/api/games/today?partner_id=7').get_json()['games'][0]
        assert game['ml'] is not None
        assert game['ml']['away'] == -152
        assert game['ml']['home'] == 126

    def test_games_today_with_partner_id_no_data_returns_null_ml(self, client):
        """Partner 9 has no NhlOddsLine rows — ml must be None, not an error."""
        game = client.get('/api/games/today?partner_id=9').get_json()['games'][0]
        assert game['ml'] is None

    def test_games_today_without_partner_id_uses_odds_snapshot(self, client, db):
        """Omitting partner_id falls back to OddsSnapshot consensus behaviour."""
        from models import OddsSnapshot
        db.session.add(OddsSnapshot(
            game_id=self.game.game_id,
            fetched_at=datetime(2026, 5, 26, 15, 0, 0),
            book='consensus',
            away_ml=-110,
            home_ml=100,
            away_implied=52.38,
            home_implied=50.0,
        ))
        db.session.commit()

        game = client.get('/api/games/today').get_json()['games'][0]
        assert game['ml'] is not None
        assert game['ml']['away'] == -110
        assert game['ml']['home'] == 100

    def test_games_today_with_partner_id_latest_row_used(self, client, db):
        """When multiple NhlOddsLine rows exist for the same game/partner, the most recent is used."""
        db.session.add(NhlOddsLine(
            game_id=self.game.game_id,
            partner_id=7,
            fetched_at=datetime(2026, 5, 26, 16, 0, 0),
            away_value='-160',
            home_value='+135',
        ))
        db.session.commit()

        game = client.get('/api/games/today?partner_id=7').get_json()['games'][0]
        assert game['ml']['away'] == -160
        assert game['ml']['home'] == 135
