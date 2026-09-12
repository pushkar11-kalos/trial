"""
PDF Compliance Inspection Report, built with reportlab's Platypus flowables
(SimpleDocTemplate + Paragraph/Table), per the `pdf` skill guidance checked
before writing this module.

Two things worth calling out:
  - Every piece of dynamic text passed into a Paragraph() is escaped with
    xml.sax.saxutils.escape() first. reportlab's Paragraph markup is a small
    XML-like language, so an unescaped "&" (present in plenty of real
    declaration text, e.g. "Nuts & Seeds") would otherwise break parsing.
  - Currency is always "Rs." in the underlying data (see CLAUDE.md) rather
    than the "₹" glyph, which isn't present in reportlab's base-14 PDF
    fonts and would render as a missing-glyph box.
"""
import io
from typing import Any
from xml.sax.saxutils import escape as _esc

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0B1626")
ACCENT = colors.HexColor("#1D5FC7")
BORDER = colors.HexColor("#E4E7EC")
GREY = colors.HexColor("#667085")

_STATUS_COLORS = {
    "PASS": colors.HexColor("#1E8E5A"),
    "REVIEW": colors.HexColor("#B7791F"),
    "NON_COMPLIANT": colors.HexColor("#C0392B"),
    "NOT_APPLICABLE": colors.HexColor("#667085"),
}
_STATUS_LABELS = {
    "PASS": "PASS",
    "REVIEW": "REVIEW",
    "NON_COMPLIANT": "NON-COMPLIANT",
    "NOT_APPLICABLE": "N/A",
}
_RESULT_COLORS = {
    "COMPLIANT": colors.HexColor("#1E8E5A"),
    "NON_COMPLIANT": colors.HexColor("#C0392B"),
    "REVIEW_REQUIRED": colors.HexColor("#B7791F"),
}


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle("MCTitle", parent=base["Title"], textColor=NAVY, fontSize=22, spaceAfter=2))
    base.add(ParagraphStyle("MCSubtitle", parent=base["Normal"], textColor=GREY, fontSize=9))
    base.add(ParagraphStyle("MCSection", parent=base["Heading2"], textColor=NAVY, spaceBefore=14, spaceAfter=6))
    base.add(ParagraphStyle("MCBody", parent=base["Normal"], fontSize=9.5, leading=13))
    base.add(ParagraphStyle("MCSmall", parent=base["Normal"], fontSize=8, textColor=GREY, leading=11))
    base.add(ParagraphStyle("MCFindingHeader", parent=base["Normal"], fontSize=10.5, leading=14))
    base.add(ParagraphStyle("MCCaption", parent=base["Normal"], fontSize=8, textColor=GREY, alignment=TA_CENTER))
    base.add(
        ParagraphStyle(
            "MCResultBanner", parent=base["Normal"], fontSize=14, textColor=colors.white, alignment=TA_CENTER
        )
    )
    return base


def _scaled_image(path: str, max_w: float, max_h: float):
    try:
        with PILImage.open(path) as im:
            w, h = im.size
        ratio = min(max_w / w, max_h / h)
        return RLImage(path, width=w * ratio, height=h * ratio)
    except Exception:
        return Paragraph("(evidence image unavailable)", ParagraphStyle("x", fontSize=8, textColor=GREY))


def _details_table(ctx: dict[str, Any], styles) -> Table:
    def p(text: Any) -> Paragraph:
        return Paragraph(_esc(str(text)) if text not in (None, "") else "—", styles["MCBody"])

    rows = [
        ["Inspection Reference", p(ctx["reference_code"]), "Inspector", p(ctx["inspector_name"])],
        ["Product", p(ctx["product_name"]), "Brand", p(ctx["brand"])],
        ["Batch / Lot", p(ctx["batch_lot"]), "Category", p(ctx["category"])],
        ["Supply Type", p(ctx["supply_type"].title()), "Location", p(ctx["inspection_location"])],
        [
            "Manufacturer/Importer",
            p(ctx["manufacturer_name"]),
            "Inspection Date",
            p(ctx["inspection_date"].strftime("%d %b %Y") if ctx["inspection_date"] else "—"),
        ],
    ]
    t = Table(rows, colWidths=[95, 155, 90, 145])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), GREY),
                ("TEXTCOLOR", (2, 0), (2, -1), GREY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER),
            ]
        )
    )
    return t


def _result_banner(ctx: dict[str, Any], styles) -> Table:
    result = ctx["overall_result"]
    color = _RESULT_COLORS.get(result, GREY)
    score_txt = f"  ·  Compliance score: {ctx['overall_score']:.0f}%" if ctx.get("overall_score") is not None else ""
    label = result.replace("_", " ")
    t = Table([[Paragraph(f"<b>{_esc(label)}</b>{_esc(score_txt)}", styles["MCResultBanner"])]], colWidths=[485])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def _finding_block(finding: dict[str, Any], styles) -> Table:
    status = finding["status"]
    color = _STATUS_COLORS.get(status, GREY)
    lines = [
        Paragraph(
            f"<b>[{_esc(finding['rule_code'])}] {_esc(finding['rule_name'])}</b> "
            f"&nbsp;—&nbsp; <font color='{color.hexval()}'><b>{_STATUS_LABELS.get(status, status)}</b></font>",
            styles["MCFindingHeader"],
        ),
        Paragraph(
            f"Severity: {_esc(finding.get('severity') or '—')} &nbsp;|&nbsp; "
            f"Category: {_esc(finding.get('category') or '—')}"
            + (
                f" &nbsp;|&nbsp; Confidence: {finding['confidence']:.0f}%"
                if finding.get("confidence") is not None
                else ""
            ),
            styles["MCSmall"],
        ),
    ]
    if finding.get("detected_value"):
        lines.append(Paragraph(f"<b>Detected:</b> {_esc(finding['detected_value'])}", styles["MCBody"]))
    if finding.get("expected_condition"):
        lines.append(Paragraph(f"<b>Expected:</b> {_esc(finding['expected_condition'])}", styles["MCBody"]))
    if finding.get("explanation"):
        lines.append(Paragraph(f"<b>Why:</b> {_esc(finding['explanation'])}", styles["MCBody"]))
    if finding.get("evidence_image_type"):
        lines.append(Paragraph(f"Evidence source: {_esc(finding['evidence_image_type'])} panel", styles["MCSmall"]))

    officer = finding.get("officer_decision")
    if officer:
        note = f" — \u201c{_esc(officer['note'])}\u201d" if officer.get("note") else ""
        lines.append(
            Paragraph(
                f"<b>Officer decision:</b> {_esc(officer['decision'].replace('_',' ').title())} by "
                f"{_esc(officer['officer_name'])} on {officer['decided_at'].strftime('%d %b %Y %H:%M')}{note}",
                styles["MCSmall"],
            )
        )
    else:
        lines.append(Paragraph("<b>Officer decision:</b> pending", styles["MCSmall"]))

    inner = Table([[l] for l in lines], colWidths=[455])
    inner.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        )
    )
    wrapper = Table([[inner]], colWidths=[485])
    wrapper.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 4, color),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return wrapper


def _declarations_table(declarations: list[dict[str, Any]], styles) -> Table:
    header = ["Field", "Value", "Confidence", "Source", "Method"]
    rows = [header]
    for d in declarations:
        rows.append(
            [
                Paragraph(_esc(d["field_label"]), styles["MCSmall"]),
                Paragraph(_esc(d["value"] or "—"), styles["MCSmall"]),
                f"{d['confidence']:.0f}%" if d.get("confidence") is not None else "—",
                _esc(d.get("source_image_type") or "—"),
                "Manual" if d.get("is_manually_edited") else "Automatic",
            ]
        )
    t = Table(rows, colWidths=[110, 175, 55, 65, 65], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ]
        )
    )
    return t


def generate_pdf_report(ctx: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
    )
    styles = _styles()
    story: list[Any] = []

    accent_bar = Table([[""]], colWidths=[485], rowHeights=[4])
    accent_bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    story.append(accent_bar)
    story.append(Spacer(1, 8))
    story.append(Paragraph("MetraCheck", styles["MCTitle"]))
    story.append(Paragraph("AI-Assisted Legal Metrology Compliance &amp; Inspection Platform", styles["MCSubtitle"]))
    story.append(
        Paragraph(
            f"Compliance Inspection Report — generated "
            f"{ctx['generated_at'].strftime('%d %b %Y %H:%M UTC')}",
            styles["MCSubtitle"],
        )
    )
    story.append(Spacer(1, 12))
    story.append(_details_table(ctx, styles))
    story.append(Spacer(1, 12))
    story.append(_result_banner(ctx, styles))
    story.append(Spacer(1, 4))
    if ctx.get("rule_pack_name"):
        story.append(
            Paragraph(
                f"Evaluated against rule pack: <b>{_esc(ctx['rule_pack_name'])} "
                f"({_esc(ctx['rule_pack_version'])})</b>",
                styles["MCSmall"],
            )
        )

    story.append(Paragraph("Rule-by-Rule Findings", styles["MCSection"]))
    if ctx["findings"]:
        for f in ctx["findings"]:
            story.append(_finding_block(f, styles))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No compliance analysis has been run for this inspection yet.", styles["MCBody"]))

    story.append(Paragraph("Extracted Declarations", styles["MCSection"]))
    if ctx["declarations"]:
        story.append(_declarations_table(ctx["declarations"], styles))
    else:
        story.append(Paragraph("No declarations have been extracted for this inspection yet.", styles["MCBody"]))

    if ctx["evidence_images"]:
        story.append(PageBreak())
        story.append(Paragraph("Evidence Photographs", styles["MCSection"]))
        cells = []
        for img in ctx["evidence_images"]:
            if img["absolute_path"]:
                flow = _scaled_image(img["absolute_path"], max_w=2.15 * inch, max_h=2.6 * inch)
            else:
                flow = Paragraph("(unavailable)", styles["MCSmall"])
            cells.append([flow, Paragraph(_esc(img["image_type"]), styles["MCCaption"])])
        grid_rows = []
        for i in range(0, len(cells), 2):
            pair = cells[i : i + 2]
            row = []
            for c in pair:
                inner = Table([[c[0]], [c[1]]])
                row.append(inner)
            if len(row) == 1:
                row.append("")
            grid_rows.append(row)
        img_table = Table(grid_rows, colWidths=[240, 240])
        img_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 14)]))
        story.append(img_table)

    story.append(Spacer(1, 16))
    story.append(Paragraph("Disclaimer", styles["MCSection"]))
    story.append(Paragraph(_esc(ctx["disclaimer"]), styles["MCSmall"]))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Audit timestamp: {ctx['generated_at'].isoformat()}Z &nbsp;|&nbsp; "
            f"Rule pack: {_esc(ctx.get('rule_pack_name') or '—')} "
            f"({_esc(ctx.get('rule_pack_version') or '—')})",
            styles["MCSmall"],
        )
    )

    doc.build(story)
    return buf.getvalue()
