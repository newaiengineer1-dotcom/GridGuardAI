"""Auto-split a bill from just UNITS and the BILLED AMOUNT.

What is known for sure vs. inferred
-----------------------------------
* slab energy charge, fixed charge, GST       -> computed from the tariff table
* monthly FCA and quarterly QTA               -> looked up from NEPRA decisions (adjustments.json)
* surcharges / duty (NJ, financing cost, ED)  -> sources disagree on which are on a bill today, so the
  app tries every combination and keeps the one that best matches YOUR billed amount (a best fit,
  clearly labelled as inferred)
* whatever is left                            -> "Unexplained difference"

Two overcharge numbers are reported:
* likely       = billed - best-fit bill (what the data most plausibly says)
* conservative = billed - the HIGHEST plausible bill (all optional charges on, load +1 kW).
  Only this part is hard to explain away, so it is the one used in complaints.
"""
from __future__ import annotations

from itertools import combinations

from .adjustments import lookup
from .tariff import GST, compute_bill

OPTIONAL = {
    "nj": {"label": "Neelum-Jhelum surcharge", "per_unit": 0.10},
    "fc": {"label": "Financing-cost / debt-service surcharge", "per_unit": 3.23, "protected_per_unit": 0.43},
    "duty": {"label": "Electricity duty (1.5%)", "pct": 1.5},
    "ptv": {"label": "PTV fee (reported abolished July 2025)", "fixed": 35.0},
}
PLAUSIBLE = ("nj", "fc", "duty")          # used for the conservative upper bound (PTV is reported abolished)
FALLBACK_ADJ = (-2.0, 6.0)                # plausible FCA+QTA+surcharges per unit when the month is unknown
ROUND_TOL = 0.01                          # 1% allowance for rounding / small unmodelled items

WARN = {
    "ptv": "A PTV fee seems to be on your bill. It was reported abolished from July 2025, so it may be disputable.",
    "duty": "Electricity duty seems to be on your bill. Sources disagree on whether it is still collected through bills; "
            "check the line on your paper bill.",
}


def _kind_params(keys, category="unprotected"):
    opu = sum((OPTIONAL[k].get("protected_per_unit", OPTIONAL[k].get("per_unit", 0)) if category == "protected" else
               0.0 if category == "lifeline" and k == "fc" else OPTIONAL[k].get("per_unit", 0)) for k in keys)
    return {"other_per_unit": opu, "duty_pct": OPTIONAL["duty"]["pct"] if "duty" in keys else 0.0,
            "other_fixed": OPTIONAL["ptv"]["fixed"] if "ptv" in keys else 0.0}


def _calc(units, prev, kw, cat, fca, qta, keys, fca_units):
    return compute_bill(units, prev, kw, cat, fca, qta, fca_units=fca_units, **_kind_params(keys, cat))


def split_bill(units, billed, prev_units=0, kw=2.0, kw_known=False, category="auto", month=None,
               fca_override=0.0, qta_override=0.0, fca_units=None) -> dict:
    units, billed, kw = float(units or 0), float(billed or 0), float(kw or 2.0)
    prev = float(prev_units or 0)
    cat = compute_bill(units, prev, kw, category)["category"]
    kw_lo, kw_hi = (kw, kw) if kw_known else (max(0.5, kw - 1), kw + 1)
    notes, warnings = [], []

    adj = lookup(month, cat) if month else None
    if fca_override or qta_override:
        mode, fca, qta = "manual", float(fca_override or 0), float(qta_override or 0)
        notes.append("Using the FCA / QTA you entered under Optional overrides.")
    elif adj:
        mode, fca, qta = "table", adj["fca"], adj["qta"]
        notes += adj["notes"]
    else:
        mode, fca, qta = "implied", 0.0, 0.0
        notes.append("This bill month is not in the FCA/QTA table, so FCA + QTA + surcharges are estimated together from "
                     "your billed amount. Pick a listed month or enter your bill's FCA/QTA for a finer split.")

    keys = []
    if mode == "implied":
        base = compute_bill(units, prev, kw, cat)["parts"]
        implied = ((billed / (1 + GST) - base["energy"] - base["fixed"]) / units) if billed and units else 0.0
        adj_c = min(max(implied, FALLBACK_ADJ[0]), FALLBACK_ADJ[1])
        fit = compute_bill(units, prev, kw, cat, other_per_unit=adj_c)
        low = compute_bill(units, prev, kw_lo, cat, other_per_unit=FALLBACK_ADJ[0])["total"]
        high = compute_bill(units, prev, kw_hi, cat, other_per_unit=FALLBACK_ADJ[1])["total"]
        fit_params = {"kw": kw, "category": cat, "fca": 0.0, "qta": 0.0, "other_per_unit": adj_c,
                      "other_fixed": 0.0, "duty_pct": 0.0}
    else:
        if billed:
            cands = []
            for n in range(len(OPTIONAL) + 1):
                for c in combinations(OPTIONAL, n):
                    r = _calc(units, prev, kw, cat, fca, qta, c, fca_units)
                    cands.append((abs(billed - r["total"]), len(c), c, r))
            _, _, keys, fit = min(cands, key=lambda x: (round(x[0], 2), x[1]))
            keys = list(keys)
        else:
            fit = _calc(units, prev, kw, cat, fca, qta, [], fca_units)
        low = _calc(units, prev, kw_lo, cat, fca, qta, [], fca_units)["total"]
        high = _calc(units, prev, kw_hi, cat, fca, qta, PLAUSIBLE, fca_units)["total"]
        fit_params = {"kw": kw, "category": cat, "fca": fca, "qta": qta, **_kind_params(keys, cat)}
        if not fca_units:
            notes.append("FCA is billed on the units of the earlier month it belongs to; this month's units are used as an "
                         "estimate. Enter the units shown on your bill's FCA line under Optional overrides for an exact match.")
    if not kw_known:
        notes.append(f"Sanctioned load assumed {kw:g} kW (range {kw_lo:g}-{kw_hi:g} kW). Tick the box in the sidebar if it is "
                     "printed on your bill.")

    unexplained = round(billed - fit["total"], 2) if billed else 0.0
    cons = round(max(0.0, billed - high * (1 + ROUND_TOL)), 2) if billed else 0.0
    likely = round(max(cons, unexplained if unexplained > ROUND_TOL * billed else 0.0), 2) if billed else 0.0
    err = abs(unexplained) / billed if billed else 0.0
    shown_keys = list(keys)
    if err <= 0.03:  # only call out a charge when it genuinely explains the bill, not just because the bill is high
        for k in keys:
            if k in WARN:
                warnings.append(WARN[k])
    elif billed and mode != "implied":
        shown_keys = [k for k in keys if k not in WARN]  # never present guessed PTV / duty lines for a poorly fitting bill
    if billed and mode != "implied" and err > 0.03:
        warnings.append(f"The bill differs from the model by {err:.1%} even after trying every optional charge: possible "
                        "overcharge, a different sanctioned load, or a charge this model does not know.")

    if mode != "implied":
        fit_params.update(_kind_params(shown_keys, cat))
    p = fit["parts"]
    comps = [("Slab energy charges", p["energy"], "energy"), ("Fixed charges", p["fixed"], "fixed")]
    if mode == "implied":
        comps.append(("FCA + QTA + surcharges (estimated together)", p["other"], "adjust"))
    else:
        comps.append((f"FCA / FPA (Rs {fca:g}/unit)", p["fca"], "adjust"))
        comps.append((f"QTA (Rs {qta:g}/unit)", p["qta"], "adjust"))
        for k in ("nj", "fc"):
            if k in shown_keys:
                rate = OPTIONAL[k].get("protected_per_unit", OPTIONAL[k]["per_unit"]) if cat == "protected" else (0.0 if cat == "lifeline" and k == "fc" else OPTIONAL[k]["per_unit"])
                comps.append((f"{OPTIONAL[k]['label']} (Rs {rate:g}/unit)", round(units * rate, 2), "surcharge"))
        if "duty" in shown_keys:
            comps.append((OPTIONAL["duty"]["label"], p["duty"], "tax"))
    comps.append((f"GST ({GST:.0%})", p["gst"], "tax"))
    if "ptv" in shown_keys:
        comps.append((OPTIONAL["ptv"]["label"], p["other_fixed"], "surcharge"))
    comps = [(l, a, k) for l, a, k in comps if abs(a) >= 0.005 or k in ("energy", "tax")]
    if billed:  # whatever the shown lines do not cover, so the table always adds up to the billed amount
        comps.append(("Unexplained difference", round(billed - sum(a for _, a, _ in comps), 2), "unexplained"))

    conf = "Indicative" if mode == "implied" else ("High" if (kw_known and err <= 0.03) else "Medium")
    return {"components": [{"label": l, "amount": round(a, 2), "kind": k} for l, a, k in comps],
            "modelled_total": fit["total"], "unexplained": unexplained, "billed": billed,
            "overcharge_conservative": cons, "overcharge_likely": likely, "low": round(low, 2), "high": round(high, 2),
            "mode": mode, "month": month, "category": cat, "fit_keys": shown_keys, "fit_error": round(err, 4),
            "confidence": conf, "warnings": warnings, "notes": notes, "fit_params": fit_params, "fit_result": fit,
            "fca_units_used": (float(fca_units) if fca_units else float(units)),
            "adjustment_status": (adj.get("status") if adj else ("manual" if mode == "manual" else "indicative")),
            "adjustment_source": (adj.get("source") if adj else "User override / combined estimate")}
