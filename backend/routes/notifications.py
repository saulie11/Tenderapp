from flask import Blueprint, request, jsonify
from backend.database import db
from backend.models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.route("", methods=["GET"])
def list_notifications():
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = int(request.args.get("limit", 50))

    query = Notification.query
    if unread_only:
        query = query.filter_by(is_read=False)

    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    unread_count = Notification.query.filter_by(is_read=False).count()

    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "unread_count": unread_count,
    })


@notifications_bp.route("/mark-read", methods=["POST"])
def mark_all_read():
    Notification.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"})


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    notif.is_read = True
    db.session.commit()
    return jsonify(notif.to_dict())
