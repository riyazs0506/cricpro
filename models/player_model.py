from datetime import datetime
from flask_login import UserMixin
from .base_models import db


# -------------------------
# USER TABLE
# -------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20))
    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    player = db.relationship("Player", uselist=False, back_populates="user")
    coach = db.relationship("Coach", uselist=False, back_populates="user")


# -------------------------
# BATCH TABLE
# -------------------------
class Batch(db.Model):
    __tablename__ = "batches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)


# -------------------------
# PLAYER TABLE
# -------------------------
class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    dob = db.Column(db.Date)
    age = db.Column(db.Integer)

    batting_style = db.Column(db.String(50))
    bowling_style = db.Column(db.String(50))
    role_in_team = db.Column(db.String(50))
    bio = db.Column(db.Text)

    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))

    user = db.relationship("User", back_populates="player")
    batch = db.relationship("Batch")

    # ✔ FIXED: PlayerStats must be defined as string name
    playerstats = db.relationship(
        "PlayerStats", uselist=False, back_populates="player"
    )


# -------------------------
# COACH TABLE
# -------------------------
class Coach(db.Model):
    __tablename__ = "coaches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", back_populates="coach")


# -------------------------
# MATCH TABLE (UPDATED)
# -------------------------
class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    match_date = db.Column(db.Date)
    format = db.Column(db.String(50))
    venue = db.Column(db.String(200))
    scoring_mode = db.Column(db.String(50))

    team_name = db.Column(db.String(200))
    opponent_name = db.Column(db.String(200))

    # ✔ FIX: add toss fields so no more TypeError
    toss_winner = db.Column(db.String(200))     # team_name / opponent_name
    toss_decision = db.Column(db.String(50))    # bat / bowl

    status = db.Column(db.String(50), default="ongoing")

    scorer_coach_id = db.Column(db.Integer)
    scorer_player_id = db.Column(db.Integer)

    # summary
    team_runs = db.Column(db.Integer, default=0)
    team_wkts = db.Column(db.Integer, default=0)
    team_overs = db.Column(db.String(20), default="0.0")

    opp_runs = db.Column(db.Integer, default=0)
    opp_wkts = db.Column(db.Integer, default=0)
    opp_overs = db.Column(db.String(20), default="0.0")


# -------------------------
# MATCH ASSIGNMENT
# -------------------------
class MatchAssignment(db.Model):
    __tablename__ = "match_assignments"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer)
    player_id = db.Column(db.Integer)


# -------------------------
# OPPONENT PLAYER
# -------------------------
class OpponentTempPlayer(db.Model):
    __tablename__ = "opponent_temp_players"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer)
    name = db.Column(db.String(120))
    role = db.Column(db.String(50))


# -------------------------
# MANUAL SCORE TABLE
# -------------------------
class ManualScore(db.Model):
    __tablename__ = "manual_scores"

    id = db.Column(db.Integer, primary_key=True)

    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)

    # THIS WAS THE PROBLEM — missing ForeignKey
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)

    # Batting
    runs = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    is_out = db.Column(db.Boolean, default=False)

    dismissal_type = db.Column(db.String(50))   # NEW
    wicket_over = db.Column(db.String(10))      # NEW

    # Bowling
    overs = db.Column(db.Float, default=0.0)
    runs_conceded = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)

    # Fielding
    catches = db.Column(db.Integer, default=0)
    drops = db.Column(db.Integer, default=0)
    saves = db.Column(db.Integer, default=0)

    # Opponent flag
    is_opponent = db.Column(db.Boolean, default=False)  # NEW

    # RELATIONSHIPS
    player = db.relationship("Player", backref="manual_scores")
    match = db.relationship("Match", backref="manual_scores")

# -------------------------
# WAGON WHEEL
# -------------------------
class WagonWheel(db.Model):
    __tablename__ = "wagon_wheel"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer)
    player_id = db.Column(db.Integer)
    angle = db.Column(db.Integer)
    distance = db.Column(db.Integer)
    runs = db.Column(db.Integer)
    shot_type = db.Column(db.String(50))


# -------------------------
# LIVE BALL TABLE
# -------------------------
class LiveBall(db.Model):
    __tablename__ = "live_balls"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer)
    over_no = db.Column(db.Integer)
    ball_no = db.Column(db.Integer)
    striker = db.Column(db.String(120))
    non_striker = db.Column(db.String(120))
    bowler = db.Column(db.String(120))
    runs = db.Column(db.Integer)
    extras = db.Column(db.String(20))
    wicket = db.Column(db.String(20))
    commentary = db.Column(db.Text)

    