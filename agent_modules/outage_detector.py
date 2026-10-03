import re
from .base import Agent, Finding

SCHEDULED_MAX = {"urban": 2, "mixed": 4, "rural": 6}  # illustrative hrs/day of scheduled load-shedding


class OutageDetector(Agent):
    name = "Outage Detector"

    def run(self, case, ctx):
        text = case.get("text", "").lower()
        hours = case.get("outage_hours") or 0
        m = re.search(r"(\d+(?:\.\d+)?)\s*(ghant|hour|hr)", text)
        if m and not hours:
            hours = float(m.group(1))
        outage = hours > 0 or any(k in text for k in ["bijli ja", "light ja", "load shedding", "outage", "no power"])
        allowed = SCHEDULED_MAX.get(case.get("area_type", "urban"), 2)
        excess = max(0, hours - allowed)
        sev = "critical" if excess >= 3 else "warn" if excess > 0 else "info"
        ctx["outage_hours"], ctx["excess_hours"] = hours, excess
        msg = f"Outage detected: {hours:g}h (scheduled allowance ~{allowed}h; excess {excess:g}h)." if outage else "No outage signal found."
        return Finding(self.name, msg, sev if outage else "info", 0.7, {"hours": hours, "excess": excess, "detected": outage})
