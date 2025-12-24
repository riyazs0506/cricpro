# models/payment.py
from datetime import datetime
from .base_models import db

class MatchPayment(db.Model):
    __tablename__ = "match_payments"

    id = db.Column(db.Integer, primary_key=True)

    availability_id = db.Column(
        db.Integer,
        db.ForeignKey("pre_match_availability.id"),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    amount = db.Column(db.Numeric(10, 2), nullable=False)

    # ✅ CONSISTENT NAMES
    payment_method = db.Column(db.String(20), nullable=False)     # razorpay / qr / cash
    payment_status = db.Column(db.String(20), default="pending")  # pending / paid / cash_pending / cash_approved

    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    razorpay_signature = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ✅ RELATIONSHIPS (THIS FIXES TEMPLATE ERRORS)
    user = db.relationship("User", backref="payments")
    availability = db.relationship("PreMatchAvailability", backref="payments")
