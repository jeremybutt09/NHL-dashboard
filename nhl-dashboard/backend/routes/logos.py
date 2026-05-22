"""Logos blueprint — GET /api/logos/<code> proxies NHL CDN SVGs."""

import httpx
from flask import Blueprint, Response

logos_bp = Blueprint("logos", __name__)

CDN_LOGO_URL = "https://assets.nhle.com/logos/nhl/svg/{code}_light.svg"

# Module-level in-memory cache: team code → raw SVG bytes.
_logo_cache: dict[str, bytes] = {}


@logos_bp.route("/api/logos/<code>")
def get_logo(code: str):
    """Fetch a team logo SVG from the NHL CDN and return it, caching the result.

    Args:
        code: Three-letter NHL team abbreviation (e.g. "TOR").

    Returns:
        SVG response with Content-Type image/svg+xml, or 404 on upstream failure.
    """
    upper_code = code.upper()

    if upper_code in _logo_cache:
        return Response(_logo_cache[upper_code], content_type="image/svg+xml")

    try:
        resp = httpx.get(CDN_LOGO_URL.format(code=upper_code), follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return Response("Logo not found", status=404)

    _logo_cache[upper_code] = resp.content
    return Response(resp.content, content_type="image/svg+xml")
