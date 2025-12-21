from .base_models import db
from datetime import date

class NutritionLog(db.Model):
    __tablename__ = "nutrition_log"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)

    log_date = db.Column(db.Date, default=date.today)

    total_calories = db.Column(db.Float, default=0)
    total_protein = db.Column(db.Float, default=0)
    total_carbs = db.Column(db.Float, default=0)
    total_fat = db.Column(db.Float, default=0)

    created_at = db.Column(db.DateTime, server_default=db.func.now())