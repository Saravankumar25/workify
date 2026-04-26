import asyncio
import io
import logging
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib import colors

from core.config import settings
from services.cloudinary_service import upload_pdf_bytes

logger = logging.getLogger(__name__)

# Resume style: compact, professional
RESUME_STYLES = {
    "h1": ParagraphStyle(
        "h1",
        fontSize=20,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=6,
        spaceBefore=0,
        fontName="Helvetica-Bold",
        alignment=0,
    ),
    "h2": ParagraphStyle(
        "h2",
        fontSize=13,
        textColor=colors.HexColor("#2a2a2a"),
        spaceAfter=4,
        spaceBefore=8,
        fontName="Helvetica-Bold",
        alignment=0,
    ),
    "h3": ParagraphStyle(
        "h3",
        fontSize=11,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=2,
        spaceBefore=4,
        fontName="Helvetica-Bold",
        alignment=0,
    ),
    "body": ParagraphStyle(
        "body",
        fontSize=11,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=4,
        spaceBefore=0,
        leading=1.5 * 11,
        fontName="Helvetica",
        alignment=0,
    ),
    "li": ParagraphStyle(
        "li",
        fontSize=11,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=2,
        spaceBefore=0,
        leading=1.5 * 11,
        fontName="Helvetica",
        alignment=0,
        leftIndent=18,
    ),
}

# Cover letter style: formal, serif
COVER_LETTER_STYLES = {
    "h1": ParagraphStyle(
        "h1",
        fontSize=14,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=12,
        spaceBefore=0,
        fontName="Times-Bold",
        alignment=0,
    ),
    "body": ParagraphStyle(
        "body",
        fontSize=11,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=12,
        spaceBefore=0,
        leading=1.6 * 11,
        fontName="Times-Roman",
        alignment=4,  # justify
    ),
}


def _md_to_elements(md_text: str, styles: dict) -> list:
    """Convert Markdown to reportlab Flowable elements."""
    if not md_text or not md_text.strip():
        return []

    lines = md_text.split("\n")
    elements = []
    in_list = False
    list_items = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# "):
            if list_items:
                elements.append(Spacer(1, 4))
                for item in list_items:
                    elements.append(item)
                list_items = []
                in_list = False
            text = stripped[2:].strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            elements.append(Paragraph(text, styles["h1"]))

        elif stripped.startswith("## "):
            if list_items:
                elements.append(Spacer(1, 2))
                for item in list_items:
                    elements.append(item)
                list_items = []
                in_list = False
            text = stripped[3:].strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            elements.append(Paragraph(text, styles.get("h2", styles["body"])))

        elif stripped.startswith("### "):
            if list_items:
                elements.append(Spacer(1, 2))
                for item in list_items:
                    elements.append(item)
                list_items = []
                in_list = False
            text = stripped[4:].strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            elements.append(Paragraph(text, styles.get("h3", styles["body"])))

        elif stripped.startswith("- ") or stripped.startswith("* "):
            in_list = True
            content = stripped[2:].strip()
            content = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", content)
            li_style = styles.get("li", styles["body"])
            list_items.append(Paragraph("• " + content, li_style))

        elif stripped == "":
            if list_items:
                for item in list_items:
                    elements.append(item)
                list_items = []
                in_list = False
                elements.append(Spacer(1, 4))

        else:
            if list_items:
                for item in list_items:
                    elements.append(item)
                list_items = []
                in_list = False
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            elements.append(Paragraph(text, styles["body"]))

    # Flush remaining list items
    if list_items:
        for item in list_items:
            elements.append(item)

    return elements


def _generate_pdf_sync(markdown: str, is_resume: bool = True) -> bytes:
    """Convert Markdown content to a PDF using ReportLab (sync, blocking)."""
    if not markdown or not markdown.strip():
        raise ValueError("Cannot render empty markdown to PDF")

    styles = RESUME_STYLES if is_resume else COVER_LETTER_STYLES
    margin_top = 1.5 * cm if is_resume else 2.5 * cm
    margin_left = 2 * cm if is_resume else 3 * cm
    margin_right = 2 * cm if is_resume else 3 * cm
    margin_bottom = 1.5 * cm if is_resume else 2.5 * cm

    # Create PDF in memory
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
        leftMargin=margin_left,
        rightMargin=margin_right,
    )

    # Convert markdown to flowable elements
    elements = _md_to_elements(markdown, styles)

    # Build PDF
    doc.build(elements)
    return pdf_buffer.getvalue()


async def _generate_pdf(markdown: str, is_resume: bool = True) -> bytes:
    """Async wrapper for PDF generation with timeout."""
    return await asyncio.wait_for(
        asyncio.to_thread(_generate_pdf_sync, markdown, is_resume),
        timeout=settings.PDF_RENDER_TIMEOUT_SECONDS,
    )


async def export_resume_pdf(
    resume_md: str,
    profile: dict,
    application_id: str = "",
) -> dict:
    """Generate a resume PDF and upload it to Cloudinary."""
    pdf_bytes = await _generate_pdf(resume_md, is_resume=True)
    name = profile.get("full_name", "resume").replace(" ", "_")
    public_id = f"workify/resumes/{application_id or name}"

    result = await upload_pdf_bytes(pdf_bytes, public_id, "workify/resumes")
    return {**result, "pdf_bytes": pdf_bytes}


async def export_cover_letter_pdf(
    cl_md: str,
    profile: dict,
    application_id: str = "",
) -> dict:
    """Generate a cover letter PDF and upload it to Cloudinary."""
    pdf_bytes = await _generate_pdf(cl_md, is_resume=False)
    name = profile.get("full_name", "cover_letter").replace(" ", "_")
    public_id = f"workify/cover_letters/{application_id or name}"

    result = await upload_pdf_bytes(pdf_bytes, public_id, "workify/cover_letters")
    return {**result, "pdf_bytes": pdf_bytes}
