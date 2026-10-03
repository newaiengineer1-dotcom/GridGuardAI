"""Plain-text bill audit report the user can download and attach to a complaint."""
from __future__ import annotations

from datetime import date

from .tariff import TARIFF_VERSION


def mask(ref: str) -> str:
    ref = (ref or "").strip()
    return ("*" * max(len(ref) - 4, 0) + ref[-4:]) if ref else "not provided"


def build_report(case: dict, sp: dict, line_rows=None, mask_reference: bool = True) -> str:
    """``sp`` is the result of ``split_bill``."""
    billed, units = case.get("billed", 0), case.get("units", 0)
    ref = mask(case.get("consumer_no")) if mask_reference else (case.get("consumer_no") or "not provided")
    out = [f"GRIDGUARD AI - BILL AUDIT REPORT ({date.today():%d %b %Y})", "=" * 64,
           f"Consumer: {case.get('name') or 'not provided'}   Reference: {ref}",
           f"City: {case.get('city', '')}   Units: {units:g}   Billed: Rs {billed:,.0f}   Bill month: {sp.get('month') or 'not listed'}",
           f"Category used: {sp['category']}   Sanctioned load: {case.get('sanctioned_kw', 0):g} kW   Confidence: {sp['confidence']}",
           "", "HOW YOUR BILL SPLITS (estimated from units + amount)", "-" * 64]
    out += [f"{c['label']:<50} Rs {c['amount']:>10,.2f}" for c in sp["components"]]
    out += ["-" * 64, f"{'Billed total':<50} Rs {billed:>10,.2f}", "",
            f"Best-fit expected bill: Rs {sp['modelled_total']:,.2f}",
            f"Highest plausible bill: Rs {sp['high']:,.2f}   Lowest: Rs {sp['low']:,.2f}"]
    if sp["overcharge_likely"] > 0:
        out.append(f"Likely overcharge (best fit): Rs {sp['overcharge_likely']:,.0f}")
    if sp["overcharge_conservative"] > 0:
        out.append(f"Conservative overcharge (above the highest plausible bill): Rs {sp['overcharge_conservative']:,.0f}")
    for w in sp["warnings"]:
        out.append(f"WARNING: {w}")
    if line_rows:
        out += ["", "LINE-BY-LINE CHECK AGAINST THE BILL", "-" * 64]
        out += [f"{l:<18} billed Rs {b:>10,.2f}  expected Rs {e:>10,.2f}  {d:+.1%}  {s}" for l, b, e, d, s in line_rows]
    out += ["", "ASSUMPTIONS AND SOURCES"] + [f"- {n}" for n in sp["notes"]]
    out += [f"- Tariff table: {TARIFF_VERSION}",
            "- Surcharges / duty shown above are INFERRED by best fit, not read from your bill. Check each one on the paper bill.",
            "- This is an estimate to support a complaint, not an official re-bill.",
            "- Nothing is filed on your behalf; you decide whether to submit a complaint."]
    return "\n".join(out)


def build_report_pdf(case: dict, sp: dict, line_rows=None, mask_reference: bool = True) -> bytes:
    """Build a compact, professional PDF audit report. Requires reportlab."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.units import mm

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("GGTitle", parent=styles["Title"], fontSize=18, leading=22, spaceAfter=6)
    h2 = ParagraphStyle("GGH2", parent=styles["Heading2"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=5)
    body = ParagraphStyle("GGBody", parent=styles["BodyText"], fontSize=8.5, leading=11)
    small = ParagraphStyle("GGSmall", parent=body, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#4b5563"))
    story = [
        Paragraph("GridGuard AI — Bill Audit Report", title),
        Paragraph(f"Generated {date.today():%d %b %Y}", small), Spacer(1, 5),
        Paragraph("CASE SUMMARY", h2),
    ]
    ref = mask(case.get("consumer_no")) if mask_reference else (case.get("consumer_no") or "not provided")
    summary = [
        ["Consumer", case.get("name") or "not provided"],
        ["Reference", ref],
        ["City", case.get("city", "")],
        ["Bill month", sp.get("month") or "not listed"],
        ["Units", f"{float(case.get('units', 0)):,.0f}"],
        ["Billed", f"Rs {float(case.get('billed', 0)):,.2f}"],
        ["Category", sp["category"].title()],
        ["Sanctioned load", f"{float(case.get('sanctioned_kw', 0)):g} kW"],
        ["Confidence", sp["confidence"]],
        ["Method", sp["mode"].title()],
    ]
    t=Table(summary, colWidths=[38*mm, 142*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eaf2ff")),
                           ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                           ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
                           ("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#cbd5e1")),
                           ("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),5)]))
    story += [t, Paragraph("BILL RECONCILIATION", h2)]
    rows=[["Component","Rs","Share of billed"]]
    billed=float(sp.get("billed",0))
    for c in sp["components"]:
        share=(c["amount"]/billed*100) if billed else 0
        rows.append([c["label"], f"{c['amount']:,.2f}", f"{share:.1f}%"])
    rows.append(["Billed total", f"{billed:,.2f}", "100.0%"])
    t=Table(rows, colWidths=[105*mm, 35*mm, 40*mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f172a")),
                           ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                           ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                           ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
                           ("FONTSIZE",(0,0),(-1,-1),7.5),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#d1d5db")),
                           ("ALIGN",(1,1),(-1,-1),"RIGHT"),("PADDING",(0,0),(-1,-1),4)]))
    story.append(t)
    story += [Paragraph("OVERCHARGE & PLAUSIBILITY", h2),
              Paragraph(
                  f"Best-fit expected: <b>Rs {sp['modelled_total']:,.2f}</b> · "
                  f"plausible range: <b>Rs {sp['low']:,.2f}–Rs {sp['high']:,.2f}</b> · "
                  f"likely overcharge: <b>Rs {sp['overcharge_likely']:,.2f}</b> · "
                  f"conservative overcharge: <b>Rs {sp['overcharge_conservative']:,.2f}</b>.",
                  body)]
    if sp.get("fit_keys"):
        story.append(Paragraph("Inferred optional charges: " + ", ".join(sp["fit_keys"]) +
                               ". These are model inferences, not proof that those lines appear on the bill.", small))
    story += [Paragraph("RATE / EVIDENCE NOTES", h2)]
    for n in sp.get("notes", []):
        story.append(Paragraph("• " + n, small))
    if sp.get("warnings"):
        story.append(Paragraph("WARNINGS", h2))
        for w in sp["warnings"]:
            story.append(Paragraph("• " + w, small))
    if line_rows:
        story.append(Paragraph("LINE-BY-LINE CHECK", h2))
        lr=[["Line","Billed","Expected","Difference","Status"]]
        for l,b,e,d,s in line_rows:
            lr.append([l,f"Rs {b:,.2f}",f"Rs {e:,.2f}",f"{d:+.1%}",s])
        t=Table(lr,colWidths=[38*mm,34*mm,34*mm,30*mm,30*mm],repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f172a")),
                               ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                               ("FONTSIZE",(0,0),(-1,-1),7),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#d1d5db")),
                               ("ALIGN",(1,1),(-1,-1),"RIGHT"),("PADDING",(0,0),(-1,-1),3)]))
        story.append(t)
    story += [Spacer(1,6),
              Paragraph("Important: GridGuard is an analytical estimate, not an official re-bill. Verify the printed bill lines and current NEPRA/DISCO notifications before filing a complaint. Reference numbers are masked by default.", small)]
    doc.build(story)
    return buf.getvalue()
