from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_inspection_report(payload: dict) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setAuthor("Vahannetra AI")
    pdf.setTitle(f"Inspection Report {payload['inspection_id']}")
    pdf.setSubject("Vehicle Damage Assessment")

    y = 280 * mm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(20 * mm, y, "Vehicle Inspection Report")
    y -= 10 * mm

    pdf.setFont("Helvetica", 11)
    lines = [
        f"Inspection ID: {payload['inspection_id']}",
        f"Vehicle: {payload['vehicle']['plate']} | {payload['vehicle']['model']} | {payload['vehicle']['type']}",
        f"Inspected At: {payload['vehicle']['inspected_at']}",
        f"Health Score: {payload['health_score']}",
        f"Triage Category: {payload['triage_category']}",
        f"Total Findings: {len(payload['findings'])}",
    ]
    for line in lines:
        pdf.drawString(20 * mm, y, line)
        y -= 7 * mm

    y -= 3 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Findings")
    y -= 8 * mm

    pdf.setFont("Helvetica", 10)
    for idx, finding in enumerate(payload["findings"], start=1):
        line = (
            f"{idx}. {finding['type']} | Severity: {finding['severity']} | "
            f"Confidence: {round(float(finding['confidence']) * 100, 1)}% | "
            f"Estimate: ₹{finding['estimate_min']} - ₹{finding['estimate_max']}"
        )
        pdf.drawString(20 * mm, y, line)
        y -= 6 * mm
        if y < 20 * mm:
            pdf.showPage()
            y = 280 * mm
            pdf.setFont("Helvetica", 10)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
