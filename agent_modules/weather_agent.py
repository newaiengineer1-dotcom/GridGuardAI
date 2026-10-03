from .base import Agent, Finding


class WeatherAgent(Agent):
    name = "Weather / Environment Agent"

    def run(self, case, ctx):
        temp, wind, src = case.get("temp_c"), case.get("wind_kmh", 0), "manual/offline"
        try:  # live Open-Meteo (no key); falls back to manual inputs when offline
            import requests
            cur = requests.get("https://api.open-meteo.com/v1/forecast", timeout=4, params={
                "latitude": ctx["lat"], "longitude": ctx["lon"], "current": "temperature_2m,wind_speed_10m"}).json()["current"]
            temp, wind, src = cur["temperature_2m"], cur["wind_speed_10m"], "live"
        except Exception:
            pass
        ctx["temp_c"], ctx["wind_kmh"] = temp, wind
        hot, windy = (temp or 0) >= 40, (wind or 0) >= 40
        msg = f"Temp {temp}C, wind {wind} km/h ({src})." + (" Heat stress likely." if hot else "") + (" Storm-level wind." if windy else "")
        return Finding(self.name, msg, "warn" if hot or windy else "info", 0.6 if src == "live" else 0.4, {"hot": hot, "windy": windy})
