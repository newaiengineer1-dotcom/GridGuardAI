import json

from agent_modules import bill_ocr
from agent_modules.bill_portals import check_consumer_no, portal_for
from agent_modules.planner import appliance_units, cliffs, what_if
from agent_modules.report import build_report, mask
from agent_modules import adjustments
from agent_modules.bill_split import split_bill
from agent_modules.tariff import compare_lines, compute_bill
from agents import Orchestrator


def test_landing_slab_unprotected_and_protected():
    r = compute_bill(150, kw=2, category="Unprotected")
    assert r["lines"][0][1] == round(150 * 28.91, 2) and r["lines"][1][1] == 600
    assert r["total"] == round((150 * 28.91 + 600) * 1.18, 2)
    p = compute_bill(150, kw=2, category="Protected")
    assert p["total"] == round((150 * 13.01 + 600) * 1.18, 2) and p["category"] == "protected"


def test_auto_category_and_cliff():
    assert compute_bill(190, prev_units=150)["category"] == "protected"
    assert compute_bill(210, prev_units=150)["category"] == "unprotected"
    assert compute_bill(150, prev_units=250)["category"] == "unprotected"
    assert compute_bill(210, category="Protected")["category"] == "unprotected"
    assert compute_bill(80, category="Lifeline")["lines"][0][1] == round(80 * 7.74, 2)
    assert compute_bill(210)["total"] > 2 * compute_bill(190)["total"] * 0.9  # the 200-unit cliff is steep


def test_adjustments_move_total_and_band():
    base, adj = compute_bill(300), compute_bill(300, fca=3.0, qta=1.0)
    assert adj["total"] > base["total"] and adj["band_pct"] < base["band_pct"]
    assert compute_bill(300, duty_pct=1.5, other_fixed=35)["total"] > base["total"]


def test_planner():
    w = what_if(250, 60, kw=2)
    assert w["saving"] > 0 and w["units_after"] == 190
    c = cliffs(295, kw=2)
    assert c["next_slab"]["units_left"] == 5 and c["next_slab"]["jump"] > 0
    assert appliance_units("LED bulb", 10, 5) == 15.0


def test_portals_and_reference_check():
    assert portal_for("LESCO")["url"] == "https://bill.pitc.com.pk"
    assert "ke.com.pk" in portal_for("K-Electric")["url"]
    assert check_consumer_no("LESCO", "12 12345 1234567")[0] is True
    assert check_consumer_no("LESCO", "12345")[0] is False
    assert check_consumer_no("LESCO", "")[0] is None


SAMPLE = """LESCO ELECTRICITY BILL  Bill Month: JAN26
Reference No 12 12345 1234567 U
Sanctioned Load 3 kW
Units Consumed: 320
Energy Charges 11,667.20
Fixed Charges 1,200.00
FCA 2.10 per unit  -450.00
GST 2,442.10
Payable within due date 15,812"""


def test_regex_parser_and_normalize():
    n = bill_ocr.normalize(bill_ocr.parse_bill_text(SAMPLE))
    f = n["fields"]
    assert f["units"] == 320 and f["current_bill"] == 15812 and f["energy_charges"] == 11667.2
    assert f["reference_no"].startswith("12123451234567") and n["confidence"] == 1.0
    vals = bill_ocr.case_values(f)
    assert vals["units"] == 320 and vals["billed"] == 15812 and vals["sanctioned_kw"] == 3.0


def test_normalize_flags_bad_values():
    n = bill_ocr.normalize({"units": "99999", "current_bill": "-5", "reference_no": "123"})
    assert n["fields"]["units"] is None and n["fields"]["current_bill"] is None and len(n["issues"]) >= 3


class _Resp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": json.dumps(self.payload)}}]}


def test_extract_image_uses_groq_vision():
    seen = {}

    def post(url, **kw):
        seen.update(kw["json"], url=url)
        return _Resp({"units": "320", "current_bill": "15,812", "reference_no": "12123451234567U"})

    r = bill_ocr.extract_bill(b"not-a-real-image", "bill.png", "gsk_x", post=post)
    assert r["ok"] and r["method"] == "groq-vision" and r["fields"]["units"] == 320
    assert seen["model"] == bill_ocr.GROQ_VISION_MODEL and "groq.com" in seen["url"]
    assert seen["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/")


def test_extract_without_key_and_bad_type():
    assert not bill_ocr.extract_bill(b"x", "bill.jpg", None)["ok"]
    assert not bill_ocr.extract_bill(b"x", "bill.txt", "k")["ok"]


def test_extract_groq_failure_returns_warning():
    def post(*a, **k):
        raise TimeoutError("slow")
    r = bill_ocr.extract_bill(b"x", "bill.jpg", "k", post=post)
    assert not r["ok"] and "Groq could not read" in r["warning"]


def test_compare_lines_and_report():
    sp = split_bill(320, 20000, kw=3, kw_known=True, month="2026-09")
    rows = compare_lines({"energy_charges": 320 * 36.46, "fixed_charges": 1200.0, "current_bill": sp["fit_result"]["total"] * 1.2},
                         sp["fit_result"])
    status = {r[0]: r[4] for r in rows}
    assert status["Energy charges"] == "ok" and status["Fixed charges"] == "ok" and status["Total payable"] == "mismatch"
    txt = build_report({"name": "Ali", "consumer_no": "12123451234567", "city": "Lahore", "units": 320, "billed": 20000,
                        "sanctioned_kw": 3}, sp, rows)
    assert "****" in txt and "12123451234567" not in txt and "Unexplained difference" in txt and "INFERRED" in txt
    assert mask("") == "not provided"


def test_auditor_feeds_complaint():
    case = {"text": "bill zyada", "city": "Lahore", "units": 200, "billed": 30000, "prev_units": 190,
            "consumer_type": "Protected", "sanctioned_kw": 2, "fca": 2.0, "qta": 1.0}
    r = Orchestrator().investigate(case)
    assert r["ctx"]["overcharge_est"] > 20000 and "Bill dispute" in r["ctx"]["draft"]["en"]
    ok = Orchestrator().investigate({**case, "billed": 4500})
    assert ok["ctx"]["overcharge_est"] == 0 and "Bill dispute" not in ok["ctx"]["draft"]["en"]


def test_adjustment_table_and_exemptions():
    assert adjustments.default_month() == "2026-09" and "2026-10" in adjustments.months()
    sep = adjustments.lookup("2026-09", "unprotected")
    assert sep["fca"] == 2.0581 and sep["qta"] == 0.5194
    assert adjustments.lookup("2026-08", "protected")["fca"] == 0.0       # protected exempt from the August FCA
    assert adjustments.lookup("2026-09", "protected")["fca"] == 2.0581    # but not from September's
    assert adjustments.lookup("2026-09", "lifeline")["fca"] == 0.0
    assert adjustments.lookup("2020-01", "unprotected") is None
    assert "PROPOSED" in " ".join(adjustments.lookup("2026-10", "unprotected")["notes"])


def _bill(units=300, kw=2.0, month="2026-09", extras=("nj", "fc"), cat="unprotected"):
    a = adjustments.lookup(month, cat)
    from agent_modules.bill_split import _calc
    return _calc(units, 0, kw, cat, a["fca"], a["qta"], list(extras), None)["total"]


def test_split_recovers_charges_and_sums_to_bill():
    billed = _bill()
    sp = split_bill(300, billed, kw=2.0, kw_known=True, month="2026-09")
    assert sp["fit_keys"] == ["nj", "fc"] and abs(sp["unexplained"]) < 0.01 and sp["confidence"] == "High"
    assert sp["overcharge_conservative"] == 0 and sp["overcharge_likely"] == 0
    assert abs(sum(c["amount"] for c in sp["components"]) - billed) < 0.02
    labels = " ".join(c["label"] for c in sp["components"])
    assert "Slab energy" in labels and "Fixed" in labels and "FCA" in labels and "QTA" in labels and "GST" in labels


def test_overcharge_detected_likely_and_conservative():
    sp = split_bill(300, _bill() + 5000, kw=2.0, kw_known=True, month="2026-09")
    assert sp["overcharge_likely"] > 4500 and sp["overcharge_conservative"] > 3000
    assert any("differs from the model" in w for w in sp["warnings"])
    small = split_bill(300, _bill() + 150, kw=2.0, kw_known=True, month="2026-09")  # inside the plausible range
    assert small["overcharge_conservative"] == 0


def test_abolished_charges_are_flagged():
    sp = split_bill(300, _bill(extras=("nj", "fc", "ptv")), kw=2.0, kw_known=True, month="2026-09")
    assert "ptv" in sp["fit_keys"] and any("PTV" in w for w in sp["warnings"])


def test_unknown_month_uses_implied_split():
    sp = split_bill(300, 16000, kw=2.0, month=None)
    assert sp["mode"] == "implied" and sp["confidence"] == "Indicative"
    assert abs(sum(c["amount"] for c in sp["components"]) - 16000) < 0.02
    assert split_bill(200, 40000, month=None)["overcharge_conservative"] > 20000


def test_unknown_load_widens_range_and_no_bill_mode():
    a = split_bill(300, _bill(), kw=2.0, kw_known=False, month="2026-09")
    b = split_bill(300, _bill(), kw=2.0, kw_known=True, month="2026-09")
    assert (a["high"] - a["low"]) > (b["high"] - b["low"]) and a["confidence"] == "Medium"
    nb = split_bill(300, 0, month="2026-09")
    assert nb["overcharge_likely"] == 0 and nb["modelled_total"] > 0


def test_no_guessed_ptv_or_duty_when_bill_is_just_high():
    sp = split_bill(300, _bill() + 5000, kw=2.0, kw_known=True, month="2026-09")
    assert "ptv" not in sp["fit_keys"] and "duty" not in sp["fit_keys"]
    assert not any("PTV" in w or "duty" in w.lower() for w in sp["warnings"] if "differs" not in w)
    assert abs(sum(c["amount"] for c in sp["components"]) - sp["billed"]) < 0.02
