from .base_models import db
from datetime import datetime

class NutritionGroup(db.Model):
    __tablename__ = "nutrition_group"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


