from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.database import db
from backend.models import Tender, Notification

tenders_bp = Blueprint("tenders", __name__, url_prefix="/api/tenders")


@tenders_bp.route("", methods=["GET"])
def list_tenders():
    status = request.args.get("status")
    search = request.args.get("search")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    query = Tender.query

    if status and status != "all":
        query = query.filter(Tender.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Tender.title.ilike(search_term),
                Tender.issuing_body.ilike(search_term),
                Tender.description.ilike(search_term),
                Tender.reference_number.ilike(search_term),
            )
        )

    query = query.order_by(Tender.created_at.desc())
    total = query.count()
    tenders = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "tenders": [t.to_dict() for t in tenders],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    })


@tenders_bp.route("/<int:tender_id>", methods=["GET"])
def get_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    data = tender.to_dict()
    data["documents"] = [d.to_dict() for d in tender.documents]
    data["submissions"] = [s.to_dict() for s in tender.submissions]
    return jsonify(data)


@tenders_bp.route("", methods=["POST"])
def create_tender():
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    tender = Tender(
        title=data["title"],
        reference_number=data.get("reference_number"),
        issuing_body=data.get("issuing_body"),
        description=data.get("description"),
        category=data.get("category"),
        value=data.get("value"),
        currency=data.get("currency", "USD"),
        source_url=data.get("source_url"),
        source_name=data.get("source_name"),
        notes=data.get("notes"),
        status=data.get("status", "new"),
    )

    if data.get("published_date"):
        try:
            tender.published_date = datetime.fromisoformat(data["published_date"].replace("Z", "+00:00"))
        except ValueError:
            pass

    if data.get("closing_date"):
        try:
            tender.closing_date = datetime.fromisoformat(data["closing_date"].replace("Z", "+00:00"))
        except ValueError:
            pass

    db.session.add(tender)
    db.session.flush()

    notification = Notification(
        message=f"New tender added: {tender.title}",
        notification_type="new_tender",
        tender_id=tender.id,
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify(tender.to_dict()), 201


@tenders_bp.route("/<int:tender_id>", methods=["PUT"])
def update_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    data = request.get_json()

    updatable = ["title", "reference_number", "issuing_body", "description", "category",
                 "value", "currency", "source_url", "source_name", "notes", "status", "is_read"]

    for field in updatable:
        if field in data:
            setattr(tender, field, data[field])

    if "published_date" in data and data["published_date"]:
        try:
            tender.published_date = datetime.fromisoformat(data["published_date"].replace("Z", "+00:00"))
        except ValueError:
            pass

    if "closing_date" in data and data["closing_date"]:
        try:
            tender.closing_date = datetime.fromisoformat(data["closing_date"].replace("Z", "+00:00"))
        except ValueError:
            pass

    tender.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(tender.to_dict())


@tenders_bp.route("/<int:tender_id>", methods=["DELETE"])
def delete_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    db.session.delete(tender)
    db.session.commit()
    return jsonify({"message": "Tender deleted"})


@tenders_bp.route("/stats", methods=["GET"])
def get_stats():
    total = Tender.query.count()
    unread = Tender.query.filter_by(is_read=False).count()
    by_status = db.session.query(Tender.status, db.func.count(Tender.id)).group_by(Tender.status).all()

    # Tenders closing soon (within 7 days)
    from datetime import timedelta
    soon = Tender.query.filter(
        Tender.closing_date <= datetime.utcnow() + timedelta(days=7),
        Tender.closing_date >= datetime.utcnow(),
        Tender.status.notin_(["won", "lost", "ignored"]),
    ).count()

    return jsonify({
        "total": total,
        "unread": unread,
        "closing_soon": soon,
        "by_status": {s: c for s, c in by_status},
    })
