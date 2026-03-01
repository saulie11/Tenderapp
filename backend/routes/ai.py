from flask import Blueprint, request, jsonify
from backend.models import Tender, Document
from backend.services import ai_service
from backend.database import db

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.route("/chat", methods=["POST"])
def chat():
    """AI chat endpoint for tender assistance."""
    data = request.get_json()
    if not data or not data.get("messages"):
        return jsonify({"error": "messages required"}), 400

    tender_context = None
    if data.get("tender_id"):
        tender = Tender.query.get(data["tender_id"])
        if tender:
            tender_context = tender.to_dict()

    try:
        response = ai_service.chat_with_ai(data["messages"], tender_context)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/write-document", methods=["POST"])
def write_document():
    """Generate a tender document using AI."""
    data = request.get_json()
    if not data or not data.get("instruction"):
        return jsonify({"error": "instruction required"}), 400

    tender_context = None
    if data.get("tender_id"):
        tender = Tender.query.get(data["tender_id"])
        if tender:
            tender_context = tender.to_dict()

    try:
        content = ai_service.write_tender_document(
            instruction=data["instruction"],
            tender_context=tender_context,
            document_type=data.get("document_type", "proposal"),
        )

        # Optionally save as document
        if data.get("save") and data.get("name"):
            doc = Document(
                name=data["name"],
                tender_id=data.get("tender_id"),
                doc_type=data.get("document_type", "proposal"),
                content=content,
            )
            db.session.add(doc)
            db.session.commit()
            return jsonify({"content": content, "document": doc.to_dict()})

        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/improve-document/<int:doc_id>", methods=["POST"])
def improve_document(doc_id):
    """Improve an existing document using AI."""
    doc = Document.query.get_or_404(doc_id)
    data = request.get_json()

    if not data or not data.get("instruction"):
        return jsonify({"error": "instruction required"}), 400

    if not doc.content:
        return jsonify({"error": "Document has no content to improve"}), 400

    try:
        improved = ai_service.improve_document(doc.content, data["instruction"])
        if data.get("save", True):
            doc.content = improved
            from datetime import datetime
            doc.updated_at = datetime.utcnow()
            db.session.commit()
        return jsonify({"content": improved, "document": doc.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/analyze-tender/<int:tender_id>", methods=["POST"])
def analyze_tender(tender_id):
    """Generate an AI analysis/summary for a tender."""
    tender = Tender.query.get_or_404(tender_id)
    try:
        summary = ai_service.generate_tender_summary(tender.to_dict())
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/extract-tender", methods=["POST"])
def extract_tender():
    """Extract tender details from pasted text."""
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "text required"}), 400

    try:
        extracted = ai_service.analyze_tender_document(data["text"])
        return jsonify(extracted)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
