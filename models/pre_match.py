from .base_models import db
from datetime import datetime




class PreMatchResponse(db.Model):
    __tablename__ = "pre_match_responses"

    id = db.Column(db.Integer, primary_key=True)
    availability_id = db.Column(db.Integer, db.ForeignKey("pre_match_availability.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(20), default="later")
    later_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime)
