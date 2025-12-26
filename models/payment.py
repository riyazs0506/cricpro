from datetime import datetime
from models import db

class MatchPayment(db.Model):
    __tablename__ = "match_payments"

    id = db.Column(db.Integer, primary_key=True)

    availability_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)

    payment_method = db.Column(db.String(20), nullable=False)  # razorpay / cash
    payment_status = db.Column(db.String(20), default="pending")  # pending / paid / cash_pending

    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    razorpay_signature = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)