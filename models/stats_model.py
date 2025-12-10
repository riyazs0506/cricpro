from .base_models import db


class PlayerStats(db.Model):
    __tablename__ = "player_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))

    matches = db.Column(db.Integer, default=0)
    total_runs = db.Column(db.Integer, default=0)
    total_balls = db.Column(db.Integer, default=0)
    total_fours = db.Column(db.Integer, default=0)
    total_sixes = db.Column(db.Integer, default=0)
    outs = db.Column(db.Integer, default=0)

    wickets = db.Column(db.Integer, default=0)
    overs_bowled = db.Column(db.Float, default=0.0)
    runs_conceded = db.Column(db.Integer, default=0)

    catches = db.Column(db.Integer, default=0)
    drops = db.Column(db.Integer, default=0)
    saves = db.Column(db.Integer, default=0)

    player = db.relationship("Player", back_populates="playerstats")


class BattingStats(db.Model):
    __tablename__ = "batting_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer)
    match_id = db.Column(db.Integer)
    runs = db.Column(db.Integer)
    balls = db.Column(db.Integer)
    fours = db.Column(db.Integer)
    sixes = db.Column(db.Integer)
    is_out = db.Column(db.Boolean)


class BowlingStats(db.Model):
    __tablename__ = "bowling_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer)
    match_id = db.Column(db.Integer)
    overs = db.Column(db.Float)
    wickets = db.Column(db.Integer)
    runs_conceded = db.Column(db.Integer)


class FieldingStats(db.Model):
    __tablename__ = "fielding_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer)
    match_id = db.Column(db.Integer)
    catches = db.Column(db.Integer)
    drops = db.Column(db.Integer)
    saves = db.Column(db.Integer)
