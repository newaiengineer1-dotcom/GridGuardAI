
from agent_modules.bill_split import split_bill
from agent_modules.report import build_report, build_report_pdf
import ui_components as ui

def test_dashboard_surfaces_all_required_lines():
    sp = split_bill(300, 16000, kw=2, kw_known=True, month="2026-09")
    html = ui.bill_intelligence_dashboard(sp, 300, 16000, {"month_label":"Sep 2026","fca":2.0581,"qta":0.5194})
    for term in ["Bill Intelligence Dashboard", "Slab energy charges", "Fixed charges",
                 "FCA / FPA", "QTA", "GST", "Unexplained difference",
                 "2.0581", "0.5194", "CALCULATED", "LOOKUP", "INFERRED", "RECONCILIATION"]:
        assert term in html

def test_pdf_report_is_real_pdf_and_contains_key_text():
    sp = split_bill(300, 16000, kw=2, kw_known=True, month="2026-09")
    data = build_report_pdf({"name":"Test","consumer_no":"1234567890","city":"Lahore",
                             "units":300,"billed":16000,"sanctioned_kw":2}, sp)
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
    txt = build_report({"name":"Test","consumer_no":"1234567890","city":"Lahore",
                        "units":300,"billed":16000,"sanctioned_kw":2}, sp)
    assert "Unexplained difference" in txt
    assert "****7890" in txt

def test_reconciliation_always_equals_billed_amount():
    for billed in [5000, 10000, 16000, 30000]:
        sp = split_bill(300, billed, kw=2, kw_known=True, month="2026-09")
        assert abs(sum(c["amount"] for c in sp["components"]) - billed) < 0.02


def test_protected_financing_surcharge_uses_lower_rate_when_inferred():
    sp = split_bill(200, 5000, kw=2, kw_known=True, category="Protected", month="2026-09")
    labels = " ".join(c["label"] for c in sp["components"])
    assert "Rs 0.43/unit" in labels or "Financing-cost / debt-service surcharge" not in labels
