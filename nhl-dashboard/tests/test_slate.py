"""Tests for _ensure_team() helper and refresh_slate() auto-append behaviour (Issue #113)."""
import logging
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import Team, Game


_STATS_TEAMS = [
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

_SCHEDULE_NOW_TOR_BOS = {
    "gameWeek": [
        {
            "date": "2026-05-24",
            "games": [
                {
                    "id": 2026010001,
                    "startTimeUTC": "2026-05-24T23:00:00Z",
                    "gameState": "FUT",
                    "venue": {"default": "Scotiabank Arena"},
                    "awayTeam": {
                        "abbrev": "TOR",
                        "placeName": {"default": "Toronto"},
                        "commonName": {"default": "Maple Leafs"},
                    },
                    "homeTeam": {
                        "abbrev": "BOS",
                        "placeName": {"default": "Boston"},
                        "commonName": {"default": "Bruins"},
                    },
                }
            ],
        }
    ]
}

_SCHEDULE_NOW_ALLSTAR = {
    "gameWeek": [
        {
            "date": "2026-05-24",
            "games": [
                {
                    "id": 2026020001,
                    "startTimeUTC": "2026-05-24T20:00:00Z",
                    "gameState": "FUT",
                    "venue": {"default": "Arena"},
                    "awayTeam": {
                        "abbrev": "ASW",
                        "placeName": {"default": "All"},
                        "commonName": {"default": "Stars West"},
                    },
                    "homeTeam": {
                        "abbrev": "ASE",
                        "placeName": {"default": "All"},
                        "commonName": {"default": "Stars East"},
                    },
                }
            ],
        }
    ]
}


class TestEnsureTeam:
    def test_ensure_team_known_team_no_insert(self, db, team_factory):
        """_ensure_team() does not insert a row when the team already exists in the DB."""
        team_factory("TOR", "Toronto Maple Leafs")
        count_before = len(db.session.scalars(select(Team)).all())

        from services.slate import _ensure_team

        obj = {"abbrev": "TOR", "placeName": {"default": "Toronto"}, "commonName": {"default": "Maple Leafs"}}
        _ensure_team("TOR", obj, _STATS_TEAMS)

        assert len(db.session.scalars(select(Team)).all()) == count_before

    def test_ensure_team_unknown_found_in_stats_api_inserts_full_row(self, db, caplog):
        """_ensure_team() inserts a full Team row when the stats API has a match."""
        from services.slate import _ensure_team

        xyz_stats = [
            {
                "id": 99,
                "franchiseId": 88,
                "fullName": "Somewhere Team",
                "leagueId": 133,
                "rawTricode": "XYZ",
                "triCode": "XYZ",
            }
        ]
        obj = {"abbrev": "XYZ", "placeName": {"default": "Somewhere"}, "commonName": {"default": "Team"}}

        with caplog.at_level(logging.WARNING, logger="services.slate"):
            _ensure_team("XYZ", obj, xyz_stats)

        team = db.session.get(Team, "XYZ")
        assert team is not None
        assert team.team_id == 99
        assert team.franchise_id == 88
        assert team.full_name == "Somewhere Team"
        assert team.league_id == 133
        assert team.raw_tricode == "XYZ"
        assert any("[slate] Auto-appended unknown team: XYZ" in r.message for r in caplog.records)

    def test_ensure_team_unknown_not_in_stats_api_inserts_minimal_row(self, db, caplog):
        """_ensure_team() inserts a minimal row with NULLs when the team is absent from the stats API."""
        from services.slate import _ensure_team

        obj = {"abbrev": "ASW", "placeName": {"default": "All"}, "commonName": {"default": "Stars West"}}

        with caplog.at_level(logging.WARNING, logger="services.slate"):
            _ensure_team("ASW", obj, [])  # empty list → no stats API match

        team = db.session.get(Team, "ASW")
        assert team is not None
        assert team.team_id is None
        assert team.franchise_id is None
        assert team.league_id is None
        assert team.raw_tricode is None
        assert any(
            "[slate] Auto-appended unrecognised team (no stats API match): ASW" in r.message
            for r in caplog.records
        )

    def test_ensure_team_known_team_no_warning_logged(self, db, team_factory, caplog):
        """_ensure_team() emits no warning when the team already exists."""
        team_factory("TOR", "Toronto Maple Leafs")

        from services.slate import _ensure_team

        obj = {"abbrev": "TOR"}
        with caplog.at_level(logging.WARNING, logger="services.slate"):
            _ensure_team("TOR", obj, _STATS_TEAMS)

        assert not any("Auto-appended" in r.message for r in caplog.records)


class TestRefreshSlateEnsureTeam:
    def test_refresh_slate_known_teams_no_auto_append(self, db, team_factory, caplog):
        """refresh_slate() writes the game row without auto-appending when both teams already exist."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        from services.slate import refresh_slate

        with patch("nhl_client.get_schedule_now", return_value=_SCHEDULE_NOW_TOR_BOS), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            with caplog.at_level(logging.WARNING, logger="services.slate"):
                refresh_slate()

        assert not any("Auto-appended" in r.message for r in caplog.records)
        assert len(db.session.scalars(select(Game)).all()) == 1

    def test_refresh_slate_unknown_team_found_in_stats_api(self, db, caplog):
        """refresh_slate() auto-appends a full row for a missing team found in the stats API."""
        from services.slate import refresh_slate

        with patch("nhl_client.get_schedule_now", return_value=_SCHEDULE_NOW_TOR_BOS), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            with caplog.at_level(logging.WARNING, logger="services.slate"):
                refresh_slate()

        tor = db.session.get(Team, "TOR")
        assert tor is not None
        assert tor.team_id == 10
        assert any("[slate] Auto-appended unknown team: TOR" in r.message for r in caplog.records)

    def test_refresh_slate_unknown_team_not_in_stats_api(self, db, caplog):
        """refresh_slate() auto-appends a minimal row for an unrecognised team (e.g. All-Star)."""
        from services.slate import refresh_slate

        with patch("nhl_client.get_schedule_now", return_value=_SCHEDULE_NOW_ALLSTAR), \
             patch("nhl_client.get_all_teams", return_value=[]):
            with caplog.at_level(logging.WARNING, logger="services.slate"):
                refresh_slate()

        asw = db.session.get(Team, "ASW")
        assert asw is not None
        assert asw.team_id is None
        assert any(
            "[slate] Auto-appended unrecognised team (no stats API match): ASW" in r.message
            for r in caplog.records
        )
        assert len(db.session.scalars(select(Game)).all()) == 1

    def test_refresh_slate_stats_api_failure_falls_back_gracefully(self, db, caplog):
        """refresh_slate() logs an error and inserts minimal rows when get_all_teams() raises."""
        from services.slate import refresh_slate

        with patch("nhl_client.get_schedule_now", return_value=_SCHEDULE_NOW_TOR_BOS), \
             patch("nhl_client.get_all_teams", side_effect=Exception("timeout")):
            with caplog.at_level(logging.ERROR, logger="services.slate"):
                refresh_slate()

        tor = db.session.get(Team, "TOR")
        assert tor is not None
        assert tor.team_id is None
        assert len(db.session.scalars(select(Game)).all()) == 1
        assert any(r.levelno == logging.ERROR for r in caplog.records)

    def test_refresh_slate_calls_get_all_teams_once_per_refresh(self, db):
        """refresh_slate() fetches the full teams list exactly once per call."""
        from services.slate import refresh_slate

        with patch("nhl_client.get_schedule_now", return_value=_SCHEDULE_NOW_TOR_BOS), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS) as mock_get_teams:
            refresh_slate()

        mock_get_teams.assert_called_once()
