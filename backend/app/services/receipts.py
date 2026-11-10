"""Print-friendly payment receipts. Internal database identifiers are never printed."""
from datetime import date, timezone
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from app.core.config import get_settings

RED = colors.HexColor("#C62828")
INK = colors.HexColor("#252B33")
MUTED = colors.HexColor("#626973")
LINE = colors.HexColor("#E8E8EA")
GOLD = colors.HexColor("#FBC02D")


def display_date(value):
    if not value:
        return "Not recorded"
    try:
        return date.fromisoformat(str(value)[:10]).strftime("%d %b %Y")
    except ValueError:
        return str(value)


def display_money(value):
    """Indian digit grouping; INR stays legible with portable PDF fonts."""
    whole, fraction = f"{Decimal(str(value or 0)):.2f}".split(".")
    tail, head = whole[-3:], whole[:-3]
    groups = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return "INR " + ",".join(groups + [tail]) + "." + fraction


class PaymentSummary(Flowable):
    def __init__(self, amount, payment_date, status):
        super().__init__()
        self.amount, self.payment_date, self.status = amount, payment_date, status
        self.height = 108

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(colors.HexColor("#FFF5EF"))
        canvas.roundRect(0, 0, self.width, self.height, 12, stroke=0, fill=1)
        canvas.setFillColor(RED)
        canvas.roundRect(0, 20, 3, 68, 1, stroke=0, fill=1)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#8C5142"))
        canvas.drawString(21, 83, "ORIGINAL PAYMENT" if self.status == "REVERSED" else "AMOUNT RECEIVED")
        font_size = min(29, 325 / max(1, stringWidth(self.amount, "Helvetica-Bold", 1)))
        canvas.setFont("Helvetica-Bold", font_size)
        canvas.setFillColor(INK)
        canvas.drawString(20, 44, self.amount)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(MUTED)
        canvas.drawString(21, 22, "Payment date  /  " + self.payment_date)
        reversed_payment = self.status == "REVERSED"
        chip_width = max(79, stringWidth(self.status, "Helvetica-Bold", 8) + 24)
        chip_x = self.width - chip_width - 19
        canvas.setFillColor(colors.HexColor("#FBE4E0" if reversed_payment else "#E6F1E8"))
        canvas.roundRect(chip_x, 67, chip_width, 23, 11, stroke=0, fill=1)
        canvas.setFillColor(RED if reversed_payment else colors.HexColor("#38674A"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(chip_x + chip_width / 2, 75, self.status)


def render_receipt(receipt, reversed_at=None):
    buffer = BytesIO()
    snapshot = receipt.snapshot
    width, height = A4
    margin = 44
    content_width = width - margin * 2
    styles = {
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=7.5, leading=12,
                                textColor=MUTED, spaceAfter=4),
        "value": ParagraphStyle("value", fontName="Helvetica", fontSize=10, leading=15,
                                textColor=INK, splitLongWords=True),
        "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=19, leading=25,
                               textColor=INK, spaceAfter=4),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=9, leading=14,
                                  textColor=RED, spaceBefore=5, spaceAfter=10),
        "note": ParagraphStyle("note", fontName="Helvetica", fontSize=8, leading=12, textColor=MUTED),
    }

    def paragraph(value, style="value"):
        return Paragraph(escape(str(value)), styles[style])

    generated = receipt.created_at
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    generated = generated.astimezone(ZoneInfo(get_settings().app_timezone))

    def page_frame(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(RED)
        canvas.roundRect(margin, height - 84, 38, 38, 9, stroke=0, fill=1)
        canvas.setFont("Helvetica-BoldOblique", 28)
        canvas.setFillColor(colors.white)
        canvas.drawString(margin + 8, height - 76, "P")
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(3)
        canvas.line(margin + 26, height - 59, margin + 38, height - 47)
        canvas.line(margin + 30, height - 47, margin + 38, height - 47)
        canvas.line(margin + 38, height - 55, margin + 38, height - 47)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 23)
        canvas.drawString(margin + 51, height - 64, "PostMate")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin + 52, height - 79, "EVERY SAVING COUNTS")
        canvas.setFillColor(RED)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(width - margin, height - 59, "PAYMENT RECEIPT")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(width - margin, height - 76, display_date(snapshot.get("payment_date")))
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.7)
        canvas.line(margin, height - 107, width - margin, height - 107)
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(3)
        canvas.line(margin, height - 107, margin + 49, height - 107)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.6)
        canvas.line(margin, 106, width - margin, 106)
        disclaimer = Paragraph("This is an internal record of payment entered into PostMate. "
                               "It is not an official India Post receipt unless issued or authorized by India Post.", styles["note"])
        _, note_height = disclaimer.wrap(content_width, 45)
        disclaimer.drawOn(canvas, margin, 94 - note_height)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin, 43, "Generated " + generated.strftime("%d %b %Y, %I:%M %p %Z"))
        canvas.drawRightString(width - margin, 43, "PostMate  /  Payment records")
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, title="PostMate Payment Receipt", author="PostMate",
                            subject="Internal payment record", leftMargin=margin, rightMargin=margin,
                            topMargin=131, bottomMargin=126)
    status = "REVERSED" if reversed_at else "PART PAYMENT" if Decimal(str(snapshot.get("outstanding") or 0)) > 0 else "PAYMENT RECORDED"
    flow = [PaymentSummary(display_money(snapshot.get("amount")), display_date(snapshot.get("payment_date")), status),
            Spacer(1, 23), paragraph("RECEIVED FROM", "label"),
            paragraph(snapshot.get("customer_name") or "Customer", "name"),
            paragraph(snapshot.get("scheme") or "Savings account"), Spacer(1, 23),
            paragraph("PAYMENT DETAILS", "section")]
    details = []
    if snapshot.get("account_number"):
        details.append(("ACCOUNT NUMBER", snapshot["account_number"]))
    if snapshot.get("policy_number"):
        details.append(("POLICY NUMBER", snapshot["policy_number"]))
    if snapshot.get("cif_id"):
        details.append(("CIF ID", snapshot["cif_id"]))
    details.extend([
        ("PAYMENT METHOD", str(snapshot.get("method") or "Not recorded").replace("_", " ").title()),
        ("INSTALMENT", str(snapshot.get("sequence") or "Not recorded")),
        # ("INSTALMENT DUE DATE", display_date(snapshot.get("due_date"))),
    ])
    if snapshot.get("staff_name"):
        details.append(("COLLECTED BY", snapshot["staff_name"]))
    if snapshot.get("reference"):
        details.append(("TRANSACTION REFERENCE", snapshot["reference"]))
    rows = []
    for index in range(0, len(details), 2):
        cells = [[paragraph(label, "label"), paragraph(value)] for label, value in details[index:index + 2]]
        if len(cells) == 1:
            cells.append("")
        rows.append(cells)
    grid = Table(rows, colWidths=[content_width / 2] * 2, hAlign="LEFT")
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20), ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14), ("LINEBELOW", (0, 0), (-1, -1), .5, LINE),
    ]))
    flow.extend([grid, Spacer(1, 20)])
    if reversed_at:
        flow.append(paragraph("This payment has been reversed. It is excluded from current collections.", "note"))
    else:
        balance = Table([[paragraph("OUTSTANDING FOR THIS INSTALMENT", "label"),
                          paragraph(display_money(snapshot.get("outstanding")))]],
                        colWidths=[content_width * .67, content_width * .33])
        balance.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7F6")),
                                    ("TOPPADDING", (0, 0), (-1, -1), 13), ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 13), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        flow.append(balance)
    doc.build(flow, onFirstPage=page_frame, onLaterPages=page_frame)
    return buffer.getvalue()
