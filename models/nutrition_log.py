from .base_models import db
from datetime import date

class NutritionLog(db.Model):
    __tablename__ = "nutrition_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    group_id = db.Column(db.Integer, db.ForeignKey("nutrition_group.id"))

    log_date = db.Column(db.Date, default=date.today)

    total_calories = db.Column(db.Float)
    total_protein = db.Column(db.Float)
    total_carbs = db.Column(db.Float)
    total_fat = db.Column(db.Float)

    created_at = db.Column(db.DateTime)

    # ✅ RELATIONSHIP (FIXES your error)
    user = db.relationship("User", backref="nutrition_logs")
