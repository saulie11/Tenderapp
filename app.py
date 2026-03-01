import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__, static_folder="frontend/dist", static_url_path="")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tenderapp.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    CORS(app)

    from backend.database import db
    db.init_app(app)

    # Register blueprints
    from backend.routes.tenders import tenders_bp
    from backend.routes.documents import documents_bp
    from backend.routes.submissions import submissions_bp
    from backend.routes.ai import ai_bp
    from backend.routes.sources import sources_bp
    from backend.routes.notifications import notifications_bp

    app.register_blueprint(tenders_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(submissions_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(sources_bp)
    app.register_blueprint(notifications_bp)

    # Create tables
    with app.app_context():
        db.create_all()
        _seed_demo_data()

    # Serve frontend
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path):
        if path and os.path.exists(os.path.join(app.static_folder or "frontend/dist", path)):
            return send_from_directory(app.static_folder or "frontend/dist", path)
        static_dir = app.static_folder or "frontend/dist"
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        # Fallback to inline HTML if frontend not built
        return send_from_directory("frontend", "index.html")

    # Background scheduler for tender monitoring
    _start_scheduler(app)

    return app


def _seed_demo_data():
    """Seed some demo data on first run."""
    from backend.models import Tender, TenderSource, Notification
    from backend.database import db

    if Tender.query.count() > 0:
        return

    from datetime import datetime, timedelta

    demo_tenders = [
        Tender(
            title="IT Infrastructure Modernization Project",
            reference_number="REF-2026-001",
            issuing_body="Department of Digital Services",
            description="Seeking qualified vendors to provide comprehensive IT infrastructure modernization including cloud migration, network upgrades, and cybersecurity implementation.",
            category="Information Technology",
            value="$2,500,000",
            currency="USD",
            source_name="Government Procurement Portal",
            published_date=datetime.utcnow() - timedelta(days=5),
            closing_date=datetime.utcnow() + timedelta(days=25),
            status="new",
        ),
        Tender(
            title="Construction of Community Health Centre",
            reference_number="REF-2026-002",
            issuing_body="Ministry of Health",
            description="Design and construction of a 5,000 sqm community health centre including outpatient facilities, pharmacy, and administrative offices.",
            category="Construction",
            value="$8,000,000",
            currency="USD",
            source_name="Ministry Procurement",
            published_date=datetime.utcnow() - timedelta(days=10),
            closing_date=datetime.utcnow() + timedelta(days=45),
            status="reviewing",
        ),
        Tender(
            title="Management Consulting Services - Strategic Review",
            reference_number="REF-2026-003",
            issuing_body="National Development Agency",
            description="Procurement of management consulting services for a 12-month strategic review and organizational transformation program.",
            category="Consulting",
            value="$450,000",
            currency="USD",
            source_name="NDA Procurement",
            published_date=datetime.utcnow() - timedelta(days=3),
            closing_date=datetime.utcnow() + timedelta(days=14),
            status="bidding",
        ),
        Tender(
            title="Supply of Office Equipment and Furniture",
            reference_number="REF-2026-004",
            issuing_body="Central Procurement Authority",
            description="Supply and delivery of office furniture, computers, and peripherals for new government offices across 5 locations.",
            category="Supply",
            value="$180,000",
            currency="USD",
            source_name="Central Procurement",
            published_date=datetime.utcnow() - timedelta(days=20),
            closing_date=datetime.utcnow() + timedelta(days=5),
            status="new",
        ),
        Tender(
            title="Environmental Impact Assessment Services",
            reference_number="REF-2025-089",
            issuing_body="Environment Protection Agency",
            description="Provision of environmental impact assessment services for proposed industrial development zones.",
            category="Environmental",
            value="$95,000",
            currency="USD",
            source_name="EPA Portal",
            published_date=datetime.utcnow() - timedelta(days=60),
            closing_date=datetime.utcnow() - timedelta(days=30),
            status="submitted",
        ),
    ]

    for t in demo_tenders:
        db.session.add(t)

    demo_source = TenderSource(
        name="Sample Government RSS Feed",
        url="https://www.ungm.org/Public/Notice/Feed",
        source_type="rss",
        keywords="IT, consulting, construction",
        is_active=True,
        check_interval_hours=24,
    )
    db.session.add(demo_source)

    notification = Notification(
        message="Welcome to TenderApp! 5 demo tenders have been loaded. Add your API key to enable AI features.",
        notification_type="info",
    )
    db.session.add(notification)

    db.session.commit()


def _start_scheduler(app):
    """Start background scheduler for periodic tender checks."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler()

        def check_tenders_job():
            with app.app_context():
                from backend.models import TenderSource, Tender, Notification
                from backend.database import db
                from backend.services.tender_monitor import check_source_for_new_tenders
                from datetime import datetime, timedelta

                sources = TenderSource.query.filter_by(is_active=True).all()
                for source in sources:
                    # Check if it's time to check this source
                    if source.last_checked:
                        next_check = source.last_checked + timedelta(hours=source.check_interval_hours)
                        if datetime.utcnow() < next_check:
                            continue

                    existing_urls = {t.source_url for t in Tender.query.filter(Tender.source_url.isnot(None)).all()}
                    new_tenders = check_source_for_new_tenders(source, existing_urls)

                    for td in new_tenders:
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
                            message=f"New tender found: {tender.title[:80]}",
                            notification_type="new_tender",
                            tender_id=tender.id,
                        )
                        db.session.add(notification)

                    source.last_checked = datetime.utcnow()
                    db.session.commit()

        def check_deadlines_job():
            with app.app_context():
                from backend.models import Tender, Notification
                from backend.database import db
                from datetime import datetime, timedelta

                # Notify about tenders closing in 3 days
                three_days = datetime.utcnow() + timedelta(days=3)
                tomorrow = datetime.utcnow() + timedelta(days=1)
                urgent = Tender.query.filter(
                    Tender.closing_date.between(tomorrow, three_days),
                    Tender.status.notin_(["won", "lost", "ignored", "submitted"]),
                ).all()

                for tender in urgent:
                    # Check if we already sent this notification today
                    existing = Notification.query.filter(
                        Notification.tender_id == tender.id,
                        Notification.notification_type == "deadline",
                        Notification.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0),
                    ).first()
                    if not existing:
                        days = tender._days_until_closing()
                        notification = Notification(
                            message=f"URGENT: '{tender.title}' closes in {days} day(s)!",
                            notification_type="deadline",
                            tender_id=tender.id,
                        )
                        db.session.add(notification)

                db.session.commit()

        scheduler.add_job(check_tenders_job, IntervalTrigger(hours=1))
        scheduler.add_job(check_deadlines_job, IntervalTrigger(hours=6))
        scheduler.start()
    except Exception as e:
        print(f"Scheduler could not start: {e}")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
