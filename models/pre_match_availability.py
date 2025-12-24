# models/pre_match.py

from datetime import datetime
from .base_models import db

class PreMatchAvailability(db.Model):
    __tablename__ = "pre_match_availability"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, nullable=False)

    title = db.Column(db.String(150), nullable=False)
    match_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(120), nullable=False)

    amount = db.Column(db.Float, nullable=False)   # ✅ match fee
    is_finalized = db.Column(db.Boolean, default=False)  # ✅ NEW

    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)