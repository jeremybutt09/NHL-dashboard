"""Tests for NhlOddsLine model, _insert_odds_lines helper, and prune job (Issue #119)."""
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import LiveGame, NhlOddsLine, NhlOddsPartner


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _seed_partners(db, partner_ids=(7, 9)):
    """Insert minimal NhlOddsPartner rows for the given partner IDs."""
    for pid in partner_ids:
        db.session.add(NhlOddsPartner(partner_id=pid, name=f"Partner{pid}"))
    db.session.commit()


def _seed_game(db, game_id=2026030001):
    """Insert a Game row with a known game_id."""
    db.session.add(LiveGame(
        game_id=game_id,
        start_est=datetime(2026, 5, 24, 23, 0, tzinfo=timezone.utc),
        status="scheduled",
    ))
    db.session.commit()
    return game_id


def _make_score_now(games=None, partners=None):
    """Build a minimal /v1/score/now response payload."""
    payload = {"currentDate": "2026-05-24", "games": games or [], "oddsPartners": partners or []}
    return payload


def _game_with_odds(game_id=2026030001, away_odds=None, home_odds=None):
    """Return a single game dict with the given odds arrays."""
    return {
        "id": game_id,
        "gameState": "FUT",
        "awayTeam": {"abbrev": "COL", "odds": away_odds or []},
        "homeTeam": {"abbrev": "VGK", "odds": home_odds or []},
        "periodDescriptor": {},
        "clock": {},
    }


# ── NhlOddsLine model ─────────────────────────────────────────────────────────

class TestNhlOddsLineModel:
    def test_nhl_odds_line_model_stores_all_columns(self, db):
        """NhlOddsLine persists all columns correctly."""
        _seed_partners(db)
        game_id = _seed_game(db)
        now = datetime.now(timezone.utc)

        row = NhlOddsLine(
            game_id=game_id,
            partner_id=7,
            fetched_at=now,
            away_value="-152",
            home_value="+126",
        )
        db.session.add(row)
        db.session.commit()

        saved = db.session.scalars(select(NhlOddsLine)).first()
        assert saved is not None
        assert saved.game_id == game_id
        assert saved.partner_id == 7
        assert saved.away_value == "-152"
        assert saved.home_value == "+126"
        assert saved.fetched_at is not None

    def test_nhl_odds_line_id_is_autoincrement_pk(self, db):
        """id column is auto-assigned surrogate primary key."""
        _seed_partners(db)
        game_id = _seed_game(db)
        now = datetime.now(timezone.utc)

        r1 = NhlOddsLine(game_id=game_id, partner_id=7, fetched_at=now, away_value="-152", home_value="+126")
        r2 = NhlOddsLine(game_id=game_id, partner_id=9, fetched_at=now, away_value="-155", home_value="+130")
        db.session.add_all([r1, r2])
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 2
        assert rows[0].id != rows[1].id

    def test_nhl_odds_line_fetched_at_not_null(self, db):
        """fetched_at is NOT NULL — omitting it raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        _seed_partners(db)
        game_id = _seed_game(db)

        db.session.add(NhlOddsLine(game_id=game_id, partner_id=7, away_value="-152", home_value="+126"))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

    def test_nhl_odds_line_decimal_format_values(self, db):
        """Decimal format odds strings (European style) are stored verbatim."""
        _seed_partners(db, partner_ids=(3,))
        game_id = _seed_game(db)
        now = datetime.now(timezone.utc)

        db.session.add(NhlOddsLine(
            game_id=game_id,
            partner_id=3,
            fetched_at=now,
            away_value="1.67",
            home_value="2.24",
        ))
        db.session.commit()

        saved = db.session.scalars(select(NhlOddsLine)).first()
        assert saved.away_value == "1.67"
        assert saved.home_value == "2.24"


# ── _insert_odds_lines helper ─────────────────────────────────────────────────

class TestInsertOddsLines:
    def test_insert_odds_lines_inserts_one_row_per_partner(self, db):
        """4 partners in the odds array → 4 rows inserted."""
        _seed_partners(db, partner_ids=(7, 9, 3, 6))
        game_id = _seed_game(db)

        away_odds = [
            {"providerId": 7, "value": "-152"},
            {"providerId": 9, "value": "-155"},
            {"providerId": 3, "value": "1.67"},
            {"providerId": 6, "value": "1.70"},
        ]
        home_odds = [
            {"providerId": 7, "value": "+126"},
            {"providerId": 9, "value": "+130"},
            {"providerId": 3, "value": "2.24"},
            {"providerId": 6, "value": "2.30"},
        ]

        from services.scores import _insert_odds_lines
        now = datetime.now(timezone.utc)
        _insert_odds_lines(game_id, away_odds, home_odds, now)
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 4
        partner_ids = {r.partner_id for r in rows}
        assert partner_ids == {7, 9, 3, 6}

    def test_insert_odds_lines_stores_correct_values(self, db):
        """away_value and home_value are stored verbatim for each partner."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        away_odds = [{"providerId": 7, "value": "-152"}]
        home_odds = [{"providerId": 7, "value": "+126"}]

        from services.scores import _insert_odds_lines
        now = datetime.now(timezone.utc)
        _insert_odds_lines(game_id, away_odds, home_odds, now)
        db.session.commit()

        row = db.session.scalars(select(NhlOddsLine)).first()
        assert row.away_value == "-152"
        assert row.home_value == "+126"
        assert row.game_id == game_id
        assert row.partner_id == 7

    def test_insert_odds_lines_fetched_at_is_utc_now(self, db):
        """fetched_at matches the timestamp passed in."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        away_odds = [{"providerId": 7, "value": "-152"}]
        home_odds = [{"providerId": 7, "value": "+126"}]

        from services.scores import _insert_odds_lines
        now = datetime(2026, 5, 24, 15, 0, 0, tzinfo=timezone.utc)
        _insert_odds_lines(game_id, away_odds, home_odds, now)
        db.session.commit()

        row = db.session.scalars(select(NhlOddsLine)).first()
        # SQLite strips tzinfo on read; compare as naive UTC
        assert row.fetched_at == now.replace(tzinfo=None)

    def test_insert_odds_lines_deduplication_within_cooldown(self, db):
        """A second call within 3 minutes does not insert a duplicate row."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        away_odds = [{"providerId": 7, "value": "-152"}]
        home_odds = [{"providerId": 7, "value": "+126"}]

        from services.scores import _insert_odds_lines
        t1 = datetime(2026, 5, 24, 15, 0, 0, tzinfo=timezone.utc)
        _insert_odds_lines(game_id, away_odds, home_odds, t1)
        db.session.commit()

        # Second call 90 seconds later — within 3-minute cooldown
        t2 = t1 + timedelta(seconds=90)
        _insert_odds_lines(game_id, away_odds, home_odds, t2)
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 1

    def test_insert_odds_lines_inserts_after_cooldown_elapsed(self, db):
        """A second call after the 3-minute cooldown does insert a new row."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        away_odds = [{"providerId": 7, "value": "-152"}]
        home_odds = [{"providerId": 7, "value": "+126"}]

        from services.scores import _insert_odds_lines
        t1 = datetime(2026, 5, 24, 15, 0, 0, tzinfo=timezone.utc)
        _insert_odds_lines(game_id, away_odds, home_odds, t1)
        db.session.commit()

        # Second call 4 minutes later — cooldown elapsed
        t2 = t1 + timedelta(minutes=4)
        _insert_odds_lines(game_id, away_odds, home_odds, t2)
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 2

    def test_insert_odds_lines_no_odds_inserts_nothing(self, db):
        """Empty away/home odds arrays → no rows inserted, no error raised."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        from services.scores import _insert_odds_lines
        now = datetime.now(timezone.utc)
        _insert_odds_lines(game_id, [], [], now)  # must not raise
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert rows == []

    def test_insert_odds_lines_absent_odds_key_no_error(self, db):
        """None away/home odds → no rows inserted, no error raised."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        from services.scores import _insert_odds_lines
        now = datetime.now(timezone.utc)
        _insert_odds_lines(game_id, None, None, now)  # must not raise
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert rows == []

    def test_insert_odds_lines_partial_odds_inserts_matched_only(self, db):
        """Only partners present in both away and home arrays get a row."""
        _seed_partners(db, partner_ids=(7, 9))
        game_id = _seed_game(db)

        # Partner 7 in both; partner 9 only in away
        away_odds = [
            {"providerId": 7, "value": "-152"},
            {"providerId": 9, "value": "-155"},
        ]
        home_odds = [
            {"providerId": 7, "value": "+126"},
            # partner 9 absent
        ]

        from services.scores import _insert_odds_lines
        now = datetime.now(timezone.utc)
        _insert_odds_lines(game_id, away_odds, home_odds, now)
        db.session.commit()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 1
        assert rows[0].partner_id == 7

    def test_insert_odds_lines_unknown_partner_skipped_with_warning(self, db, caplog):
        """Unknown providerId logs a warning and is skipped; others still inserted."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        # providerId 99 has no nhl_odds_partner row
        away_odds = [
            {"providerId": 7, "value": "-152"},
            {"providerId": 99, "value": "-199"},
        ]
        home_odds = [
            {"providerId": 7, "value": "+126"},
            {"providerId": 99, "value": "+165"},
        ]

        from services.scores import _insert_odds_lines
        now = datetime.now(timezone.utc)

        with caplog.at_level(logging.WARNING, logger="services.scores"):
            _insert_odds_lines(game_id, away_odds, home_odds, now)
        db.session.commit()

        # Only partner 7 should be inserted
        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 1
        assert rows[0].partner_id == 7

        # Warning must name the unknown partner_id
        assert any("99" in rec.message and "skipping" in rec.message.lower()
                   for rec in caplog.records)


# ── refresh_scores integration ────────────────────────────────────────────────

class TestRefreshScoresOddsLineIntegration:
    def test_refresh_scores_inserts_odds_lines_for_all_partners(self, db):
        """refresh_scores() inserts one NhlOddsLine row per partner when odds present."""
        _seed_partners(db, partner_ids=(7, 9))
        game_id = _seed_game(db)

        away_odds = [
            {"providerId": 7, "value": "-152"},
            {"providerId": 9, "value": "-155"},
        ]
        home_odds = [
            {"providerId": 7, "value": "+126"},
            {"providerId": 9, "value": "+130"},
        ]
        games = [_game_with_odds(game_id=game_id, away_odds=away_odds, home_odds=home_odds)]
        api_data = _make_score_now(games=games)

        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 2
        assert {r.partner_id for r in rows} == {7, 9}

    def test_refresh_scores_no_odds_no_error(self, db):
        """refresh_scores() handles games with empty odds arrays without error."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        games = [_game_with_odds(game_id=game_id, away_odds=[], home_odds=[])]
        api_data = _make_score_now(games=games)

        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()  # must not raise

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert rows == []


# ── prune_nhl_odds_lines ──────────────────────────────────────────────────────

class TestPruneNhlOddsLines:
    def test_prune_nhl_odds_lines_deletes_rows_older_than_30_days(self, db):
        """Rows with fetched_at older than 30 days are deleted."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        now = datetime.now(timezone.utc)
        old_ts = now - timedelta(days=31)
        db.session.add(NhlOddsLine(
            game_id=game_id, partner_id=7,
            fetched_at=old_ts, away_value="-152", home_value="+126",
        ))
        db.session.commit()

        from services.slate import prune_nhl_odds_lines
        prune_nhl_odds_lines()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert rows == []

    def test_prune_nhl_odds_lines_retains_recent_rows(self, db):
        """Rows within the 30-day window are not deleted."""
        _seed_partners(db, partner_ids=(7,))
        game_id = _seed_game(db)

        now = datetime.now(timezone.utc)
        recent_ts = now - timedelta(days=5)
        db.session.add(NhlOddsLine(
            game_id=game_id, partner_id=7,
            fetched_at=recent_ts, away_value="-152", home_value="+126",
        ))
        db.session.commit()

        from services.slate import prune_nhl_odds_lines
        prune_nhl_odds_lines()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 1

    def test_prune_nhl_odds_lines_mixed_ages(self, db):
        """Only rows older than 30 days are deleted; recent ones are kept."""
        _seed_partners(db, partner_ids=(7, 9))
        game_id = _seed_game(db)

        now = datetime.now(timezone.utc)
        old_ts = now - timedelta(days=31)
        recent_ts = now - timedelta(days=10)

        db.session.add_all([
            NhlOddsLine(game_id=game_id, partner_id=7, fetched_at=old_ts,
                        away_value="-152", home_value="+126"),
            NhlOddsLine(game_id=game_id, partner_id=9, fetched_at=recent_ts,
                        away_value="-155", home_value="+130"),
        ])
        db.session.commit()

        from services.slate import prune_nhl_odds_lines
        prune_nhl_odds_lines()

        rows = db.session.scalars(select(NhlOddsLine)).all()
        assert len(rows) == 1
        assert rows[0].partner_id == 9
