from .base import Agent, Finding

LADDER = ["DISCO complaint center / app", "NEPRA consumer complaint", "Wafaqi Mohtasib / provincial ombudsman", "Pakistan Citizen Portal"]


class RegulationAgent(Agent):
    name = "Regulation Agent"

    def run(self, case, ctx):
        notes = ["Keep bill copy, meter photo and outage log as evidence.",
                 "Cite NEPRA Consumer Service Manual timelines; verify exact clauses with your DISCO/NEPRA before filing."]
        if ctx.get("excess_hours", 0) > 0:
            notes.append("Outage exceeds scheduled allowance: eligible for a restoration/compliance complaint.")
        ctx["escalation"] = LADDER
        return Finding(self.name, "Escalation path: " + " > ".join(LADDER), "info", 0.6, {"steps": LADDER, "notes": notes})
