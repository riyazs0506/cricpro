# app.py (top imports, replace previous model imports)
import io
import os
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, current_app, send_file
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)

# config
from config import DevelopmentConfig

# models (package __init__ exposes db and model classes)
# app.py (fixed imports)
from models import (
    db, User, Coach, Player, Batch,
    Match, MatchAssignment, OpponentTempPlayer,
    ManualScore, WagonWheel, LiveBall,
    PlayerStats, BattingStats, BowlingStats, FieldingStats
)


# utils and forms
from utils import (
    calculate_age, assign_batch_by_age,
    merge_manual_into_player_stats, get_all_allowed_players
)
from forms import (
    RegisterForm, LoginForm, PlayerProfileForm,
    MatchCreateForm, ManualMatchForm
)

# PDF helpers
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# SQLAlchemy helpers
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

# Public player profile + stats (viewable by any logged-in user)
@app.route("/player/<int:player_id>/view")
@login_required
def player_public_profile(player_id):
    """
    Public player profile page — visible to any logged-in user (coach or player).
    Shows the player's basic info, user.username, and aggregated stats (PlayerStats).
    """
    player = Player.query.get_or_404(player_id)

    # fetch stats (may be None if no stats yet)
    stats = PlayerStats.query.filter_by(player_id=player.id).first()

    # optionally show recent manual scoring rows for context
    recent_manual = ManualScore.query.filter_by(player_id=player.id).order_by(ManualScore.id.desc()).limit(20).all()

    # allow editing only for the player themselves or coaches (edit link handled in template)
    can_edit = False
    if current_user.role == "coach":
        can_edit = True
    elif current_user.role == "player":
        # allow edit only if viewing your own profile
        p_self = Player.query.filter_by(user_id=current_user.id).first()
        if p_self and p_self.id == player.id:
            can_edit = True

    return render_template(
        "player_public_profile.html",
        player=player,
        stats=stats,
        recent_manual=recent_manual,
        can_edit=can_edit
    )

@app.route("/players")
@login_required
def list_players():
    players = Player.query.all()
    return render_template("player_list.html", players=players)


@app.route("/player/<int:player_id>/profile_view")
@login_required
def view_player_profile(player_id):
    # Get player
    player = Player.query.get_or_404(player_id)

    # Season / career stats (merged)
    career = PlayerStats.query.filter_by(player_id=player_id).first()

    # Match-by-match stats (from ManualScore table)
    batting_rows = ManualScore.query.filter_by(player_id=player_id).filter(
        ManualScore.balls_faced != 0
    ).all()

    bowling_rows = ManualScore.query.filter_by(player_id=player_id).filter(
        ManualScore.overs != 0
    ).all()

    fielding_rows = ManualScore.query.filter_by(player_id=player_id).filter(
        (ManualScore.catches != 0) |
        (ManualScore.drops != 0) |
        (ManualScore.saves != 0)
    ).all()

    return render_template(
        "player_profile_view.html",
        player=player,
        career=career,
        batting_rows=batting_rows,
        bowling_rows=bowling_rows,
        fielding_rows=fielding_rows
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


def generate_coach_suggestions(full_batting, full_bowling, top_fielding):
    suggestions = []

    # --- Batting Suggestions ---
    for b in full_batting:
        sr = (b["runs"] / b["balls"] * 100) if b["balls"] else 0

        s = []
        if b["runs"] >= 50:
            s.append("Excellent batting performance — continue building long innings.")
        elif b["runs"] >= 30:
            s.append("Good start — work on converting 30s into big scores.")
        else:
            s.append("Need stronger shot selection and rotation of strike.")

        if sr < 60:
            s.append("Low strike rate — improve running between wickets and placement.")
        elif sr > 120:
            s.append("Great aggressive intent — maintain controlled aggression.")

        suggestions.append({
            "player_name": b["player_name"],
            "suggestions": s
        })

    # --- Bowling Suggestions ---
    for bw in full_bowling:
        econ = (bw["runs_conceded"] / bw["overs"]) if bw["overs"] else 0
        s = []

        if bw["wickets"] >= 3:
            s.append("Strong wicket-taking performance — maintain consistency with variations.")
        elif bw["wickets"] == 0:
            s.append("Focus on bowling tighter lines to create wicket opportunities.")

        if econ > 7.5:
            s.append("Economy rate high — practice yorkers and slower balls.")
        else:
            s.append("Good economical spell — maintain discipline.")

        suggestions.append({
            "player_name": bw["player_name"],
            "suggestions": s
        })

    # --- Fielding Suggestions ---
    for f in top_fielding:
        s = []
        if f["catches"] >= 2:
            s.append("Good catching performance — work on reaction drills for run-outs.")
        else:
            s.append("Improve anticipation and ready position while fielding.")

        suggestions.append({
            "player_name": f["player_name"],
            "suggestions": s
        })

    return suggestions

@app.route("/match/<int:match_id>/report_view")
@login_required
def match_report_view(match_id):

    m = Match.query.get_or_404(match_id)

    # ---------------- OUR TEAM ROWS ----------------
    our_rows = ManualScore.query.filter_by(match_id=match_id, is_opponent=False).all()

    # ---------------- BATTING ----------------
    full_batting = []
    total = 0
    fow = []
    w_no = 1

    for r in our_rows:
        total += (r.runs or 0)

        if r.balls_faced > 0:
            full_batting.append({
                "player_name": r.player.user.username,
                "runs": r.runs,
                "balls": r.balls_faced,
                "fours": r.fours,
                "sixes": r.sixes,
                "dismissal_type": r.dismissal_type if r.is_out else "Not Out"
            })

        if r.is_out:
            fow.append({
                "number": w_no,
                "score": total,
                "over": r.wicket_over or "-",
                "player_name": r.player.user.username
            })
            w_no += 1

    # ---------------- BOWLING ----------------
    full_bowling = []
    for r in our_rows:
        if r.overs and float(r.overs) > 0:
            full_bowling.append({
                "player_name": r.player.user.username,
                "overs": float(r.overs),
                "runs_conceded": r.runs_conceded,
                "wickets": r.wickets,
            })

    # ---------------- FIELDING ----------------
    top_fielding = []
    for r in our_rows:
        if r.catches > 0:
            top_fielding.append({
                "player_name": r.player.user.username,
                "catches": r.catches
            })

    # ---------------- WAGON WHEEL ----------------
    wagon_list = []
    for w in WagonWheel.query.filter_by(match_id=match_id).all():
        pname = Player.query.get(w.player_id).user.username
        wagon_list.append({
            "player_name": pname,
            "shots": [{
                "angle": w.angle,
                "runs": w.runs,
                "shot_type": w.shot_type
            }]
        })

    # ---------------- RESULT ----------------
    result = None
    if m.team_runs is not None and m.opp_runs is not None:
        if m.team_runs > m.opp_runs:
            result = f"{m.team_name} won by {m.team_runs - m.opp_runs} runs"
        elif m.opp_runs > m.team_runs:
            result = f"{m.opponent_name} won by {m.opp_runs - m.team_runs} runs"
        else:
            result = "Match Tied"

    # ---------------- AI COACH SUGGESTIONS ----------------
    suggestions = generate_coach_suggestions(full_batting, full_bowling, top_fielding)

    # ---------------- FINAL DATA ----------------
    data = {
        "match": m,
        "result": result,

        "our": {
            "runs": m.team_runs or 0,
            "wickets": m.team_wkts or 0,
            "overs": float(m.team_overs or 0)
        },

        "opponent": {
            "runs": m.opp_runs or 0,
            "wickets": m.opp_wkts or 0,
            "overs": float(m.opp_overs or 0)
        },

        "full_batting": full_batting,
        "full_bowling": full_bowling,
        "fow": fow,

        "top_batting": sorted(full_batting, key=lambda x: x["runs"], reverse=True)[:3],
        "top_bowling": sorted(full_bowling, key=lambda x: x["wickets"], reverse=True)[:3],
        "top_fielding": top_fielding,

        "wagon_list": wagon_list,
        "suggestions": suggestions,

        "generated_at": datetime.utcnow()
    }

    return render_template("match_report.html", data=data)


@app.route("/match/<int:match_id>/report_pdf")
@login_required
def match_report_pdf(match_id):

    # USE THE SAME DATA AS VIEW
    response = match_report_view(match_id)
    html_data = response.context["data"]  # Flask provides context here

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30)
    styles = getSampleStyleSheet()
    story = []

    m = html_data["match"]

    # TITLE
    story.append(Paragraph(f"Match Report — {m.title}", styles["Title"]))
    story.append(Paragraph(f"{m.team_name} vs {m.opponent_name}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # SCORE SUMMARY
    summary = [
        ["Team", "Runs", "Wickets", "Overs"],
        [m.team_name, html_data["our"]["runs"], html_data["our"]["wickets"], html_data["our"]["overs"]],
        [m.opponent_name, html_data["opponent"]["runs"], html_data["opponent"]["wickets"], html_data["opponent"]["overs"]],
    ]

    t = Table(summary)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # TOP PERFORMERS
    story.append(Paragraph("Top Performers", styles["Heading2"]))

    for s in html_data["suggestions"]:
        story.append(Paragraph(f"<b>{s['player_name']}</b>", styles["Normal"]))
        for sug in s["suggestions"]:
            story.append(Paragraph(f"• {sug}", styles["Normal"]))
        story.append(Spacer(1, 6))

    doc.build(story)

    buffer.seek(0)
    return send_file(buffer, download_name=f"match_{match_id}_report.pdf", as_attachment=True)



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
# PLAYER STATS PDF DOWNLOAD
# --------------------------------------------------------
@app.route("/player/<int:player_id>/stats/pdf")
@login_required
def player_stats_pdf(player_id):

    player = Player.query.get_or_404(player_id)
    stats = PlayerStats.query.filter_by(player_id=player_id).first()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Player Stats Report - {player.user.username}", styles["Title"]))
    story.append(Spacer(1, 12))

    # Basic info table
    data = [
        ["Field", "Value"],
        ["Name", player.user.username],
        ["Age", player.age or "-"],
        ["Batting Style", player.batting_style or "-"],
        ["Bowling Style", player.bowling_style or "-"],
        ["Role", player.role_in_team or "-"],
    ]

    t = Table(data)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Career Stats
    if stats:
        story.append(Paragraph("Career Stats", styles["Heading2"]))
        data2 = [
            ["Matches", stats.matches],
            ["Runs", stats.total_runs],
            ["Balls", stats.total_balls],
            ["Fours", stats.total_fours],
            ["Sixes", stats.total_sixes],
            ["Wickets", stats.wickets],
            ["Overs Bowled", stats.overs_bowled],
            ["Runs Conceded", stats.runs_conceded],
            ["Catches", stats.catches],
        ]

        t2 = Table(data2)
        t2.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ]))

        story.append(t2)
    else:
        story.append(Paragraph("No stats available yet.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{player.user.username}_stats.pdf",
        mimetype="application/pdf"
    )




# --------------------------------------------------------
# RUN SERVER
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
6ol`1   
+`