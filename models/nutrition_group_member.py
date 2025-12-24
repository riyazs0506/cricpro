from .base_models import db

class NutritionGroupMember(db.Model):
    __tablename__ = "nutrition_group_member"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("nutrition_group.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
