import time
from .base import Finding
from .bill_auditor import BillAuditor
from .outage_detector import OutageDetector
from .location_agent import LocationAgent
from .regulation_agent import RegulationAgent
from .weather_agent import WeatherAgent
from .grid_analyst import GridAnalyst
from .evidence_agent import EvidenceAgent
from .action_agent import ActionAgent

PIPELINE = [LocationAgent, BillAuditor, OutageDetector, WeatherAgent, RegulationAgent, GridAnalyst, EvidenceAgent, ActionAgent]


class Orchestrator:
    """Runs specialist agents in order, isolates failures, gates filing behind human approval."""

    def __init__(self):
        self.agents = [a() for a in PIPELINE]

    def investigate(self, case: dict, on_step=None):
        findings, trace = [], []
        ctx = {"findings": findings}
        for ag in self.agents:
            t0 = time.time()
            try:
                f = ag.run(case, ctx)
            except Exception as e:  # one failing agent must not kill the case
                f = Finding(ag.name, f"Agent error: {e}", "warn", 0.0)
            findings.append(f)
            if ag.name.startswith("Investigation"):
                ctx["evidence"] = f.data.get("bullets", [])
            trace.append({"agent": ag.name, "ms": int((time.time() - t0) * 1000), "finding": f})
            if on_step:
                on_step(trace[-1])
        return {"ctx": ctx, "trace": trace, "status": "PENDING_APPROVAL"}

    @staticmethod
    def approve(result, approved, edited_text=None):
        result["status"] = "APPROVED" if approved else "REJECTED"
        if approved and edited_text:
            result["ctx"]["draft"]["en"] = edited_text
        return result
