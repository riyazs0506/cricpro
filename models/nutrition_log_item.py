from .base_models import db

class NutritionLogItem(db.Model):
    __tablename__ = "nutrition_log_item"

    id = db.Column(db.Integer, primary_key=True)

    log_id = db.Column(db.Integer, nullable=False)
    food_id = db.Column(db.Integer, nullable=False)

    quantity = db.Column(db.Float, default=1)

    calories = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)