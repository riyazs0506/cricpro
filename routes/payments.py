import os
import razorpay

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user

from models import db, PreMatchAvailability, PreMatchResponse
from models.payment import MatchPayment

payments_bp = Blueprint("payments", __name__)

# -------------------------------------------------
# Razorpay Client (TEST & LIVE both supported)
# -------------------------------------------------
def get_razorpay_client():
    return razorpay.Client(
        auth=(
            os.getenv("RAZORPAY_KEY_ID"),
            os.getenv("RAZORPAY_KEY_SECRET")
        )
    )

# -------------------------------------------------
# PAYMENT PAGE
# -------------------------------------------------
@payments_bp.route("/payment/<int:availability_id>")
@login_required
def payment_page(availability_id):

    availability = PreMatchAvailability.query.get_or_404(availability_id)

    # only AVAILABLE players can pay
    PreMatchResponse.query.filter_by(
        availability_id=availability.id,
        user_id=current_user.id,
        status="available"
    ).first_or_404()

    existing = MatchPayment.query.filter_by(
        availability_id=availability.id,
        user_id=current_user.id,
        payment_status="paid"
    ).first()

    if existing:
        flash("Payment already completed", "info")
        return redirect(url_for("payments.payment_history_player"))

    return render_template(
        "payment/payment_page.html",
        availability=availability
    )

# -------------------------------------------------
# CREATE RAZORPAY ORDER (REAL PAYMENT)
# -------------------------------------------------
@payments_bp.route("/payment/create-order/<int:availability_id>")
@login_required
def create_payment_order(availability_id):

    availability = PreMatchAvailability.query.get_or_404(availability_id)

    # prevent duplicate payment
    existing = MatchPayment.query.filter_by(
        availability_id=availability.id,
        user_id=current_user.id,
        payment_status="paid"
    ).first()

    if existing:
        return jsonify({"error": "Already paid"}), 400

    try:
        order = razorpay_client.order.create({
            "amount": int(float(availability.amount) * 100),  # paise
            "currency": "INR",
            "payment_capture": 1
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    payment = MatchPayment(
        availability_id=availability.id,
        user_id=current_user.id,
        amount=availability.amount,
        payment_method="razorpay",
        payment_status="pending",
        razorpay_order_id=order["id"]
    )

    db.session.add(payment)
    db.session.commit()

    return jsonify({
        "order_id": order["id"],
        "amount": int(float(availability.amount) * 100),
        "key": os.getenv("RAZORPAY_KEY_ID")
    })

# -------------------------------------------------
# PAYMENT SUCCESS CALLBACK
# -------------------------------------------------
@payments_bp.route("/payment/success", methods=["POST"])
@login_required
def payment_success():

    data = request.form

    payment = MatchPayment.query.filter_by(
        razorpay_order_id=data.get("razorpay_order_id")
    ).first_or_404()

    payment.razorpay_payment_id = data.get("razorpay_payment_id")
    payment.razorpay_signature = data.get("razorpay_signature")
    payment.payment_status = "paid"

    db.session.commit()

    flash("Payment successful ✅", "success")
    return redirect(url_for("payments.payment_history_player"))

# -------------------------------------------------
# CASH PAYMENT
# -------------------------------------------------
@payments_bp.route("/payment/cash/<int:availability_id>")
@login_required
def cash_payment(availability_id):

    availability = PreMatchAvailability.query.get_or_404(availability_id)

    payment = MatchPayment(
        availability_id=availability.id,
        user_id=current_user.id,
        amount=availability.amount,
        payment_method="cash",
        payment_status="cash_pending"
    )

    db.session.add(payment)
    db.session.commit()

    flash("Cash payment sent for coach approval", "info")
    return redirect(url_for("payments.payment_history_player"))

# -------------------------------------------------
# PLAYER HISTORY
# -------------------------------------------------
@payments_bp.route("/payment/history/player")
@login_required
def payment_history_player():

    payments = MatchPayment.query.filter_by(
        user_id=current_user.id
    ).order_by(MatchPayment.created_at.desc()).all()

    return render_template(
        "payment/payment_history_player.html",
        payments=payments
    )

# -------------------------------------------------
# COACH HISTORY
# -------------------------------------------------
@payments_bp.route("/payment/history/coach")
@login_required
def payment_history_coach():

    if current_user.role != "coach":
        abort(403)

    payments = MatchPayment.query.order_by(
        MatchPayment.created_at.desc()
    ).all()

    return render_template(
        "payment/payment_history_coach.html",
        payments=payments
    )