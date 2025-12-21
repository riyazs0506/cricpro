# models/pre_match.py

from datetime import datetime
from .base_models import db

class PreMatchAvailability(db.Model):
    __tablename__ = "pre_match_availability"

    id = db.Column(db.Integer, primary_key=True)

    # One availability per match
    session_id = db.Column(db.Integer, nullable=False)

    title = db.Column(db.String(150), nullable=False)
    match_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(120), nullable=False)

    # coach who created it
    user_id = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
