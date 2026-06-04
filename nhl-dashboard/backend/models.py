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
    away_score             = db.Column(db.Integer)                          # API: visitingScore
    away_team_id           = db.Column(db.Integer)                          # API: visitingTeamId

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
    away_abbrev    = db.Column(db.String(8))                      # API: awayTeam.abbrev
    home_name      = db.Column(db.String(64))                     # API: homeTeam.name.default
    home_abbrev    = db.Column(db.String(8))                      # API: homeTeam.abbrev
    away_score     = db.Column(db.Integer)                        # API: awayTeam.score
    home_score     = db.Column(db.Integer)                        # API: homeTeam.score
    away_sog       = db.Column(db.Integer)                        # API: awayTeam.sog
    home_sog       = db.Column(db.Integer)                        # API: homeTeam.sog
    period         = db.Column(db.String(8))                      # parsed from periodDescriptor
    clock          = db.Column(db.String(8))                      # API: clock.timeRemaining
    game_state     = db.Column(db.String(8))                      # API: gameState ('FUT','PRE','LIVE','CRIT','FINAL','OFF')
    updated_at     = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Boxscore {self.game_id} {self.away_name}@{self.home_name}>'


class DimPlayer(db.Model):
    """Player biographical dimension sourced from GET /v1/roster/{team}/{season}.

    One row per NHL player; upserted by player_id so repeated roster pulls are
    idempotent. sweater_number is overwritten on each upsert — it changes between
    seasons. No FK constraints to other tables for MVP.
    """
    __tablename__ = 'dim_player'

    player_id        = db.Column(db.Integer, primary_key=True)          # API: id — not auto-generated
    first_name       = db.Column(db.String(64))                         # API: firstName.default
    last_name        = db.Column(db.String(64))                         # API: lastName.default
    sweater_number   = db.Column(db.Integer)                            # API: sweaterNumber — changes seasonally
    position         = db.Column(db.String(2))                          # API: positionCode (C/L/R/D/G)
    shoots_catches   = db.Column(db.String(1))                          # API: shootsCatches (L/R)
    height_in_inches = db.Column(db.Integer)                            # API: heightInInches
    weight_in_pounds = db.Column(db.Integer)                            # API: weightInPounds
    birth_date       = db.Column(db.String(10))                         # API: birthDate (YYYY-MM-DD)
    birth_country    = db.Column(db.String(3))                          # API: birthCountry (3-letter code)
    headshot_url     = db.Column(db.String(255))                        # API: headshot (CDN URL)
    updated_at       = db.Column(db.DateTime)                           # Eastern timestamp of last upsert

    def __repr__(self):
        return f'<DimPlayer {self.player_id} {self.first_name} {self.last_name}>'


class FactSkaterStats(db.Model):
    """Per-game skater statistics fact table sourced from playerByGameStats in
    GET /v1/gamecenter/{id}/boxscore.

    One row per (game_id, player_id) for every forward and defenseman in the
    game.  Upserted on each refresh so live-game stats stay current without
    duplicating rows.  FKs to boxscore (game context) and dim_player (bio).
    """
    __tablename__ = 'fact_skater_stats'

    game_id         = db.Column(db.Integer, db.ForeignKey('boxscore.game_id'), primary_key=True, nullable=False)
    player_id       = db.Column(db.Integer, db.ForeignKey('dim_player.player_id'), primary_key=True, nullable=False)
    team_id         = db.Column(db.Integer, nullable=False)                        # NHL numeric team ID
    side            = db.Column(db.String(4), nullable=False)                      # 'away' | 'home'
    position_group  = db.Column(db.String(10), nullable=False)                     # 'forwards' | 'defense'
    position        = db.Column(db.String(2))                                      # C / L / R / D
    goals           = db.Column(db.Integer)                                        # API: goals
    assists         = db.Column(db.Integer)                                        # API: assists
    points          = db.Column(db.Integer)                                        # API: points
    plus_minus      = db.Column(db.Integer)                                        # API: plusMinus
    pim             = db.Column(db.Integer)                                        # API: pim
    toi             = db.Column(db.String(8))                                      # API: toi (MM:SS)
    hits            = db.Column(db.Integer)                                        # API: hits
    blocked_shots   = db.Column(db.Integer)                                        # API: blockedShots
    pp_goals        = db.Column(db.Integer)                                        # API: powerPlayGoals
    pp_points       = db.Column(db.Integer)                                        # API: powerPlayPoints
    sh_goals        = db.Column(db.Integer)                                        # API: shorthandedGoals
    faceoff_win_pct = db.Column(db.Float)                                          # API: faceoffWinningPctg (NULL for D)
    giveaways       = db.Column(db.Integer)                                        # API: giveaways
    takeaways       = db.Column(db.Integer)                                        # API: takeaways
    shifts          = db.Column(db.Integer)                                        # API: shifts

    def __repr__(self):
        return f'<FactSkaterStats game={self.game_id} player={self.player_id}>'


class FactGoalieStats(db.Model):
    """Per-game goalie statistics fact table sourced from playerByGameStats.*.goalies
    in GET /v1/gamecenter/{id}/boxscore.

    One row per (game_id, player_id) for every goalie dressed in the game.
    saves and shots_against are stored as separate integers (not the
    'saves/shots' composite string the API returns in saveShotsAgainst).
    decision is NULL for backup goalies who did not receive a decision.
    FKs to boxscore (game context) and dim_player (bio).
    """
    __tablename__ = 'fact_goalie_stats'

    game_id          = db.Column(db.Integer, db.ForeignKey('boxscore.game_id'), primary_key=True, nullable=False)
    player_id        = db.Column(db.Integer, db.ForeignKey('dim_player.player_id'), primary_key=True, nullable=False)
    team_id          = db.Column(db.Integer, nullable=False)                        # NHL numeric team ID
    side             = db.Column(db.String(4), nullable=False)                      # 'away' | 'home'
    starter          = db.Column(db.Integer)                                        # API: starter (1=starter, 0=backup)
    toi              = db.Column(db.String(8))                                      # API: toi (MM:SS)
    goals_against    = db.Column(db.Integer)                                        # API: goalsAgainst
    saves            = db.Column(db.Integer)                                        # parsed from saveShotsAgainst 'saves/shots'
    shots_against    = db.Column(db.Integer)                                        # parsed from saveShotsAgainst 'saves/shots'
    save_pct         = db.Column(db.Float)                                          # API: savePctg (0.0–1.0)
    es_shots_against = db.Column(db.Integer)                                        # API: evenStrengthShotsAgainst
    pp_shots_against = db.Column(db.Integer)                                        # API: powerPlayShotsAgainst
    sh_shots_against = db.Column(db.Integer)                                        # API: shorthandedShotsAgainst
    pim              = db.Column(db.Integer)                                        # API: pim
    decision         = db.Column(db.String(4))                                      # API: decision (W/L/OTL or NULL)

    def __repr__(self):
        return f'<FactGoalieStats game={self.game_id} player={self.player_id} decision={self.decision!r}>'


class NhlOddsLine(db.Model):
    """Per-game, per-partner moneyline snapshot sourced from /v1/score/now odds arrays.

    One row is inserted per (game, partner) per poll cycle, subject to a 3-minute
    duplicate-suppression window. Rows are pruned after 30 days.
    """
    __tablename__ = 'nhl_odds_line'

    id         = db.Column(db.Integer, primary_key=True)
    game_id    = db.Column(db.Integer, nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('nhl_odds_partner.partner_id'), nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False, index=True)
    away_value = db.Column(db.String(16))
    home_value = db.Column(db.String(16))

    __table_args__ = (
        db.Index('ix_nhl_odds_line_game_partner_fetched', 'game_id', 'partner_id', 'fetched_at'),
    )

    def __repr__(self):
        return f'<NhlOddsLine game={self.game_id} partner={self.partner_id} {self.fetched_at}>'
