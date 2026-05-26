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


class LiveGame(db.Model):
    """Today's live-score game row, sourced from /v1/score/now.

    This model is the renamed successor of the legacy 'game' table.  Live odds
    (NhlOddsLine, OddsSnapshot) and model probabilities (ModelFair) reference
    live_game.game_id.  Will be superseded by Boxscore (#133) and DashboardGame
    (#134) in a future migration.
    """
    __tablename__ = 'live_game'

    game_id     = db.Column(db.Integer, primary_key=True)   # NHL gamePk
    start_est   = db.Column(db.DateTime, index=True, nullable=False)
    game_date   = db.Column(db.String(10))                               # API: gameDate e.g. "2025-01-15"
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
        return f'<LiveGame {self.away_code}@{self.home_code} {self.game_id}>'


class OddsSnapshot(db.Model):
    """One row per (live_game, fetch_time). Powers the 24h sparkline."""
    __tablename__ = 'odds_snapshot'

    id          = db.Column(db.Integer, primary_key=True)
    game_id     = db.Column(db.Integer, db.ForeignKey('live_game.game_id'), index=True)
    fetched_at  = db.Column(db.DateTime, index=True, nullable=False)
    book        = db.Column(db.String(32), nullable=False)   # 'consensus' for v1
    away_ml     = db.Column(db.Integer)      # American odds, e.g. +120
    home_ml     = db.Column(db.Integer)
    away_implied = db.Column(db.Float)       # percentage points (0–100)
    home_implied = db.Column(db.Float)       # percentage points (0–100)


class ModelFair(db.Model):
    """The dashboard's 'fair' probability — your own model output."""
    __tablename__ = 'model_fair'

    game_id     = db.Column(db.Integer, db.ForeignKey('live_game.game_id'), primary_key=True)
    away_fair   = db.Column(db.Float)   # percentage points (0–100)
    home_fair   = db.Column(db.Float)   # percentage points (0–100)
    computed_at = db.Column(db.DateTime)


class NhlOddsPartner(db.Model):
    """Betting partner registry seeded from the oddsPartners array in /v1/score/now."""
    __tablename__ = 'nhl_odds_partner'

    partner_id   = db.Column(db.Integer, primary_key=True)   # NHL's partnerId — not auto-generated
    country      = db.Column(db.String(2))
    name         = db.Column(db.String(64), nullable=False)
    image_url    = db.Column(db.String(255))
    site_url     = db.Column(db.String(512))
    bg_color     = db.Column(db.String(7))
    text_color   = db.Column(db.String(7))
    accent_color = db.Column(db.String(7))

    def __repr__(self):
        return f'<NhlOddsPartner {self.partner_id} {self.name!r}>'


class Game(db.Model):
    """Canonical historical game record from the NHL Stats REST API /game endpoint.

    Renamed from NhlHistoricalGame (Issue #131).  Sourced from
    GET https://api.nhle.com/stats/rest/en/game. One row per game;
    upserted by game_id so repeated backfill runs are idempotent.
    """
    __tablename__ = 'game'

    game_id                = db.Column(db.Integer, primary_key=True)        # API: id
    eastern_start_time     = db.Column(db.String(16))                       # API: easternStartTime
    game_date              = db.Column(db.String(10), index=True)            # API: gameDate
    game_number            = db.Column(db.Integer)                          # API: gameNumber
    game_schedule_state_id = db.Column(db.Integer)                          # API: gameScheduleStateId
    game_state_id          = db.Column(db.Integer)                          # API: gameStateId
    game_type              = db.Column(db.Integer)                          # API: gameType
    home_score             = db.Column(db.Integer)                          # API: homeScore
    home_team_id           = db.Column(db.Integer)                          # API: homeTeamId
    period                 = db.Column(db.Integer)                          # API: period
    season                 = db.Column(db.Integer, index=True)              # API: season
    visiting_score         = db.Column(db.Integer)                          # API: visitingScore
    visiting_team_id       = db.Column(db.Integer)                          # API: visitingTeamId

    def __repr__(self):
        return f'<Game {self.game_id} season={self.season}>'


class Boxscore(db.Model):
    """Live boxscore for one NHL game, sourced from /v1/gamecenter/{id}/boxscore.

    One row per game; upserted by game_id on each refresh so re-runs are
    idempotent.  Live fields (score, SOG, period, clock) are overwritten on
    every poll.  Sourced from Issue #133.
    """
    __tablename__ = 'boxscore'

    game_id        = db.Column(db.Integer, primary_key=True)      # API: id
    season_id      = db.Column(db.Integer)                        # API: season
    game_type      = db.Column(db.Integer)                        # API: gameType
    game_date      = db.Column(db.String(10), index=True)         # API: gameDate
    venue          = db.Column(db.String(120))                    # API: venue.default
    start_time_est = db.Column(db.DateTime)                       # API: startTimeUTC → ET
    away_name      = db.Column(db.String(64))                     # API: awayTeam.name.default
    home_name      = db.Column(db.String(64))                     # API: homeTeam.name.default
    away_score     = db.Column(db.Integer)                        # API: awayTeam.score
    home_score     = db.Column(db.Integer)                        # API: homeTeam.score
    away_sog       = db.Column(db.Integer)                        # API: awayTeam.sog
    home_sog       = db.Column(db.Integer)                        # API: homeTeam.sog
    period         = db.Column(db.String(8))                      # parsed from periodDescriptor
    clock          = db.Column(db.String(8))                      # API: clock.timeRemaining
    updated_at     = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Boxscore {self.game_id} {self.away_name}@{self.home_name}>'


class NhlOddsLine(db.Model):
    """Per-game, per-partner moneyline snapshot sourced from /v1/score/now odds arrays.

    One row is inserted per (live_game, partner) per poll cycle, subject to a 3-minute
    duplicate-suppression window. Rows are pruned after 30 days.
    """
    __tablename__ = 'nhl_odds_line'

    id         = db.Column(db.Integer, primary_key=True)
    game_id    = db.Column(db.Integer, db.ForeignKey('live_game.game_id'), nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('nhl_odds_partner.partner_id'), nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False, index=True)
    away_value = db.Column(db.String(16))
    home_value = db.Column(db.String(16))

    __table_args__ = (
        db.Index('ix_nhl_odds_line_game_partner_fetched', 'game_id', 'partner_id', 'fetched_at'),
    )

    def __repr__(self):
        return f'<NhlOddsLine game={self.game_id} partner={self.partner_id} {self.fetched_at}>'
