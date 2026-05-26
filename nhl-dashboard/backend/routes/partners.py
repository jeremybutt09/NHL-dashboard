from flask import Blueprint, jsonify, current_app
from sqlalchemy import select
from extensions import db
from models import NhlOddsPartner

partners_bp = Blueprint('partners', __name__)


@partners_bp.get('/api/partners')
def get_partners():
    """Return all sportsbook partners from nhl_odds_partner, ordered by partner_id.

    Returns:
        200 JSON list of partner objects with partner_id, name, and image_url.
    """
    try:
        rows = db.session.scalars(
            select(NhlOddsPartner).order_by(NhlOddsPartner.partner_id)
        ).all()
        return jsonify([
            {
                'partner_id': p.partner_id,
                'name': p.name,
                'image_url': p.image_url,
            }
            for p in rows
        ])
    except Exception as exc:
        current_app.logger.exception("Unhandled error in /api/partners")
        return jsonify({'error': 'internal_server_error', 'message': str(exc)}), 500
