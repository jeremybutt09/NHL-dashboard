from datetime import datetime
from extensions import db


class Team(db.Model):
    __tablename__ = 'team'

    tri_code     = db.Column(db.String(3), primary_key=True)              # 'TOR'
    name         = db.Column(db.String(64))                               # 'Maple Leafs'
    team_id      = db.Column(db.Integer, unique=True)     # stats API id (populated by #112)
    franchise_id = db.Column(db.Integer)
    full_name    = db.Column(db.String(128))
    league_id    = db.Column(db.Integer)
    raw_tricode  = db.Column(db.String(8))

    def __repr__(self):
        return f'<Team {self.tri_code} team_id={self.team_id}>'


class Game(db.Model):
    __tablename__ = 'game'

    game_id     = db.Column(db.Integer, primary_key=True)   # NHL gamePk
    start_utc   = db.Column(db.DateTime, index=True, nullable=False)
    venue       = db.Column(db.String(120))
    away_code   = db.Column(db.String(3), db.ForeignKey('team.tri_code'))
    home_code   = db.Column(db.String(3), db.ForeignKey('team.tri_code'))
    status      = db.Column(db.String(16), nullable=False)   # 'scheduled' | 'live' | 'final'
    period      = db.Column(db.String(8),  nullable=True)
    clock       = db.Column(db.String(8),  nullable=True)
    away_score  = db.Column(db.Integer, default=0)
    home_score  = db.Column(db.Integer, default=0)
    away_sog    = db.Column(db.Integer, default=0)
    home_sog    = db.Column(db.Integer, default=0)
    updated_at  = db.Column(db.DateTime)

    away_team = db.relationship('Team', foreign_keys=[away_code])
    home_team = db.relationship('Team', foreign_keys=[home_code])

    def __repr__(self):
        return f'<Game {self.away_code}@{self.home_code} {self.game_id}>'


class OddsSnapshot(db.Model):
    """One row per (game, fetch_time). Powers the 24h sparkline."""
    __tablename__ = 'odds_snapshot'

    id          = db.Column(db.Integer, primary_key=True)
    game_id     = db.Column(db.Integer, db.ForeignKey('game.game_id'), index=True)
    fetched_at  = db.Column(db.DateTime, index=True, nullable=False)
    book        = db.Column(db.String(32), nullable=False)   # 'consensus' for v1
    away_ml     = db.Column(db.Integer)      # American odds, e.g. +120
    home_ml     = db.Column(db.Integer)
    away_implied = db.Column(db.Float)       # percentage points (0–100)
    home_implied = db.Column(db.Float)       # percentage points (0–100)


class ModelFair(db.Model):
    """The dashboard's 'fair' probability — your own model output."""
    __tablename__ = 'model_fair'

    game_id     = db.Column(db.Integer, db.ForeignKey('game.game_id'), primary_key=True)
    away_fair   = db.Column(db.Float)   # percentage points (0–100)
    home_fair   = db.Column(db.Float)   # percentage points (0–100)
    computed_at = db.Column(db.DateTime)
