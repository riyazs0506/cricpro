from datetime import datetime
from .base_models import db

class ChatGroup(db.Model):
    __tablename__ = "chat_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatGroupMember(db.Model):
    __tablename__ = "chat_group_members"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("chat_groups.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

