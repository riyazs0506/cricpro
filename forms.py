# forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, SelectField,
    DateField, TextAreaField
)
from wtforms.validators import DataRequired, Email, Optional


# ---------------- AUTH & PROFILE ----------------
class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    role = SelectField("Role", choices=[("player", "Player"), ("coach", "Coach")])
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    username = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class PlayerProfileForm(FlaskForm):
    dob = DateField("Date of Birth", format="%Y-%m-%d", validators=[Optional()])
    batting_style = SelectField("Batting Style", choices=[
        ("Right-hand", "Right-hand"),
        ("Left-hand", "Left-hand")
    ], validators=[Optional()])

    bowling_style = SelectField("Bowling Style", choices=[
        ("Right-arm Fast", "Right-arm Fast"),
        ("Right-arm Medium", "Right-arm Medium"),
        ("Right-arm Spin", "Right-arm Spin"),
        ("Left-arm Fast", "Left-arm Fast"),
        ("Left-arm Medium", "Left-arm Medium"),
        ("Left-arm Spin", "Left-arm Spin")
    ], validators=[Optional()])

    role_in_team = SelectField("Role", choices=[
        ("Batsman", "Batsman"),
        ("Bowler", "Bowler"),
        ("All-rounder", "All-rounder"),
        ("Wicket Keeper", "Wicket Keeper")
    ], validators=[Optional()])

    bio = TextAreaField("Bio", validators=[Optional()])
    submit = SubmitField("Save Profile")


# ---------------- MATCH CREATION (LIVE / MANUAL) ----------------
class MatchCreateForm(FlaskForm):
    title = StringField("Match Title", validators=[DataRequired()])

    match_type = SelectField("Match Type", choices=[
        ("T20", "T20"),
        ("ODI", "ODI"),
        ("TEST", "Test"),
        ("LOCAL", "Local")
    ])

    scoring_mode = SelectField("Scoring Mode", choices=[
        ("live", "Live"),
        ("manual", "Manual"),
        ("mixed", "Mixed")
    ], default="live")

    venue = StringField("Venue", validators=[Optional()])
    match_date = DateField("Match Date", format="%Y-%m-%d", validators=[DataRequired()])

    team_name = StringField("Your Team Name", validators=[DataRequired()])
    opponent_name = StringField("Opponent Team Name", validators=[DataRequired()])

    # ⭐ Toss Fields
    toss_winner = SelectField("Toss Winner", choices=[], validators=[Optional()])
    toss_decision = SelectField("Decision", choices=[
        ("bat", "Bat First"),
        ("bowl", "Bowl First")
    ], validators=[Optional()])

    scorer_type = SelectField("Scorer Type", choices=[
        ("coach", "Coach"),
        ("player", "Player")
    ], default="coach")

    scorer_player = SelectField("Scorer Player", choices=[], coerce=int, validators=[Optional()])

    submit = SubmitField("Create Match")


# ---------------- MANUAL MATCH CREATION ----------------
class ManualMatchForm(FlaskForm):
    title = StringField("Match Title", validators=[DataRequired()])
    match_date = DateField("Match Date", format="%Y-%m-%d", validators=[DataRequired()])

    match_type = SelectField("Match Type", choices=[
        ("T20", "T20"),
        ("ODI", "ODI"),
        ("TEST", "Test"),
        ("LOCAL", "Local Tournament")
    ], validators=[DataRequired()])

    scoring_mode = SelectField("Scoring Mode", choices=[
        ("manual", "Manual Scoring"),
        ("mixed", "Mixed Mode")
    ], default="manual")

    venue = StringField("Venue", validators=[DataRequired()])

    # Team names
    team_name = StringField("Your Team Name", validators=[DataRequired()])
    opponent_name = StringField("Opponent Team Name", validators=[DataRequired()])

    # Toss fields (dynamic)
    toss_winner = SelectField("Toss Winner", choices=[], validators=[Optional()])
    toss_decision = SelectField("Decision", choices=[
        ("bat", "Bat First"),
        ("bowl", "Bowl First")
    ])

    # Scorer
    scorer_type = SelectField(
        "Scorer",
        choices=[("coach", "Coach"), ("player", "Player")],
        default="coach"
    )

    # IMPORTANT: allow empty value
    scorer_player = SelectField(
        "Select Player Scorer",
        choices=[(0, "--- Select Player ---")],   # <-- FIXED
        coerce=int,
        validators=[Optional()]
    )

    submit = SubmitField("Create Manual Match")


