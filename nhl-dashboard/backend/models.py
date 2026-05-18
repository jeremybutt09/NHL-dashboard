from datetime import datetime
from app import db


class Team(db.Model):
    """NHL team."""

    code = db.Column(db.String(3), primary_key=True)
    name = db.Column(db.String(64))


class Game(db.Model):
    """NHL game."""

    id = db.Column(db.Integer, primary_key=True)  # NHL gamePk
    start_utc = db.Column(db.DateTime, index=True)
    venue = db.Column(db.String(120))
    away_code = db.Column(db.String(3), db.ForeignKey('team.code'))
    home_code = db.Column(db.String(3), db.ForeignKey('team.code'))
    status = db.Column(db.String(16))  # 'scheduled' | 'live' | 'final'
    period = db.Column(db.String(8), nullable=True)
    clock = db.Column(db.String(8), nullable=True)
    away_score = db.Column(db.Integer, default=0)
    home_score = db.Column(db.Integer, default=0)
    away_sog = db.Column(db.Integer, default=0)
    home_sog = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime)


class OddsSnapshot(db.Model):
    """One row per (game, fetch_time). Powers the 24h sparkline."""

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), index=True)
    fetched_at = db.Column(db.DateTime, index=True)
    book = db.Column(db.String(32))  # 'consensus' for v1
    away_ml = db.Column(db.Integer)  # American odds, e.g. +120
    home_ml = db.Column(db.Integer)
    away_implied = db.Column(db.Float)  # 0-100
    home_implied = db.Column(db.Float)


class ModelFair(db.Model):
    """Dashboard fair probability from model output."""

    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), primary_key=True)
    away_fair = db.Column(db.Float)  # 0-100
    home_fair = db.Column(db.Float)
    computed_at = db.Column(db.DateTime)
