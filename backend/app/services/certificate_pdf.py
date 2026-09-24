"""Renders a real, downloadable PDF certificate -- reportlab, pure Python,
no system dependency (no wkhtmltopdf/headless-Chrome binary to install on
the deploy host), which is why it's the pick over an HTML-to-PDF route.
Kept as its own service (not inline in routes/certificates.py) so the route
stays a thin HTTP wrapper, matching this codebase's existing
services/course_progress.py split of "route does auth + wiring, service
does the actual work"."""

from datetime import datetime
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Matches the frontend's brand/ink tokens (tailwind.config.ts) so a
# downloaded certificate doesn't look like it came from a different
# product than the one that issued it.
BRAND = HexColor("#5624d0")
INK = HexColor("#1c1d1f")
INK_MUTED = HexColor("#6a6f73")
LINE = HexColor("#d1d7dc")


def render_certificate_pdf(
    *,
    learner_name: str,
    course_title: str,
    issued_at: datetime,
    certificate_code: str,
    expires_at: datetime | None,
) -> bytes:
    buffer = BytesIO()
    page_size = landscape(letter)
    width, height = page_size
    c = canvas.Canvas(buffer, pagesize=page_size)

    # Border
    margin = 0.5 * inch
    c.setStrokeColor(BRAND)
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.rect(margin + 0.12 * inch, margin + 0.12 * inch, width - 2 * margin - 0.24 * inch, height - 2 * margin - 0.24 * inch)

    center_x = width / 2

    c.setFillColor(BRAND)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(center_x, height - 1.5 * inch, "CORTEX AI")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(center_x, height - 2.15 * inch, "Certificate of Completion")

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 13)
    c.drawCentredString(center_x, height - 2.9 * inch, "This certifies that")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(center_x, height - 3.55 * inch, learner_name)

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 13)
    c.drawCentredString(center_x, height - 4.15 * inch, "has successfully completed")

    c.setFillColor(BRAND)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(center_x, height - 4.75 * inch, course_title)

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 10)
    footer_y = margin + 0.55 * inch
    c.drawCentredString(center_x, footer_y + 0.3 * inch, f"Issued {issued_at.strftime('%B %d, %Y')}")
    expiry_line = f"Valid until {expires_at.strftime('%B %d, %Y')}" if expires_at else "Does not expire"
    c.drawCentredString(center_x, footer_y, expiry_line)
    c.setFont("Helvetica", 8)
    c.drawCentredString(center_x, footer_y - 0.3 * inch, f"Certificate code: {certificate_code}")

    c.showPage()
    c.save()
    return buffer.getvalue()
