"""Official monthly FCA and quarterly QTA lookup (data lives in adjustments.json so it is easy to update)."""
from __future__ import annotations

import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "adjustments.json")
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _load() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def months() -> list:
    """Known bill months, newest first (e.g. ['2026-10', '2026-09', ...])."""
    return sorted((k for k in _load() if not k.startswith("_")), reverse=True)


def label(key: str) -> str:
    if key not in _load():
        return "Other / not listed"
    y, m = key.split("-")
    e = _load()[key]
    return f"{_MON[int(m) - 1]} {y} bill" + ("  (FCA proposed)" if e.get("status") == "proposed" else "")


def default_month() -> str:
    """Latest month whose FCA is approved (or the newest month if none is)."""
    data = _load()
    ok = [k for k in months() if data[k].get("status") == "approved"]
    return (ok or months() or ["other"])[0]


def updated() -> str:
    return _load().get("_updated", "unknown")


def lookup(key: str, category: str):
    """Effective FCA/QTA for a bill month and category, or None when the month is not in the table."""
    e = _load().get(key or "")
    if not e:
        return None
    y, m = key.split("-")
    month_name = f"{_MON[int(m) - 1]} {y}"
    notes, fca, qta = [], float(e["fca"]), float(e["qta"])
    if category in e.get("fca_exempt", []):
        notes.append(f"Your category ({category}) is exempt from this month's FCA, so it is set to 0.")
        fca = 0.0
    else:
        notes.append(f"FCA Rs {fca:g}/unit for {e['fca_for']}, billed in {month_name}.")
    if category in e.get("qta_exempt", []):
        notes.append(f"Your category ({category}) is exempt from the QTA, so it is set to 0.")
        qta = 0.0
    elif qta:
        notes.append(f"QTA Rs {qta:g}/unit ({e['qta_for']}).")
    if e.get("status") == "proposed":
        notes.append("The FCA for this month was only PROPOSED when this table was last updated. If NEPRA changed it, "
                     "enter your bill's FCA under Optional overrides.")
    notes.append(f"Source: {e['source']}.")
    return {"fca": fca, "qta": qta, "status": e.get("status", "approved"), "notes": notes}
