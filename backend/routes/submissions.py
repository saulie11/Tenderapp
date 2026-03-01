from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.database import db
from backend.models import Submission, Notification

submissions_bp = Blueprint("submissions", __name__, url_prefix="/api/submissions")


@submissions_bp.route("", methods=["GET"])
def list_submissions():
    tender_id = request.args.get("tender_id")
    status = request.args.get("status")
    query = Submission.query

    if tender_id:
        query = query.filter_by(tender_id=int(tender_id))
    if status:
        query = query.filter_by(status=status)

    submissions = query.order_by(Submission.created_at.desc()).all()
    return jsonify([s.to_dict() for s in submissions])


@submissions_bp.route("/<int:sub_id>", methods=["GET"])
def get_submission(sub_id):
    sub = Submission.query.get_or_404(sub_id)
    return jsonify(sub.to_dict())


@submissions_bp.route("", methods=["POST"])
def create_submission():
    data = request.get_json()
    if not data or not data.get("tender_id") or not data.get("title"):
        return jsonify({"error": "tender_id and title are required"}), 400

    sub = Submission(
        tender_id=data["tender_id"],
        title=data["title"],
        status=data.get("status", "draft"),
        bid_value=data.get("bid_value"),
        currency=data.get("currency", "USD"),
        lead_contact=data.get("lead_contact"),
        team_members=data.get("team_members"),
        notes=data.get("notes"),
    )

    if data.get("submitted_date"):
        try:
            sub.submitted_date = datetime.fromisoformat(data["submitted_date"].replace("Z", "+00:00"))
        except ValueError:
            pass

    db.session.add(sub)
    db.session.flush()

    notification = Notification(
        message=f"Submission created: {sub.title}",
        notification_type="info",
        tender_id=sub.tender_id,
    )
    db.session.add(notification)
    db.session.commit()
    return jsonify(sub.to_dict()), 201


@submissions_bp.route("/<int:sub_id>", methods=["PUT"])
def update_submission(sub_id):
    sub = Submission.query.get_or_404(sub_id)
    data = request.get_json()

    old_status = sub.status
    updatable = ["title", "status", "bid_value", "currency", "lead_contact",
                 "team_members", "notes", "result_notes"]

    for field in updatable:
        if field in data:
            setattr(sub, field, data[field])

    if "submitted_date" in data and data["submitted_date"]:
        try:
            sub.submitted_date = datetime.fromisoformat(data["submitted_date"].replace("Z", "+00:00"))
        except ValueError:
            pass

    sub.updated_at = datetime.utcnow()

    # Create notification on status change
    if "status" in data and data["status"] != old_status:
        status_messages = {
            "submitted": f"Submission '{sub.title}' has been submitted!",
            "won": f"Congratulations! Submission '{sub.title}' was WON!",
            "lost": f"Submission '{sub.title}' was not successful.",
            "review": f"Submission '{sub.title}' is now under review.",
        }
        msg = status_messages.get(data["status"], f"Submission '{sub.title}' status changed to {data['status']}")
        notif_type = "success" if data["status"] == "won" else "info"
        notification = Notification(
            message=msg,
            notification_type=notif_type,
            tender_id=sub.tender_id,
        )
        db.session.add(notification)

        # Update tender status too
        if data["status"] in ("won", "lost"):
            from backend.models import Tender
            tender = Tender.query.get(sub.tender_id)
            if tender:
                tender.status = data["status"]

    db.session.commit()
    return jsonify(sub.to_dict())


@submissions_bp.route("/<int:sub_id>", methods=["DELETE"])
def delete_submission(sub_id):
    sub = Submission.query.get_or_404(sub_id)
    db.session.delete(sub)
    db.session.commit()
    return jsonify({"message": "Submission deleted"})


@submissions_bp.route("/pipeline", methods=["GET"])
def get_pipeline():
    """Get all submissions grouped by status for pipeline view."""
    statuses = ["draft", "review", "submitted", "won", "lost"]
    pipeline = {}
    for status in statuses:
        subs = Submission.query.filter_by(status=status).order_by(Submission.updated_at.desc()).all()
        pipeline[status] = [s.to_dict() for s in subs]
    return jsonify(pipeline)
