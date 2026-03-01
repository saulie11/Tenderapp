from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.database import db
from backend.models import TenderSource, Tender, Notification
from backend.services.tender_monitor import check_source_for_new_tenders

sources_bp = Blueprint("sources", __name__, url_prefix="/api/sources")


@sources_bp.route("", methods=["GET"])
def list_sources():
    sources = TenderSource.query.order_by(TenderSource.created_at.desc()).all()
    return jsonify([s.to_dict() for s in sources])


@sources_bp.route("", methods=["POST"])
def create_source():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("url"):
        return jsonify({"error": "name and url are required"}), 400

    source = TenderSource(
        name=data["name"],
        url=data["url"],
        source_type=data.get("source_type", "rss"),
        keywords=data.get("keywords"),
        is_active=data.get("is_active", True),
        check_interval_hours=data.get("check_interval_hours", 24),
    )
    db.session.add(source)
    db.session.commit()
    return jsonify(source.to_dict()), 201


@sources_bp.route("/<int:source_id>", methods=["PUT"])
def update_source(source_id):
    source = TenderSource.query.get_or_404(source_id)
    data = request.get_json()
    for field in ["name", "url", "source_type", "keywords", "is_active", "check_interval_hours"]:
        if field in data:
            setattr(source, field, data[field])
    db.session.commit()
    return jsonify(source.to_dict())


@sources_bp.route("/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    source = TenderSource.query.get_or_404(source_id)
    db.session.delete(source)
    db.session.commit()
    return jsonify({"message": "Source deleted"})


@sources_bp.route("/<int:source_id>/check", methods=["POST"])
def check_source(source_id):
    """Manually trigger a check for new tenders from a source."""
    source = TenderSource.query.get_or_404(source_id)

    existing_urls = {t.source_url for t in Tender.query.filter(Tender.source_url.isnot(None)).all()}
    new_tenders_data = check_source_for_new_tenders(source, existing_urls)

    added = []
    for td in new_tenders_data:
        tender = Tender(
            title=td["title"],
            description=td.get("description"),
            source_url=td.get("source_url"),
            source_name=td.get("source_name", source.name),
            published_date=td.get("published_date"),
            status="new",
        )
        db.session.add(tender)
        db.session.flush()

        notification = Notification(
            message=f"New tender found: {tender.title}",
            notification_type="new_tender",
            tender_id=tender.id,
        )
        db.session.add(notification)
        added.append(tender.to_dict())

    source.last_checked = datetime.utcnow()
    db.session.commit()

    return jsonify({"new_tenders": added, "count": len(added)})


@sources_bp.route("/check-all", methods=["POST"])
def check_all_sources():
    """Check all active sources for new tenders."""
    sources = TenderSource.query.filter_by(is_active=True).all()
    existing_urls = {t.source_url for t in Tender.query.filter(Tender.source_url.isnot(None)).all()}

    total_added = 0
    for source in sources:
        new_tenders_data = check_source_for_new_tenders(source, existing_urls)
        for td in new_tenders_data:
            tender = Tender(
                title=td["title"],
                description=td.get("description"),
                source_url=td.get("source_url"),
                source_name=td.get("source_name", source.name),
                published_date=td.get("published_date"),
                status="new",
            )
            db.session.add(tender)
            db.session.flush()
            existing_urls.add(td.get("source_url"))
            notification = Notification(
                message=f"New tender found: {tender.title}",
                notification_type="new_tender",
                tender_id=tender.id,
            )
            db.session.add(notification)
            total_added += 1

        source.last_checked = datetime.utcnow()

    db.session.commit()
    return jsonify({"total_added": total_added})
