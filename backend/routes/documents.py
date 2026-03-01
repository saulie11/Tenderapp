import os
from flask import Blueprint, request, jsonify, send_file, current_app
from datetime import datetime
from werkzeug.utils import secure_filename
from backend.database import db
from backend.models import Document, Tender
from backend.services.document_service import allowed_file, extract_text_from_file, generate_docx, generate_pdf
from backend.services import ai_service
import io

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@documents_bp.route("", methods=["GET"])
def list_documents():
    tender_id = request.args.get("tender_id")
    query = Document.query
    if tender_id:
        query = query.filter_by(tender_id=int(tender_id))
    docs = query.order_by(Document.created_at.desc()).all()
    return jsonify([d.to_dict() for d in docs])


@documents_bp.route("/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return jsonify(doc.to_dict())


@documents_bp.route("", methods=["POST"])
def create_document():
    """Create a text/AI-generated document."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    doc = Document(
        name=data["name"],
        tender_id=data.get("tender_id"),
        doc_type=data.get("doc_type", "general"),
        content=data.get("content", ""),
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify(doc.to_dict()), 201


@documents_bp.route("/<int:doc_id>", methods=["PUT"])
def update_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    data = request.get_json()
    for field in ["name", "doc_type", "content", "ai_summary"]:
        if field in data:
            setattr(doc, field, data[field])
    doc.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(doc.to_dict())


@documents_bp.route("/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"message": "Document deleted"})


@documents_bp.route("/upload", methods=["POST"])
def upload_document():
    """Upload a file and optionally analyze it with AI."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    tender_id = request.form.get("tender_id")
    analyze = request.form.get("analyze", "true").lower() == "true"

    filename = secure_filename(file.filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    # Add timestamp to avoid conflicts
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
    saved_filename = timestamp + filename
    file_path = os.path.join(upload_folder, saved_filename)
    file.save(file_path)

    file_size = os.path.getsize(file_path)
    mime_type = file.content_type or "application/octet-stream"

    # Extract text
    extracted_text = extract_text_from_file(file_path, mime_type)

    doc = Document(
        name=filename,
        tender_id=int(tender_id) if tender_id else None,
        doc_type=request.form.get("doc_type", "tender_spec"),
        content=extracted_text[:50000] if extracted_text else "",
        file_path=file_path,
        file_name=filename,
        file_size=file_size,
        mime_type=mime_type,
    )

    # AI analysis
    if analyze and extracted_text:
        try:
            extracted_data = ai_service.analyze_tender_document(extracted_text)
            import json
            doc.ai_extracted_data = json.dumps(extracted_data)
            doc.ai_summary = ai_service.generate_tender_summary(extracted_data)

            # Auto-populate tender if tender_id provided
            if tender_id and extracted_data:
                tender = Tender.query.get(int(tender_id))
                if tender:
                    if not tender.description and extracted_data.get("description"):
                        tender.description = extracted_data["description"]
                    if not tender.issuing_body and extracted_data.get("issuing_body"):
                        tender.issuing_body = extracted_data["issuing_body"]
                    if not tender.value and extracted_data.get("value"):
                        tender.value = extracted_data["value"]
        except Exception as e:
            print(f"AI analysis error: {e}")

    db.session.add(doc)
    db.session.commit()
    return jsonify(doc.to_dict()), 201


@documents_bp.route("/<int:doc_id>/download", methods=["GET"])
def download_document(doc_id):
    """Download a document as DOCX or PDF."""
    doc = Document.query.get_or_404(doc_id)
    fmt = request.args.get("format", "docx")

    if doc.file_path and os.path.exists(doc.file_path) and fmt == "original":
        return send_file(doc.file_path, as_attachment=True, download_name=doc.file_name or doc.name)

    if not doc.content:
        return jsonify({"error": "No content to download"}), 400

    if fmt == "pdf":
        pdf_bytes = generate_pdf(doc.content, title=doc.name)
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"{doc.name}.pdf",
            mimetype="application/pdf",
        )
    else:
        docx_bytes = generate_docx(doc.content, title=doc.name)
        return send_file(
            io.BytesIO(docx_bytes),
            as_attachment=True,
            download_name=f"{doc.name}.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
