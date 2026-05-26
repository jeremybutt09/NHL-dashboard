"""Tests for refresh_scores() as single source of truth for game table population (Issue #130).

Covers three acceptance-criteria scenarios:
  Scenario 1 — Pre-game (scheduled): missing fields handled gracefully, volatile
               columns set to null.
  Scenario 2 — Live game: period, clock, and sog populated from API.
  Scenario 3 — Final game: status "final", clock defaults to "00:00".
  Upsert: game rows missing from DB are created from /v1/score/now metadata.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import Game, Team


# ── Fixtures ──────────────────────────────────────────────────────────────────

_GAME_ID = 2026030001

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

# Scenario 1 — pre-game: no clock, periodDescriptor, score, or sog fields
_SCORE_NOW_FUT = {
    "currentDate": "2026-05-25",
    "games": [
        {
            "id": _GAME_ID,
            "gameState": "FUT",
            "startTimeUTC": "2026-05-25T23:00:00Z",
            "gameDate": "2026-05-25",
            "venue": {"default": "Scotiabank Arena"},
            "awayTeam": {"abbrev": "TOR"},
            "homeTeam": {"abbrev": "BOS"},
        }
    ],
    "oddsPartners": [],
}

# Scenario 2 — live game: all live fields present
_SCORE_NOW_LIVE = {
    "currentDate": "2026-05-25",
    "games": [
        {
            "id": _GAME_ID,
            "gameState": "LIVE",
            "startTimeUTC": "2026-05-25T23:00:00Z",
            "gameDate": "2026-05-25",
            "venue": {"default": "Scotiabank Arena"},
            "awayTeam": {"abbrev": "TOR", "score": 2, "sog": 18},
            "homeTeam": {"abbrev": "BOS", "score": 1, "sog": 14},
            "periodDescriptor": {"number": 2, "periodType": "REG"},
            "clock": {"timeRemaining": "12:34"},
        }
    ],
    "oddsPartners": [],
}

# Scenario 2 — live game: OT period type
_SCORE_NOW_LIVE_OT = {
    "currentDate": "2026-05-25",
    "games": [
        {
            "id": _GAME_ID,
            "gameState": "CRIT",
            "startTimeUTC": "2026-05-25T23:00:00Z",
            "gameDate": "2026-05-25",
            "venue": {"default": "Scotiabank Arena"},
            "awayTeam": {"abbrev": "TOR", "score": 2, "sog": 28},
            "homeTeam": {"abbrev": "BOS", "score": 2, "sog": 26},
            "periodDescriptor": {"number": 4, "periodType": "OT"},
            "clock": {"timeRemaining": "03:12"},
        }
    ],
    "oddsPartners": [],
}

# Scenario 3 — final game: scores present, clock absent from API
_SCORE_NOW_FINAL_NO_CLOCK = {
    "currentDate": "2026-05-25",
    "games": [
        {
            "id": _GAME_ID,
            "gameState": "OFF",
            "startTimeUTC": "2026-05-25T23:00:00Z",
            "gameDate": "2026-05-25",
            "venue": {"default": "Scotiabank Arena"},
            "awayTeam": {"abbrev": "TOR", "score": 3},
            "homeTeam": {"abbrev": "BOS", "score": 2},
            "periodDescriptor": {"number": 3, "periodType": "REG"},
            "gameOutcome": {"lastPeriodType": "REG"},
        }
    ],
    "oddsPartners": [],
}

# Scenario 3 — final game: FINAL state (not OFF)
_SCORE_NOW_FINAL_STATE = {
    "currentDate": "2026-05-25",
    "games": [
        {
            "id": _GAME_ID,
            "gameState": "FINAL",
            "startTimeUTC": "2026-05-25T23:00:00Z",
            "gameDate": "2026-05-25",
            "venue": {"default": "Scotiabank Arena"},
            "awayTeam": {"abbrev": "TOR", "score": 4},
            "homeTeam": {"abbrev": "BOS", "score": 1},
            "periodDescriptor": {"number": 3, "periodType": "REG"},
            "gameOutcome": {"lastPeriodType": "REG"},
        }
    ],
    "oddsPartners": [],
}


def _seed_game(db, game_id=_GAME_ID, away_code="TOR", home_code="BOS",
               status="scheduled", period=None, clock=None,
               away_score=0, home_score=0, away_sog=None, home_sog=None):
    """Insert a Game row with specified values."""
    game = Game(
        game_id=game_id,
        away_code=away_code,
        home_code=home_code,
        status=status,
        period=period,
        clock=clock,
        away_score=away_score,
        home_score=home_score,
        away_sog=away_sog,
        home_sog=home_sog,
        start_est=datetime(2026, 5, 25, 23, 0, tzinfo=timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.session.add(game)
    db.session.commit()
    return game


# ── Scenario 1: Pre-game (scheduled) ─────────────────────────────────────────

class TestRefreshScoresPreGame:
    def _run(self, db, team_factory):
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")
        _seed_game(db)

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        return db.session.get(Game, _GAME_ID)

    def test_refresh_scores_scheduled_status_is_scheduled(self, db, team_factory):
        """Pre-game gameState FUT → status 'scheduled'."""
        game = self._run(db, team_factory)
        assert game.status == "scheduled"

    def test_refresh_scores_scheduled_period_is_null(self, db, team_factory):
        """Pre-game with no periodDescriptor → period is None, not '1st'."""
        game = self._run(db, team_factory)
        assert game.period is None

    def test_refresh_scores_scheduled_clock_is_null(self, db, team_factory):
        """Pre-game with no clock field → clock is None."""
        game = self._run(db, team_factory)
        assert game.clock is None

    def test_refresh_scores_scheduled_away_sog_is_null(self, db, team_factory):
        """Pre-game with no sog field → away_sog is None."""
        game = self._run(db, team_factory)
        assert game.away_sog is None

    def test_refresh_scores_scheduled_home_sog_is_null(self, db, team_factory):
        """Pre-game with no sog field → home_sog is None."""
        game = self._run(db, team_factory)
        assert game.home_sog is None

    def test_refresh_scores_scheduled_away_score_defaults_to_zero(self, db, team_factory):
        """Pre-game with no score field → away_score is 0."""
        game = self._run(db, team_factory)
        assert game.away_score == 0

    def test_refresh_scores_scheduled_home_score_defaults_to_zero(self, db, team_factory):
        """Pre-game with no score field → home_score is 0."""
        game = self._run(db, team_factory)
        assert game.home_score == 0

    def test_refresh_scores_scheduled_no_error_for_missing_fields(self, db, team_factory):
        """refresh_scores() must not raise when clock/period/sog/score are all absent."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")
        _seed_game(db)

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            try:
                refresh_scores()
            except Exception as exc:
                pytest.fail(f"refresh_scores() must not raise for missing pre-game fields: {exc}")

    def test_refresh_scores_scheduled_nulls_sog_on_existing_live_row(self, db, team_factory):
        """A game that transitions from live→scheduled gets sog nulled (not preserved)."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")
        # Pre-seed a row that previously had live sog values
        _seed_game(db, status="live", period="2nd", clock="12:00", away_sog=22, home_sog=18)

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game.away_sog is None
        assert game.home_sog is None


# ── Scenario 2: Live game ─────────────────────────────────────────────────────

class TestRefreshScoresLiveGame:
    def _run(self, db, team_factory, payload=None):
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")
        _seed_game(db, status="scheduled")

        payload = payload or _SCORE_NOW_LIVE
        with patch("nhl_client.get_score_now", return_value=payload), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        return db.session.get(Game, _GAME_ID)

    def test_refresh_scores_live_status_is_live(self, db, team_factory):
        """gameState LIVE → status 'live'."""
        game = self._run(db, team_factory)
        assert game.status == "live"

    def test_refresh_scores_live_status_crit_is_live(self, db, team_factory):
        """gameState CRIT → status 'live' (critical game)."""
        game = self._run(db, team_factory, payload=_SCORE_NOW_LIVE_OT)
        assert game.status == "live"

    def test_refresh_scores_live_period_reflects_api(self, db, team_factory):
        """Live game → period is '2nd' from periodDescriptor.number=2."""
        game = self._run(db, team_factory)
        assert game.period == "2nd"

    def test_refresh_scores_live_period_ot(self, db, team_factory):
        """Live OT game → period is 'OT'."""
        game = self._run(db, team_factory, payload=_SCORE_NOW_LIVE_OT)
        assert game.period == "OT"

    def test_refresh_scores_live_clock_reflects_api(self, db, team_factory):
        """Live game → clock is timeRemaining from API."""
        game = self._run(db, team_factory)
        assert game.clock == "12:34"

    def test_refresh_scores_live_away_sog_updated(self, db, team_factory):
        """Live game → away_sog is updated from API."""
        game = self._run(db, team_factory)
        assert game.away_sog == 18

    def test_refresh_scores_live_home_sog_updated(self, db, team_factory):
        """Live game → home_sog is updated from API."""
        game = self._run(db, team_factory)
        assert game.home_sog == 14

    def test_refresh_scores_live_scores_updated(self, db, team_factory):
        """Live game → scores are set from awayTeam.score / homeTeam.score."""
        game = self._run(db, team_factory)
        assert game.away_score == 2
        assert game.home_score == 1


# ── Scenario 3: Final game ────────────────────────────────────────────────────

class TestRefreshScoresFinalGame:
    def _run(self, db, team_factory, payload=None):
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")
        # Pre-seed as live with a non-zero clock so we can detect if it's preserved vs. zeroed
        _seed_game(db, status="live", period="3rd", clock="04:22",
                   away_score=3, home_score=2, away_sog=30, home_sog=24)

        payload = payload or _SCORE_NOW_FINAL_NO_CLOCK
        with patch("nhl_client.get_score_now", return_value=payload), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        return db.session.get(Game, _GAME_ID)

    def test_refresh_scores_final_status_off_is_final(self, db, team_factory):
        """gameState OFF → status 'final'."""
        game = self._run(db, team_factory)
        assert game.status == "final"

    def test_refresh_scores_final_status_final_is_final(self, db, team_factory):
        """gameState FINAL → status 'final'."""
        game = self._run(db, team_factory, payload=_SCORE_NOW_FINAL_STATE)
        assert game.status == "final"

    def test_refresh_scores_final_clock_defaults_to_zero_when_absent(self, db, team_factory):
        """Final game with no clock field in API → clock is '00:00', not the old live value."""
        game = self._run(db, team_factory)
        # The API payload _SCORE_NOW_FINAL_NO_CLOCK has no 'clock' key.
        # Old live clock was '04:22'. It must NOT be preserved.
        assert game.clock == "00:00"

    def test_refresh_scores_final_away_score_stored(self, db, team_factory):
        """Final game → away_score is stored from API."""
        game = self._run(db, team_factory)
        assert game.away_score == 3

    def test_refresh_scores_final_home_score_stored(self, db, team_factory):
        """Final game → home_score is stored from API."""
        game = self._run(db, team_factory)
        assert game.home_score == 2


# ── Upsert: new game rows created from /v1/score/now ─────────────────────────

class TestRefreshScoresUpsertNewGame:
    def test_refresh_scores_creates_new_game_row_when_missing(self, db, team_factory):
        """Game absent from DB is inserted from /v1/score/now payload."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        assert db.session.get(Game, _GAME_ID) is None

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game is not None

    def test_refresh_scores_new_game_sets_away_code(self, db, team_factory):
        """Newly upserted game row has away_code from API."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game.away_code == "TOR"

    def test_refresh_scores_new_game_sets_home_code(self, db, team_factory):
        """Newly upserted game row has home_code from API."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game.home_code == "BOS"

    def test_refresh_scores_new_game_sets_start_est(self, db, team_factory):
        """Newly upserted game row has start_est derived from startTimeUTC."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game.start_est is not None
        # 2026-05-25T23:00:00Z = 19:00 EDT (UTC-4 in May)
        assert game.start_est.hour == 19

    def test_refresh_scores_new_game_sets_venue(self, db, team_factory):
        """Newly upserted game row has venue from API."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game.venue == "Scotiabank Arena"

    def test_refresh_scores_new_game_sets_game_date(self, db, team_factory):
        """Newly upserted game row has game_date from API."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game.game_date == "2026-05-25"

    def test_refresh_scores_upsert_is_idempotent(self, db, team_factory):
        """Calling refresh_scores() twice does not create duplicate game rows."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()
            refresh_scores()

        rows = db.session.scalars(
            select(Game).where(Game.game_id == _GAME_ID)
        ).all()
        assert len(rows) == 1

    def test_refresh_scores_new_game_auto_creates_team_rows(self, db):
        """refresh_scores() auto-creates minimal Team rows for unknown teams."""
        # No team_factory calls — teams do not exist in DB
        assert db.session.get(Team, "TOR") is None
        assert db.session.get(Team, "BOS") is None

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", return_value=_STATS_TEAMS):
            from services.scores import refresh_scores
            refresh_scores()

        # Teams should have been auto-created (full rows via _STATS_TEAMS)
        assert db.session.get(Team, "TOR") is not None
        assert db.session.get(Team, "BOS") is not None

    def test_refresh_scores_new_game_get_all_teams_failure_still_creates_row(self, db, team_factory):
        """Game row is created even when get_all_teams() fails (teams pre-exist in DB)."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")

        with patch("nhl_client.get_score_now", return_value=_SCORE_NOW_FUT), \
             patch("nhl_client.get_all_teams", side_effect=Exception("stats API down")):
            from services.scores import refresh_scores
            refresh_scores()

        game = db.session.get(Game, _GAME_ID)
        assert game is not None
        assert game.away_code == "TOR"
