from .base import Agent, Finding


class GridAnalyst(Agent):
    name = "Grid Analyst"

    def run(self, case, ctx):
        ex, t, w = ctx.get("excess_hours", 0), ctx.get("temp_c") or 0, ctx.get("wind_kmh") or 0
        h = [("Scheduled load-shedding / high-loss feeder", 0.35 + (0.1 if ex == 0 else 0)),
             ("Transformer/feeder overload (heat-driven demand)", 0.25 + (0.3 if t >= 40 else 0) + (0.1 if ex > 0 else 0)),
             ("Weather-related line fault", 0.1 + (0.5 if w >= 40 else 0)),
             ("Unannounced local fault (needs field repair)", 0.15 + (0.25 if ex >= 3 else 0))]
        tot = sum(s for _, s in h)
        ranked = sorted(((n, round(s / tot, 2)) for n, s in h), key=lambda x: -x[1])
        return Finding(self.name, f"Most likely cause: {ranked[0][0]} ({ranked[0][1]:.0%}).", "info", ranked[0][1], {"ranked": ranked})
