from .base import Agent, Finding
from .bill_split import split_bill
from .tariff import compute_bill, expected_bill  # noqa: F401  (expected_bill kept for compatibility)


class BillAuditor(Agent):
    """Splits the bill into slab, fixed, FCA, QTA, surcharges and taxes from units + amount, then looks for overcharges."""

    name = "Bill Auditor"

    def run(self, case, ctx):
        u, billed, prev = case.get("units", 0), case.get("billed", 0), case.get("prev_units", 0)
        if not u or not billed:
            return Finding(self.name, "No bill data supplied; audit skipped.", "info", 0.2)
        sp = split_bill(u, billed, prev, case.get("sanctioned_kw", 2.0), case.get("kw_known", False),
                        case.get("consumer_type", "auto"), case.get("bill_month"), case.get("fca", 0.0),
                        case.get("qta", 0.0), case.get("fca_units"))
        exp, cons, likely = sp["modelled_total"], sp["overcharge_conservative"], sp["overcharge_likely"]
        ctx["expected_bill"], ctx["overcharge_est"], ctx["overcharge_likely"] = exp, cons, likely
        var = (billed - exp) / exp if exp else 0.0
        flags = []
        if cons > 0:
            flags.append(f"Billed Rs {billed:,.0f} is Rs {cons:,.0f} above even the highest plausible bill (Rs {sp['high']:,.0f}); "
                         f"likely overcharge about Rs {likely:,.0f}.")
        elif likely > 0 and sp["mode"] != "implied":
            flags.append(f"Billed Rs {billed:,.0f} is about Rs {likely:,.0f} above the best-fit bill (Rs {exp:,.0f}); "
                         "this may be a charge the model does not know. Check each line.")
        flags += sp["warnings"]
        if prev and u > prev * 1.5:
            flags.append(f"Units jumped {u/prev - 1:.0%} vs last month ({prev:.0f} to {u:.0f}); check meter reading / estimated billing.")
        if u > 200 and prev and prev <= 200:
            flags.append("Crossed 200 units: protected-consumer status and slab rate may have changed.")
        sev = "critical" if cons > 0.10 * billed else "warn" if flags else "info"
        msg = " ".join(flags) or (f"Bill is consistent with the tariff: best-fit Rs {exp:,.0f}, within "
                                  f"Rs {sp['low']:,.0f} - Rs {sp['high']:,.0f}.")
        conf = {"High": 0.85, "Medium": 0.7, "Indicative": 0.55}[sp["confidence"]] + (0.05 if flags else 0)
        return Finding(self.name, msg, sev, round(conf, 2),
                       {"expected": exp, "variance": round(var, 3), "flags": flags, "category": sp["category"],
                        "components": sp["components"], "mode": sp["mode"], "confidence": sp["confidence"],
                        "likely_range": [sp["low"], sp["high"]], "assumptions": sp["notes"],
                        "overcharge_est": cons, "overcharge_likely": likely})
