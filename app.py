# app.py (FULL updated)
import io
import os
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, current_app
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)

# config (use the config.py you added)
from config import DevelopmentConfig

# models & utils & forms
from models import (
    db, User, Player, Coach, Batch, Match,
    MatchAssignment, OpponentTempPlayer,
    ManualScore, WagonWheel, LiveBall,
    PlayerStats
)
from utils import (
    calculate_age, assign_batch_by_age,
    merge_manual_into_player_stats, get_all_allowed_players
)
from forms import (
    RegisterForm, LoginForm, PlayerProfileForm,
    MatchCreateForm, ManualMatchForm
)
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from flask import request, jsonify
from models import db, ManualScore, Match, Player
from sqlalchemy import and_

# --------------------------------------------------------
# APP CONFIG
# --------------------------------------------------------
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
# allow override via env
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI",
    app.config["SQLALCHEMY_DATABASE_URI"]
)
app.config['SECRET_KEY'] = "THIS_IS_A_STRONG_SECRET_KEY_12345"  
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400   # session lasts 24 hours

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# Provide datetime in templates
@app.context_processor
def inject_globals():
    return {
        "datetime": datetime,
        "current_year": datetime.now(timezone.utc).year
    }



# --------------------------------------------------------
# INITIAL CREATE TABLES (safe)
# --------------------------------------------------------
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        # Do not crash application startup: show message and continue.
        # Common local dev issue: MySQL auth/cert problems. Surface it clearly.
        print("Warning: create_all() failed:", e)


# --------------------------------------------------------
# LOGIN MANAGER
# --------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# --------------------------------------------------------
# HOME + AUTH
# --------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():

        existing = User.query.filter(
            (User.username == form.username.data) |
            (User.email == form.email.data)
        ).first()

        if existing:
            flash("Username or Email already exists.", "danger")
            return redirect(url_for("register"))

        u = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data
        )

        # Players must be approved; coaches auto-approved
        u.status = "approved" if u.role == "coach" else "pending"

        db.session.add(u)
        db.session.commit()

        if u.role == "player":
            db.session.add(Player(user_id=u.id))
        else:
            db.session.add(Coach(user_id=u.id))

        db.session.commit()

        flash("Registration successful! Wait for approval (if player).", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter(
            (User.username == form.username.data) |
            (User.email == form.username.data)
        ).first()

        if not user or not check_password_hash(user.password_hash, form.password.data):
            flash("Invalid login details", "danger")
            return redirect(url_for("login"))

        if user.role == "player" and user.status != "approved":
            flash("Your account is pending approval.", "warning")
            return redirect(url_for("login"))

        login_user(user)
        flash("Logged in!", "success")

        if user.role == "coach":
            return redirect(url_for("dashboard_coach"))
        else:
            return redirect(url_for("dashboard_player"))

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


# --------------------------------------------------------
# DASHBOARDS
# --------------------------------------------------------
@app.route("/coach/dashboard")
@login_required
def dashboard_coach():
    if current_user.role != "coach":
        return redirect(url_for("home"))

    coach = Coach.query.filter_by(user_id=current_user.id).first()

    pending_players = Player.query.join(User).filter(User.status == "pending").all()

    today = datetime.utcnow().date()
    matches_today = Match.query.filter(db.func.date(Match.match_date) == today).all()

    # SHOW MATCHES WAITING FOR THIS COACH ONLY
    matches_pending = Match.query.filter(
        Match.status == "pending_approval",
        Match.scorer_coach_id == coach.id
    ).all()

    return render_template(
        "dashboard_coach.html",
        coach=coach,
        pending_players=pending_players,
        matches_today=matches_today,
        matches_pending=matches_pending
    )




@app.route("/player/dashboard")
@login_required
def dashboard_player():
    if current_user.role != "player":
        return redirect(url_for("home"))

    p = Player.query.filter_by(user_id=current_user.id).first()
    upcoming = Match.query.order_by(Match.match_date.asc()).all()

    return render_template(
        "dashboard_player.html",
        player=p,
        upcoming_matches=upcoming
    )
# --------------------------------------------------------
# PLAYER PROFILE (VIEW ONLY)
# --------------------------------------------------------
@app.route("/player/profile")
@login_required
def player_profile():
    if current_user.role != "player":
        return redirect(url_for("home"))

    p = Player.query.filter_by(user_id=current_user.id).first()
    return render_template("player_profile.html", player=p)


# --------------------------------------------------------
# PLAYER MANAGEMENT
# --------------------------------------------------------
@app.route("/coach/players")
@login_required
def coach_player_list():
    if current_user.role != "coach":
        return redirect(url_for("home"))

    players = Player.query.join(User).filter(User.status == "approved").all()
    return render_template("coach_player_list.html", players=players)


@app.route("/coach/player/<int:id>")
@login_required
def coach_view_player(id):
    player = Player.query.get_or_404(id)
    return render_template("coach_player_profile.html", player=player)


@app.route("/coach/player/<int:id>/approve")
@login_required
def approve_player(id):
    if current_user.role != "coach":
        return redirect(url_for("home"))

    p = Player.query.get_or_404(id)
    u = User.query.get(p.user_id)

    u.status = "approved"

    if p.dob:
        p.age = calculate_age(p.dob)
        batch = assign_batch_by_age(p.age)
        if batch:
            p.batch_id = batch.id

    db.session.commit()

    flash("Player approved!", "success")
    return redirect(url_for("dashboard_coach"))


# --------------------------------------------------------
# PLAYER PROFILE EDIT
# --------------------------------------------------------
@app.route("/player/profile/edit", methods=["GET", "POST"])
@login_required
def player_edit_profile():
    if current_user.role != "player":
        return redirect(url_for("home"))

    p = Player.query.filter_by(user_id=current_user.id).first()
    form = PlayerProfileForm(obj=p)

    if form.validate_on_submit():

        p.dob = form.dob.data
        p.batting_style = form.batting_style.data
        p.bowling_style = form.bowling_style.data
        p.role_in_team = form.role_in_team.data
        p.bio = form.bio.data

        if p.dob:
            p.age = calculate_age(p.dob)
            batch = assign_batch_by_age(p.age)
            if batch:
                p.batch_id = batch.id

        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("dashboard_player"))

    return render_template("player_edit_profile.html", form=form, player=p)


# --------------------------------------------------------
# MATCH CREATION (NORMAL)
# --------------------------------------------------------
@app.route("/coach/match/create", methods=["GET", "POST"])
@login_required
def coach_create_match():

    if current_user.role != "coach":
        return redirect(url_for("home"))

    form = MatchCreateForm()
    coach = Coach.query.filter_by(user_id=current_user.id).first()

    # scorer players
    approved_players = Player.query.join(User).filter(User.status == "approved").all()
    form.scorer_player.choices = [(p.id, p.user.username) for p in approved_players]

    # dynamic toss options (use placeholders; client-side JS should update after typing team/opponent)
    form.toss_winner.choices = [
        (form.team_name.data or "Our Team", form.team_name.data or "Our Team"),
        (form.opponent_name.data or "Opponent", form.opponent_name.data or "Opponent")
    ]

    if form.validate_on_submit():

        m = Match(
            title=form.title.data,
            match_date=form.match_date.data,
            format=form.match_type.data,
            venue=form.venue.data,
            scoring_mode=form.scoring_mode.data,
            team_name=form.team_name.data,
            opponent_name=form.opponent_name.data,
            status="ongoing"
        )

        # ------- TOSS -------
        m.toss_winner = form.toss_winner.data
        m.toss_decision = form.toss_decision.data

        if m.toss_winner == m.team_name:
            m.batting_side = "our" if m.toss_decision == "bat" else "opponent"
        else:
            m.batting_side = "opponent" if m.toss_decision == "bat" else "our"

        # scorer
        if form.scorer_type.data == "coach":
            m.scorer_coach_id = coach.id
        else:
            # if scorer_player is not provided or 0 -> None
            m.scorer_player_id = form.scorer_player.data if form.scorer_player.data else None

        db.session.add(m)
        db.session.commit()

        flash("Match Created!", "success")
        return redirect(url_for("match_detail", match_id=m.id))

    return render_template("match_create.html", form=form)


# --------------------------------------------------------
# MANUAL MATCH CREATION (WITH TOSS)
# --------------------------------------------------------
@app.route("/match/manual/create", methods=["GET", "POST"])
@login_required
def manual_match_create():
    if current_user.role != "coach":
        flash("Only coach can create matches", "danger")
        return redirect(url_for("home"))

    form = ManualMatchForm()

    # Load list of approved players for scorer selection
    players = Player.query.join(User).filter(User.status == "approved").all()
    # Ensure there is always at least the placeholder
    choices = [(0, "--- Select Player ---")] + [(p.id, p.user.username) for p in players]
    form.scorer_player.choices = choices

    # Build dynamic toss options from submitted POST values first, otherwise placeholders
    team_default = form.team_name.data or request.form.get("team_name") or "Team A"
    opp_default = form.opponent_name.data or request.form.get("opponent_name") or "Team B"
    form.toss_winner.choices = [(team_default, team_default), (opp_default, opp_default)]

    if form.validate_on_submit():
        coach = Coach.query.filter_by(user_id=current_user.id).first()

        match = Match(
            title=form.title.data,
            match_date=form.match_date.data,
            format=form.match_type.data,
            venue=form.venue.data,
            scoring_mode=form.scoring_mode.data,
            team_name=form.team_name.data,
            opponent_name=form.opponent_name.data,
            toss_winner=form.toss_winner.data,
            toss_decision=form.toss_decision.data,
            status="ongoing",
            scorer_coach_id=coach.id if form.scorer_type.data == "coach" else None,
            scorer_player_id=form.scorer_player.data if (form.scorer_type.data == "player" and form.scorer_player.data != 0) else None
        )

        # Decide batting side
        if match.toss_winner == match.team_name:
            match.batting_side = "team" if match.toss_decision == "bat" else "opponent"
        else:
            match.batting_side = "opponent" if match.toss_decision == "bat" else "team"

        db.session.add(match)
        db.session.commit()

        flash("Manual Match Created Successfully!", "success")
        return redirect(url_for("manual_scoring", match_id=match.id))

    # show form
    return render_template("match_manual_create.html", form=form)


# --------------------------------------------------------
# MATCH LIST + DETAIL
# --------------------------------------------------------
@app.route("/matches")
@login_required
def match_list():
    matches = Match.query.order_by(Match.match_date.asc()).all()
    return render_template("match_list.html", matches=matches)

@app.route("/coach/player/<int:id>/stats")
@login_required
def coach_player_stats(id):
    if current_user.role != "coach":
        return redirect(url_for("home"))

    player = Player.query.get_or_404(id)
    stats = PlayerStats.query.filter_by(player_id=id).first()

    return render_template("coach_player_stats.html", player=player, stats=stats)


@app.route("/match/<int:match_id>")
@login_required
def match_detail(match_id):
    m = Match.query.get_or_404(match_id)

    def can_score(match):
        if current_user.role == "coach":
            c = Coach.query.filter_by(user_id=current_user.id).first()
            return match.scorer_coach_id == c.id
        if current_user.role == "player":
            p = Player.query.filter_by(user_id=current_user.id).first()
            return match.scorer_player_id == p.id
        return False

    playing = MatchAssignment.query.filter_by(match_id=m.id).all()
    opponents = OpponentTempPlayer.query.filter_by(match_id=m.id).all()

    return render_template(
        "match_detail.html",
        match=m,
        can_score=can_score(m),
        playing_count=len(playing),
        opponent_count=len(opponents)
    )


# --------------------------------------------------------
# PLAYER SELECTION (SQUAD)
# --------------------------------------------------------
@app.route("/match/<int:match_id>/select_players", methods=["GET", "POST"])
@login_required
def select_players(match_id):
    m = Match.query.get_or_404(match_id)

    if current_user.role != "coach":
        flash("Not allowed", "danger")
        return redirect(url_for("match_detail", match_id=m.id))

    system_players = Player.query.join(User).filter(User.status == "approved").all()
    existing = MatchAssignment.query.filter_by(match_id=m.id).all()
    selected_ids = [r.player_id for r in existing]
    opp_players = OpponentTempPlayer.query.filter_by(match_id=m.id).all()

    if request.method == "POST":
        payload = request.get_json() or {}

        selected = payload.get("selected_players", [])
        opponents = payload.get("opponents", [])

        if len(selected) < 11:
            return jsonify({"error": "Select at least 11 players"}), 400

        MatchAssignment.query.filter_by(match_id=m.id).delete()
        OpponentTempPlayer.query.filter_by(match_id=m.id).delete()
        db.session.flush()

        for pid in selected:
            db.session.add(MatchAssignment(match_id=m.id, player_id=int(pid)))

        for opp in opponents:
            if opp.get("name"):
                db.session.add(
                    OpponentTempPlayer(
                        match_id=m.id,
                        name=opp["name"],
                        role=opp.get("role", "")
                    )
                )

        db.session.commit()
        return jsonify({"status": "ok"}), 200

    selected_players = Player.query.filter(Player.id.in_(selected_ids)).all() if selected_ids else []

    return render_template(
        "select_players.html",
        match=m,
        system_players=system_players,
        selected_players=selected_players,
        opponent_players=opp_players
    )


# --------------------------------------------------------
# MANUAL SCORING PAGE
# --------------------------------------------------------
@app.route("/match/<int:match_id>/manual")
@login_required
def manual_scoring(match_id):

    m = Match.query.get_or_404(match_id)

    allowed = False
    if current_user.role == "coach":
        c = Coach.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_coach_id == c.id)
    elif current_user.role == "player":
        p = Player.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_player_id == p.id)

    if not allowed:
        flash("You are not the assigned scorer.", "danger")
        return redirect(url_for("match_detail", match_id=m.id))

    # players: if squad assigned use that otherwise fallback to all approved players
    squad_assignments = MatchAssignment.query.filter_by(match_id=m.id).all()
    if squad_assignments:
        squad_ids = [a.player_id for a in squad_assignments]
        players = Player.query.filter(Player.id.in_(squad_ids)).all()
    else:
        players = Player.query.join(User).filter(User.status == "approved").all()

    opponents = OpponentTempPlayer.query.filter_by(match_id=m.id).all()

    return render_template(
        "manual_scoring.html",
        match=m,
        players=players,
        opponents=opponents
    )

# --------------------------------------------------------
# API: MANUAL SCORE SAVE
# --------------------------------------------------------
# --------------------------------------------------------
# API: MANUAL SCORE SAVE (FINAL FIXED VERSION)
# --------------------------------------------------------
@app.route("/api/match/<int:match_id>/manual_save", methods=["POST"])
@login_required
def api_manual_save(match_id):

    m = Match.query.get_or_404(match_id)

    # scorer permission check
    allowed = False
    if current_user.role == "coach":
        c = Coach.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_coach_id == c.id)
    elif current_user.role == "player":
        p = Player.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_player_id == p.id)

    if not allowed:
        return jsonify({"error": "not_allowed"}), 403

    data = request.get_json() or {}

    try:
        # clear previous manual data
        ManualScore.query.filter_by(match_id=match_id).delete()
        WagonWheel.query.filter_by(match_id=match_id).delete()
        db.session.flush()

        # ---------------- BATTING ----------------
        for b in data.get("batting", []):
            db.session.add(ManualScore(
                match_id=match_id,
                player_id=b.get("player_id"),
                runs=b.get("runs", 0),
                balls_faced=b.get("balls", 0),
                fours=b.get("fours", 0),
                sixes=b.get("sixes", 0),
                is_out=bool(b.get("is_out", 0)),
                wicket_over=b.get("wicket_over"),
                wicket_ball=b.get("wicket_ball"),
                dismissal_type=b.get("dismissal_type"),
                is_opponent=False
            ))

        # ---------------- BOWLING ----------------
        for bo in data.get("bowling", []):
            db.session.add(ManualScore(
                match_id=match_id,
                player_id=bo.get("player_id"),
                overs=bo.get("overs", 0.0),
                runs_conceded=bo.get("runs_conceded", 0),
                wickets=bo.get("wickets", 0),
                is_opponent=False
            ))

        # ---------------- FIELDING ----------------
        for f in data.get("fielding", []):
            db.session.add(ManualScore(
                match_id=match_id,
                player_id=f.get("player_id"),
                catches=f.get("catches", 0),
                drops=f.get("drops", 0),
                saves=f.get("saves", 0),
                is_opponent=False
            ))

        # ---------------- WAGON WHEEL ----------------
        for w in data.get("wagon", []):
            db.session.add(WagonWheel(
                match_id=match_id,
                player_id=w.get("player_id"),
                angle=w.get("angle"),
                distance=w.get("distance", 0),
                runs=w.get("runs", 0),
                shot_type=w.get("shot_type"),
                is_opponent=False
            ))

        # ---------------- OPPONENT SUMMARY ----------------
        op = data.get("opponent_simple")
        if op:
            db.session.add(ManualScore(
                match_id=match_id,
                player_id=None,
                runs=op.get("runs", 0),
                wickets=op.get("wickets", 0),
                overs=op.get("overs", 0.0),
                is_opponent=True
            ))

            m.opp_runs = int(op.get("runs", 0))
            m.opp_wkts = int(op.get("wickets", 0))
            m.opp_overs = str(op.get("overs", "0.0"))

        # ---------------- TEAM SUMMARY ----------------
        ts = data.get("team_summary")
        if ts:
            m.team_runs = int(ts.get("runs", 0))
            m.team_wkts = int(ts.get("wkts", 0))
            m.team_overs = str(ts.get("overs", "0.0"))
            m.result = ts.get("result")

        # mark as pending approval
        m.status = "pending_approval"

        db.session.commit()
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

 
# --------------------------------------------------------
# LIVE SCORING PANEL + BALL INSERT
# --------------------------------------------------------
@app.route("/match/<int:match_id>/panel")
@login_required
def scoring_panel(match_id):

    m = Match.query.get_or_404(match_id)

    allowed = False
    if current_user.role == "coach":
        c = Coach.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_coach_id == c.id)
    elif current_user.role == "player":
        p = Player.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_player_id == p.id)

    if not allowed:
        flash("Not authorized.", "danger")
        return redirect(url_for("match_detail", match_id=match_id))

    last = LiveBall.query.filter_by(match_id=match_id).order_by(LiveBall.id.desc()).first()
    next_over, next_ball = (1, 1)

    if last:
        if last.ball_no == 6:
            next_over = last.over_no + 1
            next_ball = 1
        else:
            next_over = last.over_no
            next_ball = last.ball_no + 1

    squad_ids = [a.player_id for a in MatchAssignment.query.filter_by(match_id=m.id)]
    players = Player.query.filter(Player.id.in_(squad_ids)).all() if squad_ids else \
        Player.query.join(User).filter(User.status == "approved").all()

    opponents = OpponentTempPlayer.query.filter_by(match_id=m.id).all()

    return render_template(
        "live_score_admin.html",
        match=m,
        players=players,
        opponents=opponents,
        next_over=next_over,
        next_ball=next_ball
    )


@app.route("/api/live/<int:match_id>/add", methods=["POST"])
@login_required
def api_live_add(match_id):

    m = Match.query.get_or_404(match_id)

    allowed = False
    if current_user.role == "coach":
        c = Coach.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_coach_id == c.id)
    elif current_user.role == "player":
        p = Player.query.filter_by(user_id=current_user.id).first()
        allowed = (m.scorer_player_id == p.id)

    if not allowed:
        return jsonify({"error": "not_allowed"}), 403

    data = request.get_json() or {}

    try:
        lb = LiveBall(
            match_id=match_id,
            over_no=int(data.get("over_no", 1)),
            ball_no=int(data.get("ball_no", 1)),
            striker=data.get("striker"),
            non_striker=data.get("non_striker"),
            bowler=data.get("bowler"),
            runs=int(data.get("runs", 0)),
            extras=data.get("extras", "none"),
            wicket=data.get("wicket", "none"),
            commentary=data.get("commentary", ""),
            angle=data.get("angle"),
            shot_type=data.get("shot_type")
        )
        db.session.add(lb)
        db.session.commit()

        return jsonify({"status": "ok"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------------
# START + END INNINGS
# --------------------------------------------------------
@app.route("/match/<int:match_id>/start_innings", methods=["POST"])
@login_required
def start_innings(match_id):
    m = Match.query.get_or_404(match_id)

    if current_user.role != "coach":
        flash("Only coach can start innings.", "danger")
        return redirect(url_for("match_detail", match_id=match_id))

    batting_side = request.form.get("batting_side")  # expected "team" or "opponent"

    if m.current_innings not in [1, 2]:
        m.current_innings = 1
    else:
        # advance innings if ending/starting next
        m.current_innings = min(2, m.current_innings + 1)

    if batting_side:
        m.batting_side = batting_side

    m.started_at = datetime.utcnow()
    db.session.commit()

    flash(f"Innings {m.current_innings} started!", "success")
    return redirect(url_for("match_detail", match_id=match_id))


@app.route("/match/<int:match_id>/end_innings", methods=["POST"])
@login_required
def end_innings(match_id):
    m = Match.query.get_or_404(match_id)

    if current_user.role != "coach":
        flash("Not allowed.", "danger")
        return redirect(url_for("match_detail", match_id=match_id))

    m.completed_at = datetime.utcnow()
    db.session.commit()

    flash(f"Innings {m.current_innings} ended.", "success")
    return redirect(url_for("match_detail", match_id=match_id))


# --------------------------------------------------------
# VIEW LIVE & HISTORY
# --------------------------------------------------------
@app.route("/match/<int:match_id>/live")
def live_score_view(match_id):
    m = Match.query.get_or_404(match_id)
    return render_template("live_score_view.html", match=m)


@app.route("/match/<int:match_id>/history")
def ball_history(match_id):
    m = Match.query.get_or_404(match_id)
    balls = LiveBall.query.filter_by(match_id=match_id).order_by(LiveBall.id.asc()).all()
    return render_template("ball_history.html", match=m, balls=balls)


# --------------------------------------------------------
# APPROVE MATCH (MERGE STATS)
# --------------------------------------------------------
@app.route("/coach/match/<int:match_id>/approve_match", methods=["POST"])
@login_required
def coach_approve_match(match_id):
    if current_user.role != "coach":
        flash("Not allowed.", "danger"); return redirect(url_for("home"))
    m = Match.query.get_or_404(match_id)
    try:
        merge_manual_into_player_stats(match_id)
        OpponentTempPlayer.query.filter_by(match_id=match_id).delete()
        m.status = "completed"
        db.session.commit()
        flash("Match approved and stats updated!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Approval failed: {e}", "danger")
    return redirect(url_for("dashboard_coach"))



@app.route("/match/<int:match_id>/report")
@login_required
def match_report_pdf(match_id):
    """
    Generate a professional-style PDF match report (in-memory) and return as attachment.
    Uses simple heuristics to produce coach suggestions.
    """
    from sqlalchemy import func

    m = Match.query.get_or_404(match_id)

    # fetch manual scoring rows (exclude opponent summary rows for player-level stats)
    manual_rows = ManualScore.query.filter_by(match_id=match_id, is_opponent=False).all()

    # Build per-player aggregates from manual_rows
    per = {}
    for r in manual_rows:
        pid = r.player_id
        if not pid:
            continue
        if pid not in per:
            per[pid] = {
                "player": r.player,
                "runs": 0,
                "balls": 0,
                "outs": 0,
                "fours": 0,
                "sixes": 0,
                "wickets": 0,
                "overs": 0.0,
                "runs_conceded": 0,
                "catches": 0
            }
        rec = per[pid]
        rec["runs"] += (r.runs or 0)
        rec["balls"] += (r.balls_faced or 0)
        if r.is_out:
            rec["outs"] += 1
        rec["fours"] += (r.fours or 0)
        rec["sixes"] += (r.sixes or 0)
        rec["wickets"] += (r.wickets or 0)
        rec["overs"] += float(r.overs or 0.0)
        rec["runs_conceded"] += (r.runs_conceded or 0)
        rec["catches"] += (r.catches or 0)

    # Top performers (simple picks)
    def top_batting():
        best = None
        for pid, rec in per.items():
            if best is None or rec["runs"] > per[best]["runs"]:
                best = pid
        return per[best] if best else None

    def top_bowler():
        best = None
        for pid, rec in per.items():
            if best is None or rec["wickets"] > per[best]["wickets"]:
                best = pid
        return per[best] if best else None

    def top_fielder():
        best = None
        for pid, rec in per.items():
            if best is None or rec["catches"] > per[best]["catches"]:
                best = pid
        return per[best] if best else None

    batter = top_batting()
    bowler = top_bowler()
    fielder = top_fielder()

    # match-level quick numbers (use match columns if present, otherwise compute)
    team_runs = getattr(m, "team_runs", None)
    if team_runs is None:
        # compute from manual rows marked is_opponent==False batting rows
        team_rows = ManualScore.query.filter_by(match_id=match_id, is_opponent=False).all()
        team_runs = sum([r.runs or 0 for r in team_rows])

    opp = getattr(m, "opp_runs", None)
    if opp is None:
        opp_simple = ManualScore.query.filter_by(match_id=match_id, is_opponent=True).first()
        opp = opp_simple.runs if opp_simple else 0

    # Build a BytesIO PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Header
    story.append(Paragraph(f"{m.title}", styles["Title"]))
    story.append(Paragraph(f"{m.team_name} vs {m.opponent_name} — {m.match_date}", styles["Normal"]))
    story.append(Spacer(1, 8))

    # Overview table (professional-ish)
    overview_data = [
        ["Team", "Runs", "Wkts", "Overs"],
        [m.team_name, str(getattr(m, "team_runs", team_runs) or 0), str(getattr(m, "team_wkts", 0) or 0), str(getattr(m, "team_overs", "0.0") or "0.0")],
        [m.opponent_name, str(getattr(m, "opp_runs", opp) or 0), str(getattr(m, "opp_wkts", 0) or 0), str(getattr(m, "opp_overs", "0.0") or "0.0")]
    ]
    t = Table(overview_data, hAlign="LEFT", colWidths=[200, 60, 60, 60])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN",(1,1),(-1,-1),"CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Top performers table
    perf_rows = [["Category","Player","Detail"]]
    if batter:
        sr = (batter["runs"] / batter["balls"] * 100) if batter["balls"]>0 else 0
        perf_rows.append(["Batting", batter["player"].user.username, f"{batter['runs']} ({batter['balls']}b) SR: {sr:.2f}"])
    else:
        perf_rows.append(["Batting", "-", "-"])

    if bowler:
        perf_rows.append(["Bowling", bowler["player"].user.username, f"{bowler['wickets']} wickets, {bowler['overs']:.1f} overs"])
    else:
        perf_rows.append(["Bowling", "-", "-"])

    if fielder:
        perf_rows.append(["Fielding", fielder["player"].user.username, f"{fielder['catches']} catches"])
    else:
        perf_rows.append(["Fielding", "-", "-"])

    pt = Table(perf_rows, colWidths=[100, 180, 160])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
    ]))
    story.append(Paragraph("Top Performers", styles["Heading3"]))
    story.append(pt)
    story.append(Spacer(1, 12))

    # Suggestions (simple AI heuristics — coach-level suggestions)
    suggestions = []
    # Example rules:
    if batter:
        sr = (batter["runs"] / batter["balls"] * 100) if batter["balls"]>0 else 0
        if sr < 70:
            suggestions.append(f"{batter['player'].user.username}: Strike rotation improvement — practice strike-rotation drills and running between wickets to increase SR.")
        else:
            suggestions.append(f"{batter['player'].user.username}: Good power & scoring rate — focus on placement in middle overs.")
    else:
        suggestions.append("No significant batting contributions found to analyse.")

    if bowler:
        econ = (bowler["runs_conceded"] / bowler["overs"]) if bowler["overs"]>0 else 0
        if bowler["wickets"] >= 3:
            suggestions.append(f"{bowler['player'].user.username}: Excellent wicket taking — work on variations to increase consistency.")
        elif econ and econ > 7.5:
            suggestions.append(f"{bowler['player'].user.username}: High economy ({econ:.2f}) — focus on line/length & slower ball control.")
    else:
        suggestions.append("No notable bowling performance found.")

    if fielder:
        if fielder["catches"] >= 2:
            suggestions.append(f"{fielder['player'].user.username}: Strong fielding — practice direct-hit accuracy for run-outs.")
        else:
            suggestions.append("Fielding: Encourage improved ground-fielding drills (reaction & diving).")

    story.append(Paragraph("Coach Suggestions (automated)", styles["Heading3"]))
    for s in suggestions:
        story.append(Paragraph("• " + s, styles["Normal"]))
        story.append(Spacer(1,6))

    # Build PDF
    doc.build(story)

    buffer.seek(0)
    filename = f"match_report_{match_id}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

@app.route("/coach/match/<int:match_id>/result", methods=["POST"])
@login_required
def update_result(match_id):
    if current_user.role != "coach":
        flash("Not allowed.", "danger")
        return redirect(url_for("match_detail", match_id=match_id))

    match = Match.query.get_or_404(match_id)
    match.result = request.form.get("result")

    db.session.commit()
    flash("Match result updated!", "success")
    return redirect(url_for("match_detail", match_id=match_id))

@app.route("/coach/match/<int:match_id>/approve", methods=["GET"])
@login_required
def coach_approve_page(match_id):
    if current_user.role != "coach":
        flash("Not allowed.", "danger")
        return redirect(url_for("home"))

    m = Match.query.get_or_404(match_id)

    batting = ManualScore.query.filter_by(match_id=match_id).filter(ManualScore.balls_faced != None).all()
    bowling = ManualScore.query.filter_by(match_id=match_id).filter(ManualScore.overs != None).all()
    fielding = ManualScore.query.filter_by(match_id=match_id).filter(ManualScore.catches != None).all()

    suggestions = [
        "Top-order should focus on rotating strike in the middle overs.",
        "Bowling unit needs to work on death-over yorker consistency.",
        "Fielders should practice direct-hit drills to convert half-chances."
    ]

    return render_template(
        "coach_approve_matches.html",
        match=m,
        batting=batting,
        bowling=bowling,
        fielding=fielding,
        suggestions=suggestions
    )

@app.route("/coach/match/<int:match_id>/review")
@login_required
def coach_review_match(match_id):

    if current_user.role != "coach":
        flash("Not allowed.", "danger")
        return redirect(url_for("home"))

    match = Match.query.get_or_404(match_id)

    # get rows
    batting = ManualScore.query.filter(
        ManualScore.match_id == match_id,
        ManualScore.balls_faced.isnot(None)
    ).all()

    bowling = ManualScore.query.filter(
        ManualScore.match_id == match_id,
        ManualScore.overs.isnot(None)
    ).all()

    fielding = ManualScore.query.filter(
        ManualScore.match_id == match_id,
        (ManualScore.catches > 0) | (ManualScore.drops > 0) | (ManualScore.saves > 0)
    ).all()

    # simple AI suggestions (already inside your PDF logic — reuse)
    suggestions = []

    for b in batting:
        if b.runs < 10:
            suggestions.append(f"{b.player.user.username}: Needs to build longer innings.")
        elif b.runs >= 30:
            suggestions.append(f"{b.player.user.username}: Good batting performance.")

    for bo in bowling:
        if bo.wickets >= 3:
            suggestions.append(f"{bo.player.user.username}: Excellent wicket-taking spell.")

    return render_template(
        "approve_match.html",
        match=match,
        batting=batting,
        bowling=bowling,
        fielding=fielding,
        suggestions=suggestions
    )


# --------------------------------------------------------
# RUN SERVER
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
