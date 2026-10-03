"""Value engineering: rank the actions that save the consumer the most money, with explicit assumptions."""
from __future__ import annotations

from .planner import bill_for, what_if, cliffs

# ILLUSTRATIVE planning assumptions - shown to the user and editable in the UI.
SOLAR_KWH_PER_KW_MONTH = 130
SOLAR_COST_PER_KW = 130_000  # Rs, installed (assumption; get local quotes)


def solar_option(units: float, rate_per_unit: float, offset_share: float = 0.7,
                 cost_per_kw: float = SOLAR_COST_PER_KW, kwh_per_kw: float = SOLAR_KWH_PER_KW_MONTH) -> dict:
    kw = round(units * offset_share / kwh_per_kw, 1)
    monthly = round(units * offset_share * rate_per_unit)
    cost = round(kw * cost_per_kw)
    return {"system_kw": kw, "cost": cost, "monthly_saving": monthly,
            "payback_years": round(cost / (monthly * 12), 1) if monthly else None}


def opportunities(units: float, prev_units: float = 0, overcharge: float = 0.0, outage_hours_month: float = 0.0, **k) -> dict:
    """Ranked actions with monthly Rs impact. ``overcharge`` is the unexplained amount from the bill split."""
    now = bill_for(units, prev_units, **k)
    avg = now / units if units else 0
    acts = []
    if overcharge > 0:
        acts.append({"action": "Dispute the unexplained part of the bill", "monthly_saving": round(overcharge), "effort": "Low",
                     "confidence": "Medium", "how": "Use the complaint draft; attach bill and meter photo."})
    c = cliffs(units, prev_units, **k)
    d = c.get("drop_to")
    if d and d["saving"] > 0:
        acts.append({"action": f"Cut {d['units_to_cut']} units to drop below the {d['boundary']}-unit slab", "monthly_saving": round(d["saving"]),
                     "effort": "Medium", "confidence": "High", "how": "Shift AC / geyser / iron use; inverter AC if possible."})
    for pct in (10, 20):
        w = what_if(units, units * pct / 100, prev_units, **k)
        acts.append({"action": f"Use {pct}% fewer units", "monthly_saving": round(w["saving"]), "effort": "Medium" if pct == 10 else "High",
                     "confidence": "High", "how": "Fans/LED/AC set-point 26C, standby off."})
    s = solar_option(units, avg)
    if s["payback_years"]:
        acts.append({"action": f"Rooftop solar ~{s['system_kw']} kW (covers ~70%)", "monthly_saving": s["monthly_saving"], "effort": "High",
                     "confidence": "Medium", "how": f"Cost ~Rs {s['cost']:,}; payback ~{s['payback_years']} yrs (assumption-based)."})
    acts.sort(key=lambda a: -a["monthly_saving"])
    return {"bill_now": round(now), "avg_rate": round(avg, 1), "actions": acts, "solar": s,
            "annual_potential": round(sum(a["monthly_saving"] for a in acts[:2]) * 12)}
