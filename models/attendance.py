from datetime import date
from .base_models import db

class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.Enum("present", "absent", "late"), nullable=False)
    improvement_note = db.Column(db.Text)
    edit_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    player = db.relationship("Player", backref="attendance_records")
