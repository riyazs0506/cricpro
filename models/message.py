from .base_models import db
from datetime import datetime

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    group_id = db.Column(db.Integer, nullable=True)

    content = db.Column(db.Text, nullable=False)

    delivered = db.Column(db.Boolean, default=True)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    # ✅ THIS IS THE FIX
    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        backref="sent_messages"
    )