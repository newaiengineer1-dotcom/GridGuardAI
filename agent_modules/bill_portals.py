"""Where to open the official online bill for each DISCO (Option 1).

GridGuard does NOT scrape these portals. It sends the user to the official page and the
user copies units / amount back (or scans the bill photo). Links are fixed here on purpose,
so a user is never sent to a look-alike site.
"""
from __future__ import annotations

import re

PITC_URL = "https://bill.pitc.com.pk"
KE_URL = "https://www.ke.com.pk"
WAPDA_DISCOS = {"LESCO", "GEPCO", "FESCO", "IESCO", "MEPCO", "PESCO", "HESCO", "SEPCO", "QESCO", "TESCO"}


def portal_for(disco: str) -> dict:
    d = (disco or "").strip().upper()
    if d == "K-ELECTRIC":
        return {"name": "K-Electric", "url": KE_URL, "id_label": "K-Electric account number",
                "digits": None, "family": "ke",
                "steps": ["Open ke.com.pk (or the K-Electric app).", "Go to the View / Pay Bill section.",
                          "Enter your account number exactly as printed on your bill.",
                          "Note the units consumed and the payable amount, then copy them into GridGuard."]}
    name = d if d in WAPDA_DISCOS else "your DISCO"
    return {"name": f"{name} (PITC portal)" if d in WAPDA_DISCOS else "PITC bill portal", "url": PITC_URL,
            "id_label": "14-digit reference number", "digits": 14, "family": "pitc",
            "steps": [f"Open bill.pitc.com.pk (it serves the WAPDA DISCOs).",
                      f"Choose {name} and enter your 14-digit reference number from the top of your bill.",
                      "Note the units consumed and the payable amount, then copy them into GridGuard.",
                      "Or download/photograph the bill and scan it in the next step."]}


def check_consumer_no(disco: str, number: str):
    """Return (ok, message). ok is None when nothing can be checked."""
    n = (number or "").strip()
    if not n:
        return None, ""
    info = portal_for(disco)
    if info["digits"]:
        digits = re.sub(r"\D", "", n)
        if len(digits) == info["digits"]:
            return True, f"Looks like a valid {info['digits']}-digit reference number."
        return False, (f"{info['name']} reference numbers are normally {info['digits']} digits; "
                       f"you entered {len(digits)}. Check it against your bill.")
    return None, "K-Electric account numbers vary in format; copy it exactly from your bill."
