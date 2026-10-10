import io
from datetime import date
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def generate_certificate_pdf(recipient_name: str, event_name: str, issue_date: date, issued_by: str, certificate_number: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Title
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width / 2.0, height - 2 * inch, "Certificate of Participation")
    
    # Subtitle
    c.setFont("Helvetica", 18)
    c.drawCentredString(width / 2.0, height - 3 * inch, "This is proudly presented to")
    
    # Recipient Name
    c.setFont("Helvetica-Bold", 42)
    c.drawCentredString(width / 2.0, height - 4.2 * inch, recipient_name)
    
    # Event & Date
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2.0, height - 5.5 * inch, f"For successful participation in {event_name}")
    c.drawCentredString(width / 2.0, height - 6 * inch, f"Issued on: {issue_date.strftime('%B %d, %Y')}")
    
    # Issuer & Cert Number
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, 1.5 * inch, f"Issued by: {issued_by}")
    c.drawRightString(width - 1 * inch, 1.5 * inch, f"Certificate No: {certificate_number}")
    
    # Border
    c.setLineWidth(3)
    c.rect(0.5 * inch, 0.5 * inch, width - 1 * inch, height - 1 * inch)
    
    c.showPage()
    c.save()
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
