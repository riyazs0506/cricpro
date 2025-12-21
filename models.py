# models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# ---------------------------------------------------------
# USER MODEL
# ---------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("player", "coach"), nullable=False)
    status = db.Column(db.Enum("pending", "approved"), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    player = db.relationship("Player", uselist=False, back_populates="user")
    coach = db.relationship("Coach", uselist=False, back_populates="user")


# ---------------------------------------------------------
# BATCH MODEL
# ---------------------------------------------------------
class Batch(db.Model):
    __tablename__ = "batches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)


# ---------------------------------------------------------
# PLAYER MODEL
# ---------------------------------------------------------
class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    dob = db.Column(db.Date)
    age = db.Column(db.Integer)
    batting_style = db.Column(db.String(50))
    bowling_style = db.Column(db.String(50))
    role_in_team = db.Column(db.String(50))
    wicket_keeper = db.Column(db.Boolean, default=False)
    bio = db.Column(db.Text)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))

    user = db.relationship("User", back_populates="player")
    batch = db.relationship("Batch")

    # relationship to statistics (one-to-one)
    playerstats = db.relationship("PlayerStats", uselist=False, back_populates="player")


# ---------------------------------------------------------
# COACH MODEL
# ---------------------------------------------------------
class Coach(db.Model):
    __tablename__ = "coaches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)

    user = db.relationship("User", back_populates="coach")


# ---------------------------------------------------------
# MATCH MODEL
# ---------------------------------------------------------
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

    status = db.Column(db.String(50), default="ongoing")

    scorer_coach_id = db.Column(db.Integer, db.ForeignKey("coaches.id"), nullable=True)
    scorer_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)

    # Toss fields
    toss_winner = db.Column(db.String(200))      # team_name or opponent_name
    toss_decision = db.Column(db.String(20))     # bat / bowl

    # innings logic
    current_innings = db.Column(db.Integer, default=1)      # 1 or 2
    batting_side = db.Column(db.String(20))                 # "team" or "opponent"

    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Report / quick score columns (added to DB) — keep defaults
    result = db.Column(db.String(255), nullable=True)

    team_runs = db.Column(db.Integer, default=0)
    team_wkts = db.Column(db.Integer, default=0)
    team_overs = db.Column(db.String(20), default="0.0")

    opp_runs = db.Column(db.Integer, default=0)
    opp_wkts = db.Column(db.Integer, default=0)
    opp_overs = db.Column(db.String(20), default="0.0")


# ---------------------------------------------------------
# SQUAD ASSIGNMENTS
# ---------------------------------------------------------
class MatchAssignment(db.Model):
    __tablename__ = "match_assignments"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))


# ---------------------------------------------------------
# TEMP OPPONENT PLAYERS
# ---------------------------------------------------------
class OpponentTempPlayer(db.Model):
    __tablename__ = "opponent_temp_players"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    name = db.Column(db.String(120))
    role = db.Column(db.String(50))


# ---------------------------------------------------------
# MANUAL SCORE ROWS
# ---------------------------------------------------------
# models.py (extract)

class ManualScore(db.Model):
    __tablename__ = "manual_scores"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)

    # Batting
    runs = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    is_out = db.Column(db.Boolean, default=False)

    # NEW OUT DETAIL FIELDS (Option A names)
    wicket_over = db.Column(db.Integer, nullable=True)        # over when out (e.g. 12)
    wicket_ball = db.Column(db.Integer, nullable=True)        # ball in over 0..5
    dismissal_type = db.Column(db.String(50), nullable=True) # bowled/caught/run_out/etc.

    # Bowling
    overs = db.Column(db.Float, default=0.0)
    runs_conceded = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)

    # Fielding
    catches = db.Column(db.Integer, default=0)
    drops = db.Column(db.Integer, default=0)
    saves = db.Column(db.Integer, default=0)

    is_opponent = db.Column(db.Boolean, default=False)

    # relationship helpers (optional)
    player = db.relationship("Player", backref="manual_scores", lazy=True)



# ---------------------------------------------------------
# WAGON WHEEL SHOTS
# ---------------------------------------------------------
class WagonWheel(db.Model):
    __tablename__ = "wagon_wheel"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    angle = db.Column(db.Integer)
    distance = db.Column(db.Integer)
    runs = db.Column(db.Integer)
    shot_type = db.Column(db.String(50))
    is_opponent = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------
# LIVE BALL BY BALL
# ---------------------------------------------------------
class LiveBall(db.Model):
    __tablename__ = "live_balls"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    over_no = db.Column(db.Integer)
    ball_no = db.Column(db.Integer)

    striker = db.Column(db.String(120))
    non_striker = db.Column(db.String(120))
    bowler = db.Column(db.String(120))

    runs = db.Column(db.Integer)
    extras = db.Column(db.String(20))
    wicket = db.Column(db.String(50))
    commentary = db.Column(db.Text)

    angle = db.Column(db.Integer)
    shot_type = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# PLAYER STATS MERGED AFTER APPROVAL
# ---------------------------------------------------------
class PlayerStats(db.Model):
    __tablename__ = "player_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))

    matches = db.Column(db.Integer, default=0)
    total_runs = db.Column(db.Integer, default=0)
    total_balls = db.Column(db.Integer, default=0)
    total_fours = db.Column(db.Integer, default=0)
    total_sixes = db.Column(db.Integer, default=0)

    # track outs for batting average calculation
    outs = db.Column(db.Integer, default=0)

    wickets = db.Column(db.Integer, default=0)
    overs_bowled = db.Column(db.Float, default=0.0)
    runs_conceded = db.Column(db.Integer, default=0)

    catches = db.Column(db.Integer, default=0)
    drops = db.Column(db.Integer, default=0)
    saves = db.Column(db.Integer, default=0)

    player = db.relationship("Player", back_populates="playerstats")



class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20))  # present / absent
    improvement_note = db.Column(db.Text)

    player = db.relationship("Player", backref="attendance_records")


class PlayerAvailability(db.Model):
    __tablename__ = "player_availability"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    status = db.Column(db.String(20))  # available / not_available / later
    created_at = db.Column(db.DateTime, default=db.func.now())

    player = db.relationship("Player")
    match = db.relationship("Match")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    message = db.Column(db.Text)
    category = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship("User")
