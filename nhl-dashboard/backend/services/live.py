"""
Live score service: updates period, clock, score, and SOG for in-progress games.
"""
from datetime import datetime, timezone

from extensions import db
from models import LiveGame


def refresh_live():
    """For each live Game, hit NHL boxscore and update score/clock/period/sog."""
    from sqlalchemy import select
    from nhl_client import get_boxscore

    live_games = db.session.scalars(
        select(LiveGame).where(LiveGame.status == 'live')
    ).all()

    now = datetime.now(timezone.utc)
    for g in live_games:
        try:
            data = get_boxscore(g.game_id)
            _update_from_boxscore(g, data, now)
        except Exception as e:
            print(f'[live] Error updating game {g.game_id}: {e}')

    if live_games:
        db.session.commit()


def _update_from_boxscore(g: LiveGame, data: dict, now: datetime):
    """Parse NHL boxscore response and write to the Game row."""
    game_state = data.get('gameState', '')
    if game_state in ('FINAL', 'OFF'):
        g.status = 'final'
    elif game_state in ('LIVE', 'CRIT'):
        g.status = 'live'

    # Period (periodDescriptor is None for FUT games)
    pd = data.get('periodDescriptor') or {}
    period_num  = pd.get('number', 1)
    period_type = pd.get('periodType', 'REG')
    if period_type == 'OT':
        g.period = 'OT'
    elif period_type == 'SO':
        g.period = 'SO'
    else:
        ordinals = {1: '1st', 2: '2nd', 3: '3rd'}
        g.period = ordinals.get(period_num, f'{period_num}th')

    # Clock
    clock_data = data.get('clock', {})
    g.clock = clock_data.get('timeRemaining', '20:00')

    # Scores
    away_info = data.get('awayTeam', {})
    home_info = data.get('homeTeam', {})
    g.away_score = away_info.get('score', g.away_score) or g.away_score
    g.home_score = home_info.get('score', g.home_score) or g.home_score
    g.away_sog   = away_info.get('sog',   g.away_sog)   or g.away_sog
    g.home_sog   = home_info.get('sog',   g.home_sog)   or g.home_sog

    g.updated_at = now
