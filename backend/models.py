from datetime import datetime
from backend.database import db


class Tender(db.Model):
    __tablename__ = "tenders"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    reference_number = db.Column(db.String(100), unique=True, nullable=True)
    issuing_body = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(200), nullable=True)
    value = db.Column(db.String(100), nullable=True)
    currency = db.Column(db.String(10), default="USD")
    source_url = db.Column(db.String(1000), nullable=True)
    source_name = db.Column(db.String(200), nullable=True)
    published_date = db.Column(db.DateTime, nullable=True)
    closing_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.String(50), default="new"
    )  # new, reviewing, bidding, submitted, won, lost, ignored
    is_read = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = db.relationship("Document", backref="tender", lazy=True, cascade="all, delete-orphan")
    submissions = db.relationship("Submission", backref="tender", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "reference_number": self.reference_number,
            "issuing_body": self.issuing_body,
            "description": self.description,
            "category": self.category,
            "value": self.value,
            "currency": self.currency,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "closing_date": self.closing_date.isoformat() if self.closing_date else None,
            "status": self.status,
            "is_read": self.is_read,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "document_count": len(self.documents),
            "days_until_closing": self._days_until_closing(),
        }

    def _days_until_closing(self):
        if self.closing_date:
            delta = self.closing_date - datetime.utcnow()
            return delta.days
        return None


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey("tenders.id"), nullable=True)
    name = db.Column(db.String(500), nullable=False)
    doc_type = db.Column(db.String(50), default="general")  # tender_spec, proposal, response, template, general
    content = db.Column(db.Text, nullable=True)  # AI-generated or extracted text
    file_path = db.Column(db.String(1000), nullable=True)
    file_name = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    ai_summary = db.Column(db.Text, nullable=True)
    ai_extracted_data = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tender_id": self.tender_id,
            "name": self.name,
            "doc_type": self.doc_type,
            "content": self.content,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "ai_summary": self.ai_summary,
            "has_file": bool(self.file_path),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey("tenders.id"), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default="draft")  # draft, review, submitted, won, lost
    submitted_date = db.Column(db.DateTime, nullable=True)
    bid_value = db.Column(db.String(100), nullable=True)
    currency = db.Column(db.String(10), default="USD")
    lead_contact = db.Column(db.String(200), nullable=True)
    team_members = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    result_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tender_id": self.tender_id,
            "title": self.title,
            "status": self.status,
            "submitted_date": self.submitted_date.isoformat() if self.submitted_date else None,
            "bid_value": self.bid_value,
            "currency": self.currency,
            "lead_contact": self.lead_contact,
            "team_members": self.team_members,
            "notes": self.notes,
            "result_notes": self.result_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TenderSource(db.Model):
    __tablename__ = "tender_sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    source_type = db.Column(db.String(50), default="rss")  # rss, website, api
    keywords = db.Column(db.Text, nullable=True)  # comma-separated keywords to filter
    is_active = db.Column(db.Boolean, default=True)
    last_checked = db.Column(db.DateTime, nullable=True)
    check_interval_hours = db.Column(db.Integer, default=24)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "source_type": self.source_type,
            "keywords": self.keywords,
            "is_active": self.is_active,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "check_interval_hours": self.check_interval_hours,
            "created_at": self.created_at.isoformat(),
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default="info")  # info, new_tender, deadline, success, warning
    tender_id = db.Column(db.Integer, db.ForeignKey("tenders.id"), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "notification_type": self.notification_type,
            "tender_id": self.tender_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }
