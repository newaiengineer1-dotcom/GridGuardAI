"""Residential (A-1) tariff engine: itemised expected bill from units consumed.

IMPORTANT - how accurate is this?
The slab table below is the SRO 279(I)/2026 domestic table as published by several
bill-guide websites. Those sites do not agree on every figure, and NEPRA / DISCO notices
change it. The monthly FCA, quarterly QTA and any surcharges are NOT in the slab table:
they change every month and are printed on each bill.

So the result is only as good as the inputs:
* units only                      -> rough estimate (about +/-12%)
* units + FCA/QTA from your bill  -> close estimate (about +/-3%)
Use the back-test in the app to measure the real error on your own past bills, and edit
the table below when NEPRA notifies new rates.
"""
from __future__ import annotations

TARIFF_VERSION = "SRO 279(I)/2026 slab table (verify against the latest NEPRA/DISCO notification)"
INF = float("inf")

# (upper unit limit, Rs per unit, fixed charge in Rs per kW per month). Landing-slab billing:
# ALL units are charged at the rate of the band the consumption lands in.
UNPROTECTED = [(100, 22.44, 275), (200, 28.91, 300), (300, 33.10, 350), (400, 36.46, 400),
               (500, 38.95, 500), (600, 40.22, 675), (700, 41.85, 675), (INF, 47.20, 675)]
PROTECTED = [(100, 10.54, 200), (200, 13.01, 300)]
LIFELINE = [(50, 3.95, 0), (100, 7.74, 0)]
GST = 0.18

CATEGORIES = ["Auto-detect", "Protected", "Unprotected", "Lifeline"]
_TABLES = {"protected": PROTECTED, "unprotected": UNPROTECTED, "lifeline": LIFELINE}


def _band(table, units):
    for cap, rate, fc in table:
        if units <= cap:
            return cap, rate, fc
    return table[-1]


def detect_category(units: float, prev_units: float = 0, choice: str = "auto"):
    """Return (category, notes). Protected needs <=200 units in each of the last 6 months."""
    c, notes = (choice or "auto").strip().lower(), []
    if c.startswith("life"):
        if units <= 100:
            return "lifeline", ["Lifeline: minimum monthly charge (if any) is not modelled."]
        notes.append("Lifeline applies only up to 100 units; treated as protected/unprotected instead.")
        c = "auto"
    if c.startswith("prot"):
        if units <= 200:
            return "protected", notes
        return "unprotected", notes + ["Above 200 units the protected rate cannot apply."]
    if c.startswith("unprot"):
        return "unprotected", notes
    # auto
    if units > 200 or (prev_units or 0) > 200:
        if units <= 200:
            notes.append("Last month was above 200 units, so protected status was assumed lost.")
        return "unprotected", notes
    return "protected", notes + ["Assumed protected (<=200 units this and last month). "
                                 "If you crossed 200 units in any of the last 6 months, choose Unprotected."]


def compute_bill(units, prev_units=0, kw=2.0, category="auto", fca=0.0, qta=0.0,
                 other_per_unit=0.0, other_fixed=0.0, duty_pct=0.0, gst=GST, fca_units=None) -> dict:
    """Itemised expected bill. fca / qta / other_per_unit are Rs per unit; duty_pct is a percent.

    ``fca_units``: FCA is billed on the units of the earlier month it belongs to; default is this month's units."""
    units, kw = float(units or 0), float(kw or 0)
    fca, qta, opu = float(fca or 0), float(qta or 0), float(other_per_unit or 0)
    ofx, duty_pct = float(other_fixed or 0), float(duty_pct or 0)
    cat, notes = detect_category(units, float(prev_units or 0), category)
    cap, rate, fc = _band(_TABLES[cat], units)
    energy = units * rate
    fixed = 0.0 if cat == "lifeline" else kw * fc
    fu = units if not fca_units else float(fca_units)
    taxable = energy + fixed + fu * fca + units * (qta + opu)
    duty, gst_amt = taxable * duty_pct / 100, taxable * gst
    total = taxable + duty + gst_amt + ofx

    lines = [(f"Energy charges ({units:g} units x Rs {rate:g})", energy)]
    if fixed:
        lines.append((f"Fixed charges ({kw:g} kW x Rs {fc:g})", fixed))
    if fca:
        lines.append((f"FCA / FPA ({fu:g} x Rs {fca:g})", fu * fca))
    if qta:
        lines.append((f"QTA ({units:g} x Rs {qta:g})", units * qta))
    if opu:
        lines.append((f"Other per-unit charges ({units:g} x Rs {opu:g})", units * opu))
    if duty:
        lines.append((f"Electricity duty ({duty_pct:g}%)", duty))
    lines.append((f"GST ({gst:.0%})", gst_amt))
    if ofx:
        lines.append(("Other fixed charges", ofx))

    given = bool(fca or qta)
    notes.append("FCA/QTA taken from your bill: close estimate." if given else
                 "No FCA/QTA entered: rough estimate. Add them from your bill for a closer match.")
    return {"total": round(total, 2), "category": cat, "rate": rate, "fixed_rate": fc, "band_cap": cap,
            "parts": {"energy": round(energy, 2), "fixed": round(fixed, 2), "fca": round(fu * fca, 2),
                      "qta": round(units * qta, 2), "other": round(units * opu, 2), "duty": round(duty, 2),
                      "gst": round(gst_amt, 2), "other_fixed": round(ofx, 2)},
            "lines": [(label, round(v, 2)) for label, v in lines], "band_pct": 0.03 if given else 0.12,
            "notes": notes, "tariff_version": TARIFF_VERSION}


def expected_bill(units: float) -> float:
    """Backward-compatible helper: expected total for ``units`` with default assumptions."""
    return compute_bill(units)["total"]


def compare_lines(fields: dict, result: dict) -> list:
    """Compare lines read from a real bill with the model: [(label, billed, expected, diff_pct, status)]."""
    by = {}
    for label, v in result["lines"]:
        l = label.lower()
        key = ("energy" if l.startswith("energy") else "fixed" if l.startswith("fixed") else
               "gst" if l.startswith("gst") else None)
        if key:
            by[key] = v
    pairs = [("Energy charges", fields.get("energy_charges"), by.get("energy")),
             ("Fixed charges", fields.get("fixed_charges"), by.get("fixed")),
             ("GST", fields.get("gst_amount"), by.get("gst")),
             ("Total payable", fields.get("current_bill"), result["total"])]
    rows = []
    for label, billed, exp in pairs:
        if billed is None or exp is None or not exp:
            continue
        d = (billed - exp) / exp
        rows.append((label, billed, exp, d, "ok" if abs(d) <= 0.01 else "watch" if abs(d) <= 0.05 else "mismatch"))
    return rows
