import os
import io
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "md", "rtf"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(file_path: str, mime_type: str = None) -> str:
    """Extract text content from uploaded file."""
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    if ext == "txt" or ext == "md":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if ext == "pdf":
        return _extract_pdf_text(file_path)

    if ext in ("doc", "docx"):
        return _extract_docx_text(file_path)

    return ""


def _extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF using reportlab/basic approach."""
    try:
        # Try pypdf first if available
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            pass

        # Fallback: read raw bytes and extract visible text
        with open(file_path, "rb") as f:
            content = f.read()
        # Basic extraction of text between BT and ET markers
        import re
        text_parts = []
        pattern = rb"BT(.*?)ET"
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            strings = re.findall(rb"\((.*?)\)", match)
            for s in strings:
                try:
                    text_parts.append(s.decode("latin-1"))
                except Exception:
                    pass
        return " ".join(text_parts)
    except Exception as e:
        return f"[Could not extract PDF text: {e}]"


def _extract_docx_text(file_path: str) -> str:
    """Extract text from Word document."""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        return f"[Could not extract DOCX text: {e}]"


def generate_docx(content: str, title: str = "Document") -> bytes:
    """Generate a Word document from text content."""
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Title
    title_para = doc.add_heading(title, 0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Process content - handle markdown-like formatting
    lines = content.split("\n")
    for line in lines:
        line = line.rstrip()
        if line.startswith("# "):
            doc.add_heading(line[2:], 1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], 2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], 3)
        elif line.startswith("- ") or line.startswith("* "):
            para = doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith(tuple(f"{i}. " for i in range(1, 20))):
            para = doc.add_paragraph(line.split(". ", 1)[1] if ". " in line else line, style="List Number")
        elif line == "":
            doc.add_paragraph("")
        else:
            doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf(content: str, title: str = "Document") -> bytes:
    """Generate a PDF from text content."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, spaceAfter=20)
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.5 * cm))

    # Content
    lines = content.split("\n")
    for line in lines:
        line = line.rstrip()
        if not line:
            story.append(Spacer(1, 0.3 * cm))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Heading1"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], styles["Heading3"]))
        elif line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph(f"• {line[2:]}", styles["Normal"]))
        else:
            story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
