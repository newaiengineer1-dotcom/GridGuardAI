from .base import Agent, Finding


class EvidenceAgent(Agent):
    name = "Investigation / Evidence Agent"

    def run(self, case, ctx):
        prior = ctx.get("findings", [])
        w = {"critical": 1.0, "warn": 0.6, "info": 0.2}
        score = round(min(1.0, sum(w[f.severity] * f.confidence for f in prior) / 2.5), 2)
        ctx["case_strength"] = score
        bullets = [f"[{f.agent}] {f.summary}" for f in prior if f.severity != "info"]
        verdict = "Strong" if score >= 0.6 else "Moderate" if score >= 0.35 else "Weak"
        return Finding(self.name, f"Case strength: {verdict} ({score:.0%}).", "info" if verdict == "Weak" else "warn",
                       score, {"bullets": bullets, "score": score, "verdict": verdict})
