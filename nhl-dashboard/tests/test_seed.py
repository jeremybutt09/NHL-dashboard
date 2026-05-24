"""Unit tests for the team seeding service (Issue #112)."""
import logging
from unittest.mock import patch, MagicMock

import httpx
import pytest
from sqlalchemy import select

from models import Team


_TWO_TEAMS = [
    {
        "id": 10,
        "franchiseId": 5,
        "fullName": "Toronto Maple Leafs",
        "leagueId": 133,
        "rawTricode": "TOR",
        "triCode": "TOR",
    },
    {
        "id": 6,
        "franchiseId": 6,
        "fullName": "Boston Bruins",
        "leagueId": 133,
        "rawTricode": "BOS",
        "triCode": "BOS",
    },
]


class TestSeedTeams:
    def test_seed_teams_upserts_all_teams(self, db):
        """seed_teams() inserts one Team row per team returned by the stats API."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", return_value=_TWO_TEAMS):
            seed_teams()

        rows = db.session.scalars(select(Team)).all()
        assert len(rows) == 2

    def test_seed_teams_stores_all_fields(self, db):
        """Each Team row stores team_id, franchise_id, full_name, league_id, raw_tricode, tri_code."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", return_value=_TWO_TEAMS):
            seed_teams()

        tor = db.session.get(Team, "TOR")
        assert tor is not None
        assert tor.team_id == 10
        assert tor.franchise_id == 5
        assert tor.full_name == "Toronto Maple Leafs"
        assert tor.league_id == 133
        assert tor.raw_tricode == "TOR"
        assert tor.tri_code == "TOR"

    def test_seed_teams_is_idempotent_no_duplicates(self, db):
        """Running seed_teams() twice with identical data creates no duplicate rows."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", return_value=_TWO_TEAMS):
            seed_teams()
            seed_teams()

        rows = db.session.scalars(select(Team)).all()
        assert len(rows) == 2

    def test_seed_teams_updates_changed_field_on_second_run(self, db):
        """A second seed run with changed data updates the row without creating a duplicate."""
        from services.seed import seed_teams

        with patch("services.seed.get_all_teams", return_value=[_TWO_TEAMS[0]]):
            seed_teams()

        mutated = dict(_TWO_TEAMS[0], fullName="Leafs Updated")
        with patch("services.seed.get_all_teams", return_value=[mutated]):
            seed_teams()

        tor = db.session.get(Team, "TOR")
        assert tor.full_name == "Leafs Updated"
        assert len(db.session.scalars(select(Team)).all()) == 1

    def test_seed_teams_logs_upserted_count_on_success(self, db, caplog):
        """seed_teams() emits '[seed] Upserted N teams' at INFO level after a successful run."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", return_value=_TWO_TEAMS):
            with caplog.at_level(logging.INFO, logger="services.seed"):
                seed_teams()

        assert any("[seed] Upserted 2 teams" in r.message for r in caplog.records)

    def test_seed_teams_api_failure_logs_warning(self, db, caplog):
        """seed_teams() logs a WARNING when get_all_teams() raises an exception."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", side_effect=Exception("timeout")):
            with caplog.at_level(logging.WARNING, logger="services.seed"):
                seed_teams()

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_seed_teams_api_failure_does_not_raise(self, db):
        """seed_teams() returns normally without raising when the stats API is unavailable."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", side_effect=Exception("connection refused")):
            seed_teams()  # must not raise

    def test_seed_teams_subsequent_call_succeeds_after_failure(self, db):
        """A successful seed run following a failed run upserts rows normally."""
        from services.seed import seed_teams
        with patch("services.seed.get_all_teams", side_effect=Exception("timeout")):
            seed_teams()

        with patch("services.seed.get_all_teams", return_value=_TWO_TEAMS):
            seed_teams()

        rows = db.session.scalars(select(Team)).all()
        assert len(rows) == 2


class TestGetAllTeams:
    def test_get_all_teams_returns_list_of_dicts(self):
        """get_all_teams() returns the 'data' list from the NHL stats API response."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"data": _TWO_TEAMS}

        with patch("nhl_client.httpx.get", return_value=mock_resp):
            from nhl_client import get_all_teams
            result = get_all_teams()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["triCode"] == "TOR"

    def test_get_all_teams_raises_on_5xx(self):
        """get_all_teams() propagates HTTPStatusError on a non-2xx response."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )

        with patch("nhl_client.httpx.get", return_value=mock_resp):
            from nhl_client import get_all_teams
            with pytest.raises(httpx.HTTPStatusError):
                get_all_teams()

    def test_get_all_teams_targets_stats_api_base_url(self):
        """get_all_teams() calls the stats REST endpoint, not the web API."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"data": []}

        with patch("nhl_client.httpx.get", return_value=mock_resp) as mock_get:
            from nhl_client import get_all_teams
            get_all_teams()

        called_url = mock_get.call_args[0][0]
        assert "api.nhle.com/stats/rest" in called_url
        assert "team" in called_url
