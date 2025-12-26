# -------------------- STANDARD IMPORTS --------------------
import io
import os
from datetime import datetime, date, timezone, timedelta

from sqlalchemy import func

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, send_file
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------- SOCKET IO --------------------
from flask_socketio import SocketIO , emit , join_room , leave_room

# -------------------- CONFIG --------------------
from config import DevelopmentConfig

# -------------------- MODELS (SINGLE DB INSTANCE) --------------------
from models import (
    db,
    User, Coach, Player, Batch,
    Match, MatchAssignment, OpponentTempPlayer,
    ManualScore, WagonWheel, LiveBall,
    PlayerStats, BattingStats, BowlingStats, FieldingStats,
    Attendance,
    Notification, Message, ChatGroup, ChatGroupMember, PreMatchResponse, 
    PreMatchAvailability,NutritionGroupMember, NutritionGroup, NutritionLog, 
    NutritionLogItem,FoodItem,MatchPayment
)

# -------------------- DRILL MAP --------------------
from drillmap import DRILL_MAP

# -------------------- UTILS --------------------
from utils import (
    calculate_age, assign_batch_by_age,
    merge_manual_into_player_stats, get_all_allowed_players
)

# -------------------- FORMS --------------------
from forms import (
    RegisterForm, LoginForm, PlayerProfileForm,
    MatchCreateForm, ManualMatchForm
)

# -------------------- PDF --------------------
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors



# -------------------- APP INIT --------------------
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

app.config["SECRET_KEY"] = "THIS_IS_A_STRONG_SECRET_KEY_12345"


from routes.payments import payments_bp
app.register_blueprint(payments_bp)

# -------------------- EXTENSIONS INIT --------------------
db.init_app(app)

socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager(app)
login_manager.login_view = "login"

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print("⚠️ Warning: create_all() failed:", e)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        count = Message.query.filter_by(
            receiver_id=current_user.id,
            is_read=False
        ).count()
        return dict(unread_count=count)
    return dict(unread_count=0)


@app.context_processor
def inject_unread_message_count():
    if current_user.is_authenticated:
        count = Message.query.filter_by(
            receiver_id=current_user.id,
            is_read=0,
            is_deleted=0
        ).count()
        return dict(unread_message_count=count)
    return dict(unread_message_count=0)


@app.context_processor
def inject_unread_messages():
    if current_user.is_authenticated:
        unread = Message.query.filter(
            Message.receiver_id == current_user.id,
            Message.is_read == 0
        ).count()
    else:
        unread = 0

    return dict(unread_messages=unread)



# ================================
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



from datetime import date

def attendance_reminder_for_today(coach_user_id):
    """
    Send reminder notification to coach
    if attendance is not marked today
    """
    today = date.today()

    attendance_exists = Attendance.query.filter(
        Attendance.date == today
    ).first()

    if not attendance_exists:
        existing = Notification.query.filter_by(
            user_id=coach_user_id,
            category="attendance_reminder"
        ).filter(
            Notification.created_at >= datetime.combine(today, datetime.min.time())
        ).first()

        if not existing:
            notif = Notification(
                user_id=coach_user_id,
                message="Attendance not marked for today",
                category="attendance_reminder"
            )
            db.session.add(notif)
            db.session.commit()

# =========================
# DIET PLAN ROUTES
# =========================

@app.route("/diet")
@login_required
def diet_plans():
    return render_template("diet/diet_home.html")

@app.route("/diet/u14")
@login_required
def diet_u14():
    return render_template("diet/diet_u14.html")

@app.route("/diet/u16")
@login_required
def diet_u16():
    return render_template("diet/diet_u16.html")

@app.route("/diet/u19")
@login_required
def diet_u19():
    return render_template("diet/diet_u19.html")

@app.route("/diet/senior")
@login_required
def diet_senior():
    return render_template("diet/diet_senior.html")


# =========================
# FOOD CATEGORY ROUTES
# =========================

@app.route("/diet/foods/fruits")
@login_required
def food_fruits():
    return render_template("diet/food_fruits.html")

@app.route("/diet/foods/vegetables")
@login_required
def food_vegetables():
    return render_template("diet/food_vegetables.html")

@app.route("/diet/foods/nuts-seeds")
@login_required
def food_nuts_seeds():
    return render_template("diet/food_nuts_seeds.html")

@app.route("/diet/foods/dairy")
@login_required
def food_dairy():
    return render_template("diet/food_dairy.html")

@app.route("/diet/foods/grains")
@login_required
def food_grains():
    return render_template("diet/food_grains.html")

@app.route("/diet/foods/protein")
@login_required
def food_protein():
    return render_template("diet/food_protein.html")


# =========================
# FITNESS PLAN ROUTES
# =========================

@app.route("/fitness")
@login_required
def fitness_plans():
    return render_template("fitness/fitness_home.html")


# =========================
# CRICKET SKILLS ROUTES
# =========================

@app.route("/skills")
@login_required
def cricket_skills():
    return render_template("skills/skills_home.html")


# --------------------------------------------------------
# COACH DASHBOARD
# --------------------------------------------------------
from datetime import date
from sqlalchemy import desc

@app.route("/coach/dashboard")
@login_required
def dashboard_coach():
    if current_user.role != "coach":
        return redirect(url_for("home"))

    today = date.today()

    # -------------------------
    # ATTENDANCE
    # -------------------------
    attendance_today = Attendance.query.filter(
        Attendance.date == today
    ).all()

    attendance_present = sum(1 for a in attendance_today if a.status == "present")
    attendance_absent = sum(1 for a in attendance_today if a.status == "absent")

    # -------------------------
    # PLAYER APPROVAL (RESTORED)
    # -------------------------
    pending_players = Player.query.join(User).filter(
        User.status == "pending"
    ).all()

    # -------------------------
    # PLAYER PROFILE LIST (RESTORED)
    # -------------------------
    players = Player.query.all()

    # -------------------------
    # MATCHES (UNCHANGED)
    # -------------------------
    live_matches = Match.query.filter_by(
        status="ongoing",
        scoring_mode="live"
    ).all()

    manual_matches = Match.query.filter_by(
        status="ongoing",
        scoring_mode="manual"
    ).all()

    pending_matches = Match.query.filter_by(
        status="pending_approval"
    ).all()

    # -------------------------
    # ✅ PRE-MATCH AVAILABILITY (IMPORTANT CHANGE)
    # -------------------------
    # 👉 ONLY MOST RECENT SESSION FOR DASHBOARD
    latest_pre_match_session = PreMatchAvailability.query.filter_by(
        user_id=current_user.id
    ).order_by(desc(PreMatchAvailability.created_at)).first()

    # -------------------------
    # NOTIFICATIONS (UNCHANGED)
    # -------------------------
    notifications = Notification.query.filter(
    Notification.user_id == current_user.id,
    Notification.is_read == False,
    Notification.created_at >= (datetime.utcnow() - timedelta(minutes=10))
    ).order_by(Notification.created_at.desc()).all()

    # -------------------------
    # PAYMENT SUMMARY (NEW)
    # -------------------------
    payments = MatchPayment.query.order_by(
        MatchPayment.created_at.desc()
    ).all()

    paid_count = sum(1 for p in payments if p.status == "paid")
    pending_count = sum(1 for p in payments if p.status != "paid")

    return render_template(
    "dashboard_coach.html",
    attendance_present=attendance_present,
    attendance_absent=attendance_absent,
    pending_players=pending_players,
    players=players,
    live_matches=live_matches,
    manual_matches=manual_matches,
    pending_matches=pending_matches,
    latest_pre_match_session=latest_pre_match_session,
    notifications=notifications,

    # ✅ PAYMENT CONTEXT
    paid_count=paid_count,
    pending_count=pending_count
)

@app.route("/coach/pre-match")
@login_required
def coach_pre_match_list():
    if current_user.role != "coach":
        abort(403)

    sessions = PreMatchAvailability.query.order_by(
        PreMatchAvailability.created_at.desc()
    ).all()

    return render_template(
        "coach_pre_match_list.html",
        sessions=sessions
    )


# ================================
# ATTENDANCE LIST VIEWS (SAFE)
# ================================

@app.route("/attendance/today/present")
@login_required
def attendance_today_present():
    if current_user.role != "coach":
        abort(403)

    today = datetime.utcnow().date()

    records = Attendance.query.filter(
        Attendance.date == today,
        Attendance.status == "present"
    ).all()

    return render_template(
        "attendance_list.html",
        title="Present Players",
        records=records
    )


@app.route("/attendance/today/absent")
@login_required
def attendance_today_absent():
    if current_user.role != "coach":
        abort(403)

    today = datetime.utcnow().date()

    records = Attendance.query.filter(
        Attendance.date == today,
        Attendance.status == "absent"
    ).all()

    return render_template(
        "attendance_list.html",
        title="Absent Players",
        records=records
    )


@app.route("/attendance/present-list")
@login_required
def attendance_present_list():
    if current_user.role != "coach":
        abort(403)

    today = datetime.utcnow().date()
    records = Attendance.query.filter_by(
        date=today,
        status="present"
    ).all()

    return render_template(
        "attendance_list.html",
        title="Present Players",
        records=records
    )



@app.route("/attendance/absent-list")
@login_required
def attendance_absent_list():
    if current_user.role != "coach":
        abort(403)

    today = datetime.utcnow().date()
    records = Attendance.query.filter_by(
        date=today,
        status="absent"
    ).all()

    return render_template(
        "attendance_list.html",
        title="Absent Players",
        records=records
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
# --------------------------------------------------------
@app.route("/player/dashboard")
@login_required
def dashboard_player():
    if current_user.role != "player":
        return redirect(url_for("home"))

    player = Player.query.filter_by(user_id=current_user.id).first()
    today = date.today()

    upcoming_matches = Match.query.filter(
        Match.match_date >= today
    ).order_by(Match.match_date.asc()).all()

    attendance_today = Attendance.query.filter_by(
        player_id=player.id,
        date=today
    ).first()

    notifications = Notification.query.filter(
    Notification.user_id == current_user.id,
    Notification.is_read == False,
    Notification.created_at >= (datetime.utcnow() - timedelta(minutes=10))
    ).order_by(Notification.created_at.desc()).all()

    # -------------------------
    # PAYMENT STATUS (NEW)
    # -------------------------
    pending_payment = MatchPayment.query.filter_by(
    user_id=current_user.id,
    payment_status="pending"
    ).first()

    unread_messages = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=0
    ).count()

    return render_template(
    "dashboard_player.html",
    player=player,
    upcoming_matches=upcoming_matches,
    attendance_today=attendance_today,
    notifications=notifications,
    unread_messages=unread_messages,
    pending_payment=pending_payment   # ✅ NEW
    )

@app.route("/notification/<int:notification_id>")
@login_required
def open_notification(notification_id):
    n = Notification.query.get_or_404(notification_id)

    if n.user_id != current_user.id:
        abort(403)

    n.is_read = True
    db.session.commit()

    return redirect(n.link)


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
               # wicket_ball=b.get("wicket_ball"),
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
               # is_opponent=False
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

    # ---------------- BATSMEN ----------------
    for b in full_batting:
        # SAFETY CHECK
        if not b.get("player_name"):
            continue

        runs = b.get("runs", 0)
        balls = b.get("balls", 0)
        sr = (runs / balls * 100) if balls > 0 else 0

        s = []

        if runs >= 50:
            s.append("Excellent batting performance — continue building long innings.")
        elif runs >= 30:
            s.append("Good start — work on converting 30s into big scores.")
        else:
            s.append("Need stronger shot selection and rotation of strike.")

        if balls > 0:
            if sr < 60:
                s.append("Low strike rate — improve running between wickets and placement.")
            elif sr > 120:
                s.append("Great aggressive intent — maintain controlled aggression.")

        suggestions.append({
            "player_name": b["player_name"],
            "suggestions": s
        })

    # ---------------- BOWLERS ----------------
    for bw in full_bowling:
        if not bw.get("player_name"):
            continue

        overs = bw.get("overs", 0)
        runs_conceded = bw.get("runs_conceded", 0)
        wickets = bw.get("wickets", 0)

        econ = (runs_conceded / overs) if overs > 0 else 0
        s = []

        if wickets >= 3:
            s.append("Strong wicket-taking performance — maintain consistency with variations.")
        elif wickets == 0:
            s.append("Focus on bowling tighter lines to create wicket opportunities.")

        if overs > 0:
            if econ > 7.5:
                s.append("Economy rate high — practice yorkers and slower balls.")
            else:
                s.append("Good economical spell — maintain discipline.")

        suggestions.append({
            "player_name": bw["player_name"],
            "suggestions": s
        })

    # ---------------- FIELDERS ----------------
    for f in top_fielding:
        if not f.get("player_name"):
            continue

        catches = f.get("catches", 0)
        s = []

        if catches >= 2:
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

    batting = ManualScore.query.filter(
        ManualScore.match_id == match_id,
        ManualScore.balls_faced.isnot(None),
        ManualScore.is_opponent == False   # ✅ IMPORTANT
    ).all()

    bowling = ManualScore.query.filter(
        ManualScore.match_id == match_id,
        ManualScore.overs.isnot(None),
        ManualScore.is_opponent == False   # ✅ IMPORTANT
    ).all()

    fielding = ManualScore.query.filter(
        ManualScore.match_id == match_id,
        ManualScore.is_opponent == False,
        (ManualScore.catches > 0) |
        (ManualScore.drops > 0) |
        (ManualScore.saves > 0)
    ).all()

    suggestions = []

    # ---------------- BATTING ----------------
    for b in batting:
        if not b.player or not b.player.user:
            continue  # ✅ SAFETY GUARD

        name = b.player.user.username

        if b.runs < 10:
            suggestions.append(f"{name}: Needs to build longer innings.")
        elif b.runs >= 30:
            suggestions.append(f"{name}: Good batting performance.")
        if b.balls_faced and (b.runs / b.balls_faced * 100) < 60:
            suggestions.append(f"{name}: Improve strike rotation.")

    # ---------------- BOWLING ----------------
    for bo in bowling:
        if not bo.player or not bo.player.user:
            continue  # ✅ SAFETY GUARD

        name = bo.player.user.username

        if bo.wickets >= 3:
            suggestions.append(f"{name}: Excellent wicket-taking spell.")
        elif bo.overs and (bo.runs_conceded / bo.overs) > 7:
            suggestions.append(f"{name}: Work on economy rate.")

    # ---------------- FIELDING ----------------
    for f in fielding:
        if not f.player or not f.player.user:
            continue  # ✅ SAFETY GUARD

        name = f.player.user.username

        if f.catches >= 2:
            suggestions.append(f"{name}: Strong catching performance.")
        elif f.drops > 0:
            suggestions.append(f"{name}: Needs catching improvement.")

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



#phase 2 updaed-------------------------------------------

from datetime import date
from collections import defaultdict

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    if current_user.role != "coach":
        abort(403)

    players = Player.query.all()
    today = date.today()

    # ✅ Existing attendance for today
    existing_attendance = Attendance.query.filter_by(date=today).all()

    # ✅ attendance_map FIX (for template)
    attendance_map = {a.player_id: a for a in existing_attendance}

    if request.method == "POST":

        # 🔐 Edit limit check
        if existing_attendance:
            edit_count = existing_attendance[0].edit_count or 0
            if edit_count >= 2:
                flash("Attendance edit limit reached for today (max 2 edits).", "danger")
                return redirect(url_for("attendance"))

        for p in players:
            status = request.form.get(f"player_{p.id}", "absent")
            note = request.form.get(f"note_{p.id}", "")

            record = attendance_map.get(p.id)

            if record:
                # ✅ Update existing
                record.status = status
                record.improvement_note = note
                record.edit_count += 1
            else:
                # ✅ First time mark
                record = Attendance(
                    player_id=p.id,
                    date=today,
                    status=status,
                    improvement_note=note,
                    edit_count=0
                )
                db.session.add(record)

                # AI Suggestions (UNCHANGED)
                ai_suggestions = generate_ai_suggestions(p, note)
                for s in ai_suggestions:
                    db.session.add(Notification(
                        user_id=p.user_id,
                        message=(
                            f"Coach Suggestion ({s['area']}): "
                            f"{s['recommendation']} | Drills: {', '.join(s['drills'])}"
                        ),
                        category="ai_suggestion"
                    ))

        db.session.commit()
        flash("Attendance saved successfully", "success")
        return redirect(url_for("dashboard_coach"))

    return render_template(
        "attendance.html",
        players=players,
        attendance_map=attendance_map
    )

@app.route("/attendance/summary")
@login_required
def attendance_summary():
    if current_user.role != "coach":
        abort(403)

    today = date.today()

    attendance = (
        Attendance.query
        .join(Player, Attendance.player_id == Player.id)
        .join(User, Player.user_id == User.id)
        .filter(Attendance.date == today)
        .order_by(User.username.asc())
        .all()
    )

    total = len(attendance)
    present = sum(1 for a in attendance if a.status == "present")
    absent = sum(1 for a in attendance if a.status == "absent")

    return render_template(
        "attendance_summary.html",
        attendance=attendance,
        date=today,
        total=total,
        present=present,
        absent=absent
    )


@app.route("/attendance/pdf")
@login_required
def attendance_pdf():
    today = date.today()

    attendance = Attendance.query.filter_by(date=today).all()

    os.makedirs("generated_reports", exist_ok=True)
    file_path = f"generated_reports/attendance_{today}.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # ===== TITLE =====
    elements.append(Paragraph(
        f"<b>Attendance Report</b><br/>Date: {today}",
        styles["Title"]
    ))

    elements.append(Paragraph("<br/>", styles["Normal"]))

    # ===== TABLE DATA =====
    table_data = [
        ["Player", "Status", "Coach Note"]
    ]

    for a in attendance:
        table_data.append([
            a.player.user.username,
            "Present" if a.status == "present" else "Absent",
            a.improvement_note or "-"
        ])

    table = Table(table_data, colWidths=[180, 80, 200])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),

        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("ALIGN", (0,0), (0,-1), "LEFT"),

        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),

        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
        ("TOPPADDING", (0,0), (-1,0), 10),
    ]))

    elements.append(table)

    doc.build(elements)

    return send_file(file_path, as_attachment=True)




@app.route("/drills/<int:player_id>", methods=["GET","POST"])
@login_required
def drills(player_id):
    player = Player.query.get_or_404(player_id)

    if request.method == "POST":
        issue = request.form["issue"]
        drills = DRILL_MAP.get(issue, {})
        return render_template("drills.html", player=player, drills=drills)

    return render_template("drills.html", player=player)


# ================================
# PHASE 4 — AI COACH ENGINE
# ================================
# ================================
# PHASE 4 — AI COACH ENGINE
# ================================

def generate_ai_suggestions(player, attendance_note=None):
    """
    AI rule-based coach suggestion engine.
    Uses DRILL_MAP for auto drill suggestions.
    """

    suggestions = []

    if not attendance_note:
        return suggestions

    note = attendance_note.lower()

    # 🟦 Batting issues
    if "bat" in note or "swing" in note:
        suggestions.append({
            "area": "Batting Technique",
            "recommendation": "Improve bat swing & bat path control",
            "drills": DRILL_MAP["bat swing"]["drills"]
        })

    if "foot" in note:
        suggestions.append({
            "area": "Footwork",
            "recommendation": "Improve front & back foot movement",
            "drills": DRILL_MAP["footwork batting"]["drills"]
        })

    if "timing" in note:
        suggestions.append({
            "area": "Timing",
            "recommendation": "Improve timing and play late under eyes",
            "drills": DRILL_MAP["timing"]["drills"]
        })

    # 🟦 Bowling issues
    if "bowling" in note or "action" in note:
        suggestions.append({
            "area": "Bowling Action",
            "recommendation": "Correct bowling action & alignment",
            "drills": DRILL_MAP["bowling action"]["drills"]
        })

    # 🟦 Fitness issues
    if "fitness" in note or "balance" in note:
        suggestions.append({
            "area": "Fitness & Balance",
            "recommendation": "Improve balance, agility and core stability",
            "drills": DRILL_MAP["balance training"]["drills"]
        })

    return suggestions



from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

@app.route("/drills/pdf")
@login_required
def drills_pdf():
    file_path = "generated_reports/drills_report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    content = []

    for topic, data in DRILL_MAP.items():
        content.append(Paragraph(f"<b>{topic.upper()}</b>", styles["Heading2"]))
        for d in data["drills"]:
            content.append(Paragraph(f"- {d}", styles["Normal"]))

    doc.build(content)
    return send_file(file_path, as_attachment=True)




#phase 2 updated end---------------------------------------

# ---------------- CHAT LIST ----------------
@app.route("/chat")
@login_required
def chat_list():
    # 1️⃣ Users you have chatted with
    user_ids = db.session.query(Message.sender_id)\
        .filter(Message.receiver_id == current_user.id)\
        .union(
            db.session.query(Message.receiver_id)
            .filter(Message.sender_id == current_user.id)
        ).all()

    user_ids = [u[0] for u in user_ids if u[0] != current_user.id]

    chat_users = User.query.filter(User.id.in_(user_ids)).all()

    # 2️⃣ Groups user belongs to
    group_ids = (
        ChatGroupMember.query
        .filter_by(user_id=current_user.id)
        .with_entities(ChatGroupMember.group_id)
        .subquery()
    )

    chat_groups = ChatGroup.query.filter(ChatGroup.id.in_(group_ids)).all()

    return render_template(
        "chat_list.html",
        chat_users=chat_users,
        chat_groups=chat_groups
    )





@app.route("/chat/new")
@login_required
def start_new_chat():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template("chat_new.html", users=users)



# -------------------- USER TO USER CHAT --------------------
@app.route("/chat/user/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat_user(user_id):
    other_user = User.query.get_or_404(user_id)

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at).all()

    # MARK RECEIVED MESSAGES AS READ
    Message.query.filter(
        Message.sender_id == user_id,
        Message.receiver_id == current_user.id,
        Message.is_read == 0
    ).update({"is_read": 1})
    db.session.commit()

    return render_template(
        "chat.html",
        messages=messages,
        other_user=other_user
    )



# -------------------- DELETE MESSAGE --------------------
@app.route("/chat/delete/<int:msg_id>", methods=["POST"])
@login_required
def delete_message(msg_id):
    msg = Message.query.get_or_404(msg_id)
    if msg.sender_id != current_user.id:
        abort(403)

    msg.is_deleted = 1
    db.session.commit()
    return redirect(request.referrer)


# -------------------- EDIT MESSAGE --------------------
@app.route("/chat/edit/<int:msg_id>", methods=["POST"])
@login_required
def edit_message(msg_id):
    msg = Message.query.get_or_404(msg_id)
    if msg.sender_id != current_user.id:
        abort(403)

    msg.content = request.form["content"]
    msg.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(request.referrer)


@app.route("/chat/group/create", methods=["GET", "POST"])
@login_required
def create_group_chat():
    users = User.query.filter(User.id != current_user.id).all()

    if request.method == "POST":
        name = request.form["name"]
        members = request.form.getlist("members")

        group = ChatGroup(
            name=name,
            created_by=current_user.id
        )
        db.session.add(group)
        db.session.commit()

        # Add creator
        db.session.add(ChatGroupMember(
            group_id=group.id,
            user_id=current_user.id
        ))

        # Add selected members
        for uid in members:
            db.session.add(ChatGroupMember(
                group_id=group.id,
                user_id=int(uid)
            ))

        db.session.commit()
        flash("Group created successfully", "success")

        return redirect(url_for("chat_group", group_id=group.id))

    return render_template("chat_group_create.html", users=users)




# ---------------- GROUP CHAT ----------------
@app.route("/chat/group/<int:group_id>", methods=["GET"])
@login_required
def chat_group(group_id):
    from models import ChatGroup, ChatGroupMember, Message, User

    group = ChatGroup.query.get_or_404(group_id)

    member_ids = [
        m.user_id for m in ChatGroupMember.query.filter_by(group_id=group_id)
    ]

    if current_user.id not in member_ids:
        abort(403)

    messages = Message.query.filter_by(
        group_id=group_id,
        is_deleted=0
    ).order_by(Message.created_at).all()

    users = User.query.filter(User.id.in_(member_ids)).all()
    users_map = {u.id: u for u in users}

    return render_template(
        "chat_group.html",
        group=group,
        messages=messages,
        users_map=users_map,
        group_id=group_id
    )

#----------------------------------------------

@app.route("/pre-match/create", methods=["GET", "POST"])
@login_required
def pre_match_create():
    if current_user.role != "coach":
        abort(403)

    if request.method == "POST":
        availability = PreMatchAvailability(
            session_id=int(datetime.utcnow().timestamp()),  # unique session
            title=request.form["title"],
            match_date=request.form["match_date"],
            venue=request.form["venue"],
            amount=float(request.form["amount"]),  # ✅ MATCH FEE
            user_id=current_user.id
        )
        db.session.add(availability)
        db.session.commit()

        # 🔔 Notify players + coaches (availability only, payment later)
        users = User.query.filter(User.role.in_(["player", "coach"])).all()
        for u in users:
            db.session.add(Notification(
                user_id=u.id,
                message=f"📢 Pre-Match Availability: {availability.title}",
                link=url_for(
                    "respond_availability",
                    availability_id=availability.id
                )
            ))

        db.session.commit()

        flash("Pre-match availability created successfully", "success")
        return redirect(
            url_for("availability_summary", availability_id=availability.id)
        )

    return render_template("pre_match_create.html")



@app.route("/availability/<int:availability_id>", methods=["GET", "POST"])
@login_required
def respond_availability(availability_id):
    availability = PreMatchAvailability.query.get_or_404(availability_id)

    response = PreMatchResponse.query.filter_by(
        availability_id=availability_id,
        user_id=current_user.id
    ).first()

    if request.method == "POST":
        status = request.form["status"]

        if not response:
            response = PreMatchResponse(
                availability_id=availability_id,
                user_id=current_user.id
            )
            db.session.add(response)

        if status == "later":
            if response.later_count >= 3:
                flash("Later limit reached (3)", "danger")
                return redirect(request.url)
            response.later_count += 1

        response.status = status
        response.updated_at = datetime.utcnow()
        db.session.commit()

        # 🔔 Mark notification read automatically
        Notification.query.filter_by(
            user_id=current_user.id,
            link=request.path
        ).update({"is_read": True})

        db.session.commit()
        flash("Availability response saved", "success")

        # ✅ ROLE-BASED REDIRECT (FIX)
        if current_user.role == "coach":
            return redirect(url_for("dashboard_coach"))
        else:
            return redirect(url_for("dashboard_player"))

    return render_template(
        "pre_match_respond.html",
        availability=availability,
        response=response
    )

@app.route("/availability/<int:availability_id>/summary", methods=["GET", "POST"])
@login_required
def availability_summary(availability_id):
    if current_user.role != "coach":
        abort(403)

    availability = PreMatchAvailability.query.get_or_404(availability_id)

    # Fetch responses
    responses = db.session.query(
        User.id,
        User.username,
        PreMatchResponse.status
    ).join(
        PreMatchResponse, User.id == PreMatchResponse.user_id
    ).filter(
        PreMatchResponse.availability_id == availability_id
    ).all()

    # -------------------------
    # FINISH & ENABLE PAYMENT
    # -------------------------
    if request.method == "POST":
        availability.is_finalized = True
        db.session.commit()

        # 🔔 Notify ONLY AVAILABLE PLAYERS
        for r in responses:
            if r.status == "available":
                db.session.add(Notification(
                    user_id=r.id,
                    message=f"💰 Match fee ₹{availability.amount} enabled. Please pay now.",
                    link=url_for("payments.payment_page", availability_id=availability.id)
                ))

        db.session.commit()

        flash("Squad finalized & payment enabled", "success")
        return redirect(url_for("dashboard_coach"))

    return render_template(
        "availability_summary.html",
        availability=availability,
        responses=responses
    )


@app.route("/availability/<int:availability_id>/pdf")
@login_required
def availability_pdf(availability_id):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    import os

    availability = PreMatchAvailability.query.get_or_404(availability_id)

    # 🔹 Ensure folder exists
    output_dir = "generated_reports"
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(
        output_dir,
        f"pre_match_{availability_id}.pdf"
    )

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    elements = []

    # 🔹 Title
    elements.append(
        Paragraph(
            "<b>Pre-Match Availability Report</b>",
            styles["Title"]
        )
    )
    elements.append(Spacer(1, 12))

    # 🔹 Match Details
    elements.append(Paragraph(
        f"<b>Title:</b> {availability.title or 'N/A'}",
        styles["Normal"]
    ))
    elements.append(Paragraph(
        f"<b>Date:</b> {availability.match_date or 'N/A'}",
        styles["Normal"]
    ))
    elements.append(Paragraph(
        f"<b>Venue:</b> {availability.venue or 'N/A'}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 12))

    # 🔹 Responses
    responses = db.session.query(
        User.username,
        PreMatchResponse.status
    ).join(
        PreMatchResponse,
        User.id == PreMatchResponse.user_id
    ).filter(
        PreMatchResponse.availability_id == availability_id
    ).order_by(User.username).all()

    if responses:
        for r in responses:
            elements.append(
                Paragraph(
                    f"{r.username} — <b>{r.status.upper()}</b>",
                    styles["Normal"]
                )
            )
    else:
        elements.append(
            Paragraph("No responses submitted yet.", styles["Italic"])
        )

    # 🔹 Build PDF
    doc.build(elements)

    return send_file(file_path, as_attachment=True)




# ---------------- SEND MESSAGE ----------------
@app.route("/chat/send", methods=["POST"])
@login_required
def chat_send():
    data = request.json

    msg = Message(
        sender_id=current_user.id,
        receiver_id=data.get("receiver_id"),  # None for group
        group_id=data.get("group_id"),        # None for user chat
        content=data["content"],
        delivered=True
    )

    db.session.add(msg)
    db.session.commit()

    socketio.emit(
        "new_message",
        {
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "group_id": msg.group_id,
            "created_at": msg.created_at.strftime("%H:%M")
        }
    )

    return jsonify({"status": "sent"})

#nutition

from models import (
    NutritionGroup,
    NutritionGroupMember,
    FoodItem,
    NutritionLog,
    NutritionLogItem
)

from datetime import date
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

# =========================
# NUTRITION HOME
# =========================
@app.route("/nutrition")
@login_required
def nutrition_home():
    groups = NutritionGroup.query.all()
    return render_template("nutrition/nutrition_home.html", groups=groups)


# =========================
# CREATE GROUP (COACH ONLY)
# =========================
@app.route("/nutrition/group/create", methods=["GET", "POST"])
@login_required
def nutrition_group_create():
    if current_user.role != "coach":
        abort(403)

    players = User.query.filter_by(role="player").all()

    if request.method == "POST":
        name = request.form["name"]
        members = request.form.getlist("members")

        group = NutritionGroup(
            name=name,
            created_by=current_user.id
        )
        db.session.add(group)
        db.session.flush()

        for uid in members:
            db.session.add(
                NutritionGroupMember(
                    group_id=group.id,
                    user_id=int(uid)
                )
            )

        db.session.commit()
        flash("Nutrition group created", "success")
        return redirect(url_for("nutrition_home"))

    return render_template(
        "nutrition/nutrition_group_create.html",
        players=players
    )


# =========================
# VIEW GROUP
# =========================
@app.route("/nutrition/group/<int:group_id>")
@login_required
def nutrition_group_view(group_id):
    group = NutritionGroup.query.get_or_404(group_id)

    logs = NutritionLog.query.filter_by(
        group_id=group.id
    ).order_by(NutritionLog.created_at.desc()).all()

    return render_template(
        "nutrition/nutrition_group_view.html",
        group=group,
        logs=logs
    )


# =========================
# CALCULATOR
# =========================
@app.route("/nutrition/calculator/<int:group_id>", methods=["GET", "POST"])
@login_required
def nutrition_calculator(group_id):
    group = NutritionGroup.query.get_or_404(group_id)
    foods = FoodItem.query.all()

    if request.method == "POST":
        log = NutritionLog(
            user_id=current_user.id,
            group_id=group.id,
            log_date=date.today(),
            total_calories=0,
            total_protein=0,
            total_carbs=0,
            total_fat=0
        )
        db.session.add(log)
        db.session.flush()

        for f in foods:
            qty = request.form.get(f"qty_{f.id}")
            if qty and float(qty) > 0:
                qty = float(qty)

                item = NutritionLogItem(
                    log_id=log.id,
                    food_id=f.id,
                    quantity=qty,
                    calories=f.calories * qty,
                    protein=f.protein * qty,
                    carbs=f.carbs * qty,
                    fat=f.fat * qty
                )

                log.total_calories += item.calories
                log.total_protein += item.protein
                log.total_carbs += item.carbs
                log.total_fat += item.fat

                db.session.add(item)

        db.session.commit()
        flash("Nutrition saved & shared", "success")
        return redirect(url_for("nutrition_group_view", group_id=group.id))

    return render_template(
        "nutrition/nutrition_calculator.html",
        foods=foods,
        group=group
    )


# =========================
# HISTORY
# =========================
@app.route("/nutrition/history")
@login_required
def nutrition_history():
    logs = NutritionLog.query.filter_by(
        user_id=current_user.id
    ).order_by(NutritionLog.log_date.desc()).all()

    return render_template(
        "nutrition/nutrition_history.html",
        logs=logs
    )



def notify_payment_enabled(availability_id, amount):
    available_players = PreMatchResponse.query.filter_by(
        availability_id=availability_id,
        status="available"
    ).all()

    for r in available_players:
        n = Notification(
            user_id=r.user_id,
            message=f"💰 Match fee ₹{amount} enabled. Please complete payment.",
            link=f"/payment/{availability_id}"
        )
        db.session.add(n)

    db.session.commit()




# -------------------------------------------------
# SOCKET CONNECT → USER ROOM
# -------------------------------------------------
@socketio.on("connect")
def on_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")


@socketio.on("join_group")
def join_group(data):
    group_id = data.get("group_id")
    if current_user.is_authenticated and group_id:
        join_room(f"group_{group_id}")
        print(f"User {current_user.id} joined group_{group_id}")


@socketio.on("join_match_room")
def join_match_room(data):
    match_id = data.get("match_id")
    join_room(f"match_{match_id}")


# -------------------------------------------------
# JOIN GROUP ROOM
# -------------------------------------------------
@socketio.on("join_group")
def handle_join_group(data):
    group_id = data.get("group_id")
    if group_id:
        join_room(f"group_{group_id}")
        print(f"✅ Joined group room: group_{group_id}")

# -------------------- SOCKET EVENTS --------------------
@socketio.on("send_message")
def handle_send_message(data):
    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    content = data.get("content")

    msg = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        delivered=1
    )
    db.session.add(msg)
    db.session.commit()

    payload = {
        "id": msg.id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "created_at": msg.created_at.strftime("%H:%M")
    }

    # ✅ Send to receiver
    socketio.emit(
        "receive_message",
        payload,
        to=f"user_{receiver_id}"
    )

    # ✅ Send back to sender (WhatsApp style instant echo)
    socketio.emit(
        "receive_message",
        payload,
        to=f"user_{sender_id}"
    )

    # ✅ Refresh chat list for both users
    socketio.emit("refresh_chat_list", {}, to=f"user_{receiver_id}")
    socketio.emit("refresh_chat_list", {}, to=f"user_{sender_id}")

@socketio.on("send_group_message")
def handle_group_message(data):
    content = data.get("content")
    group_id = data.get("group_id")

    msg = Message(
        sender_id=current_user.id,
        group_id=group_id,
        content=content,
        delivered=1
    )
    db.session.add(msg)
    db.session.commit()

    socketio.emit(
        "receive_group_message",
        {
            "id": msg.id,
            "group_id": group_id,
            "sender_id": current_user.id,
            "sender_name": current_user.username,
            "content": content
        },
        to=f"group_{group_id}"
    )


@socketio.on("edit_group_message")
def edit_group_message(data):
    msg = Message.query.get(data["msg_id"])
    if msg and msg.sender_id == current_user.id:
        msg.content = data["content"]
        db.session.commit()

        socketio.emit(
            "group_message_edited",
            {
                "msg_id": msg.id,
                "content": msg.content,
                "group_id": msg.group_id
            },
            to=f"group_{msg.group_id}"
        )


@socketio.on("delete_group_message")
def delete_group_message(data):
    msg = Message.query.get(data["msg_id"])
    if msg and msg.sender_id == current_user.id:
        msg.is_deleted = 1
        db.session.commit()

        socketio.emit(
            "group_message_deleted",
            {
                "msg_id": msg.id,
                "group_id": msg.group_id
            },
            to=f"group_{msg.group_id}"
        )


@socketio.on("message_read")
def message_read(data):
    msg = Message.query.get(data["message_id"])
    msg.is_read = 1
    db.session.commit()

    emit("read_receipt", {
        "message_id": msg.id
    }, room=f"user_{msg.sender_id}")


@socketio.on("edit_message")
def edit_message(data):
    msg = Message.query.get(data["id"])
    if msg.sender_id == current_user.id:
        msg.message = data["new_text"]
        db.session.commit()

        emit("message_edited", {
            "id": msg.id,
            "new_text": msg.message
        }, room=data["room"])


@socketio.on("delete_message")
def delete_message(data):
    msg = Message.query.get(data["id"])
    if msg.sender_id == current_user.id:
        msg.is_deleted = 1
        db.session.commit()

        emit("message_deleted", {
            "id": msg.id
        }, room=data["room"])


@socketio.on("mark_read")
def handle_mark_read(data):
    Message.query.filter_by(
        sender_id=data["sender_id"],
        receiver_id=current_user.id,
        is_read=False
    ).update({"is_read": True})

    db.session.commit()





# --------------------------------------------------------
# RUN SERVER
# --------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True)
