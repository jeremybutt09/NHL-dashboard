"""Tests for NhlOddsPartner model and _upsert_partners helper (Issue #118)."""
from unittest.mock import patch

import pytest
from sqlalchemy import select

from models import NhlOddsPartner


# ── Fixtures ──────────────────────────────────────────────────────────────────

_PARTNER_FANDUEL = {
    "partnerId": 7,
    "country": "CA",
    "name": "FanDuel",
    "imageUrl": "https://assets.nhle.com/betting_partner/fanduel.svg",
    "siteUrl": "https://fanduel.com",
    "bgColor": "#0078ff",
    "textColor": "#FFFFFF",
    "accentColor": "#FFFFFF",
}

_PARTNER_DRAFTKINGS = {
    "partnerId": 9,
    "country": "US",
    "name": "DraftKings",
    "imageUrl": "https://assets.nhle.com/betting_partner/draftkings.svg",
    "siteUrl": "https://draftkings.com",
    "bgColor": "#000000",
    "textColor": "#53D337",
    "accentColor": "#53D337",
}


def _make_score_now(partners=None, games=None):
    """Build a minimal /v1/score/now response."""
    payload = {"currentDate": "2026-05-24", "games": games or []}
    if partners is not None:
        payload["oddsPartners"] = partners
    return payload


# ── NhlOddsPartner model ──────────────────────────────────────────────────────

class TestNhlOddsPartnerModel:
    def test_nhl_odds_partner_model_stores_all_eight_columns(self, db):
        """NhlOddsPartner row persists all 8 columns from the NHL API partner shape."""
        partner = NhlOddsPartner(
            partner_id=7,
            country="CA",
            name="FanDuel",
            image_url="https://assets.nhle.com/betting_partner/fanduel.svg",
            site_url="https://fanduel.com",
            bg_color="#0078ff",
            text_color="#FFFFFF",
            accent_color="#FFFFFF",
        )
        db.session.add(partner)
        db.session.commit()

        row = db.session.get(NhlOddsPartner, 7)
        assert row is not None
        assert row.partner_id == 7
        assert row.country == "CA"
        assert row.name == "FanDuel"
        assert row.image_url == "https://assets.nhle.com/betting_partner/fanduel.svg"
        assert row.site_url == "https://fanduel.com"
        assert row.bg_color == "#0078ff"
        assert row.text_color == "#FFFFFF"
        assert row.accent_color == "#FFFFFF"

    def test_nhl_odds_partner_partner_id_is_integer_pk(self, db):
        """partner_id is used as the integer primary key (not auto-generated)."""
        partner = NhlOddsPartner(partner_id=9, name="DraftKings")
        db.session.add(partner)
        db.session.commit()

        row = db.session.get(NhlOddsPartner, 9)
        assert row is not None
        assert row.partner_id == 9

    def test_nhl_odds_partner_name_not_null_constraint(self, db):
        """name column is NOT NULL — omitting it raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        db.session.add(NhlOddsPartner(partner_id=1))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

    def test_nhl_odds_partner_upsert_idempotent(self, db):
        """db.session.merge() on same partner_id keeps exactly one row."""
        db.session.add(NhlOddsPartner(partner_id=7, name="FanDuel"))
        db.session.commit()

        db.session.merge(NhlOddsPartner(partner_id=7, name="FanDuel"))
        db.session.commit()

        rows = db.session.scalars(
            select(NhlOddsPartner).where(NhlOddsPartner.partner_id == 7)
        ).all()
        assert len(rows) == 1

    def test_nhl_odds_partner_upsert_overwrites_changed_field(self, db):
        """Merging a partner with a changed site_url overwrites the existing value."""
        db.session.add(NhlOddsPartner(partner_id=7, name="FanDuel",
                                      site_url="https://old.fanduel.com"))
        db.session.commit()

        db.session.merge(NhlOddsPartner(partner_id=7, name="FanDuel",
                                        site_url="https://new.fanduel.com"))
        db.session.commit()

        row = db.session.get(NhlOddsPartner, 7)
        assert row.site_url == "https://new.fanduel.com"


# ── _upsert_partners helper ───────────────────────────────────────────────────

class TestUpsertPartners:
    def test_upsert_partners_inserts_new_partners(self, db):
        """_upsert_partners() with 2 partner dicts inserts exactly 2 rows."""
        from services.scores import _upsert_partners

        _upsert_partners([_PARTNER_FANDUEL, _PARTNER_DRAFTKINGS])

        rows = db.session.scalars(select(NhlOddsPartner)).all()
        assert len(rows) == 2
        partner_ids = {r.partner_id for r in rows}
        assert partner_ids == {7, 9}

    def test_upsert_partners_stores_all_column_values(self, db):
        """_upsert_partners() persists every field from the partner dict."""
        from services.scores import _upsert_partners

        _upsert_partners([_PARTNER_FANDUEL])

        row = db.session.get(NhlOddsPartner, 7)
        assert row.country == "CA"
        assert row.name == "FanDuel"
        assert row.image_url == "https://assets.nhle.com/betting_partner/fanduel.svg"
        assert row.site_url == "https://fanduel.com"
        assert row.bg_color == "#0078ff"
        assert row.text_color == "#FFFFFF"
        assert row.accent_color == "#FFFFFF"

    def test_upsert_partners_no_duplicates_on_repeat_call(self, db):
        """Calling _upsert_partners() twice with the same data leaves exactly 2 rows."""
        from services.scores import _upsert_partners

        _upsert_partners([_PARTNER_FANDUEL, _PARTNER_DRAFTKINGS])
        _upsert_partners([_PARTNER_FANDUEL, _PARTNER_DRAFTKINGS])

        rows = db.session.scalars(select(NhlOddsPartner)).all()
        assert len(rows) == 2

    def test_upsert_partners_overwrites_changed_metadata(self, db):
        """_upsert_partners() overwrites a field that changed between calls."""
        from services.scores import _upsert_partners

        _upsert_partners([_PARTNER_FANDUEL])

        updated = dict(_PARTNER_FANDUEL, siteUrl="https://ca.fanduel.com")
        _upsert_partners([updated])

        row = db.session.get(NhlOddsPartner, 7)
        assert row.site_url == "https://ca.fanduel.com"

    def test_upsert_partners_empty_list_no_error(self, db):
        """_upsert_partners([]) raises no error and leaves the table empty."""
        from services.scores import _upsert_partners

        _upsert_partners([])  # must not raise

        rows = db.session.scalars(select(NhlOddsPartner)).all()
        assert rows == []


# ── refresh_scores integration ────────────────────────────────────────────────

class TestRefreshScoresPartnersIntegration:
    def test_refresh_scores_upserts_partners_when_key_present(self, db):
        """refresh_scores() upserts NhlOddsPartner rows when oddsPartners is in the response."""
        api_data = _make_score_now(partners=[_PARTNER_FANDUEL, _PARTNER_DRAFTKINGS])
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()

        rows = db.session.scalars(select(NhlOddsPartner)).all()
        assert len(rows) == 2

    def test_refresh_scores_handles_absent_odds_partners_key(self, db):
        """refresh_scores() does not raise when oddsPartners key is absent."""
        api_data = _make_score_now()  # no oddsPartners key
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()  # must not raise

        rows = db.session.scalars(select(NhlOddsPartner)).all()
        assert rows == []

    def test_refresh_scores_handles_empty_odds_partners_array(self, db):
        """refresh_scores() does not raise when oddsPartners is an empty list."""
        api_data = _make_score_now(partners=[])
        with patch("nhl_client.get_score_now", return_value=api_data):
            from services.scores import refresh_scores
            refresh_scores()  # must not raise

        rows = db.session.scalars(select(NhlOddsPartner)).all()
        assert rows == []
