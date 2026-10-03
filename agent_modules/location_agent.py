from .base import Agent, Finding

CITIES = {  # city: (DISCO, lat, lon)
    "karachi": ("K-Electric", 24.86, 67.01), "lahore": ("LESCO", 31.55, 74.34),
    "islamabad": ("IESCO", 33.68, 73.05), "rawalpindi": ("IESCO", 33.60, 73.04),
    "faisalabad": ("FESCO", 31.42, 73.08), "multan": ("MEPCO", 30.20, 71.47),
    "gujranwala": ("GEPCO", 32.16, 74.19), "peshawar": ("PESCO", 34.02, 71.52),
    "quetta": ("QESCO", 30.18, 66.99), "hyderabad": ("HESCO", 25.39, 68.37),
    "sukkur": ("SEPCO", 27.70, 68.86),
}


class LocationAgent(Agent):
    name = "Location Agent"

    def run(self, case, ctx):
        city = case.get("city", "").strip().lower()
        if city not in CITIES:
            return Finding(self.name, f"City '{city}' not mapped; using manual DISCO.", "warn", 0.3)
        disco, lat, lon = CITIES[city]
        ctx.update(disco=disco, lat=lat, lon=lon)
        return Finding(self.name, f"{city.title()} is served by {disco}.", "info", 0.9, {"disco": disco, "lat": lat, "lon": lon})
