"""Savings planner: slab cliffs, what-if reductions and appliance cost shares.

Pakistan's landing-slab billing means ONE extra unit can re-price ALL units, so the
biggest savings usually come from staying just below a slab boundary.
"""
from __future__ import annotations

from .tariff import PROTECTED, UNPROTECTED, compute_bill

# Typical running power in watts. Approximate: real appliances vary by model and age.
APPLIANCES = {
    "Split AC 1.5 ton (non-inverter)": 1600, "Split AC 1.5 ton (inverter)": 900, "Ceiling fan (AC motor)": 75,
    "Ceiling fan (DC / inverter)": 35, "Refrigerator (average draw)": 90, "Deep freezer (average draw)": 110,
    "LED bulb": 10, "LED TV": 80, "Washing machine": 500, "Electric iron": 1000, "Water pump (1 HP)": 750,
    "Microwave oven": 1100, "Electric geyser": 3000, "Desktop computer": 150,
}
DEFAULT_ROWS = [("Split AC 1.5 ton (inverter)", 1, 6.0), ("Ceiling fan (AC motor)", 3, 12.0),
                ("Refrigerator (average draw)", 1, 24.0), ("LED bulb", 6, 6.0), ("LED TV", 1, 4.0)]


def appliance_units(name: str, qty: float, hours_per_day: float, days: int = 30) -> float:
    return round(APPLIANCES.get(name, 0) * qty * hours_per_day * days / 1000, 1)


def _kw(**k):
    return {x: k[x] for x in ("kw", "category", "fca", "qta", "other_per_unit", "other_fixed", "duty_pct") if x in k}


def bill_for(units, prev_units=0, **k) -> float:
    return compute_bill(max(units, 0), prev_units=prev_units, **_kw(**k))["total"]


def what_if(units, reduction, prev_units=0, **k) -> dict:
    """Bill now vs bill after using ``reduction`` fewer units."""
    now = bill_for(units, prev_units, **k)
    new_units = max(units - reduction, 0)
    after = bill_for(new_units, prev_units, **k)
    return {"units_after": new_units, "bill_now": now, "bill_after": after, "saving": round(now - after, 2)}


def cliffs(units, prev_units=0, **k) -> dict:
    """Distance to the next slab boundary and the extra cost of crossing it."""
    cat = compute_bill(units, prev_units=prev_units, **_kw(**k))["category"]
    table = {"protected": PROTECTED, "unprotected": UNPROTECTED}.get(cat, UNPROTECTED)
    out = {"category": cat, "next_slab": None, "protected_cliff": None, "drop_to": None}
    cap = next((c for c, _, _ in table if units <= c), None)
    if cap not in (None, float("inf")):
        gap = int(cap - units)
        here = bill_for(units, prev_units, **k)
        past = bill_for(cap + 1, prev_units, **k)
        out["next_slab"] = {"units_left": gap, "boundary": int(cap), "bill_at_boundary": bill_for(cap, prev_units, **k),
                            "bill_just_over": past, "jump": round(past - bill_for(cap, prev_units, **k), 2),
                            "headroom_cost": round(bill_for(cap, prev_units, **k) - here, 2)}
    if cat == "unprotected" and units > 200:
        # staying at 200 units would need the protected category; show the potential benefit only if eligible
        cut = int(units - 200)
        out["protected_cliff"] = {"units_to_cut": cut, "bill_at_200_protected":
                                  bill_for(200, 0, **{**k, "category": "Protected"}),
                                  "note": "Only applies if you can stay at 200 units or less for six months in a row."}
    # largest boundary below the current units: where a reduction would drop a whole slab
    lower = [c for c, _, _ in table if c < units and c != float("inf")]
    if lower:
        b = max(lower)
        out["drop_to"] = {"boundary": int(b), "units_to_cut": int(units - b),
                          "saving": round(bill_for(units, prev_units, **k) - bill_for(b, prev_units, **k), 2)}
    return out


def appliance_costs(rows, actual_units, prev_units=0, **k) -> list:
    """Per appliance: monthly units and the money saved by running it 1 hour/day less."""
    out = []
    for name, qty, hrs in rows:
        u = appliance_units(name, qty, hrs)
        one_hr = appliance_units(name, qty, 1.0)
        out.append({"name": name, "units": u,
                    "saving_per_hour_less": what_if(actual_units, one_hr, prev_units, **k)["saving"] if actual_units else 0})
    return out
