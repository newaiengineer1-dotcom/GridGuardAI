"""Read a bill photo / PDF into structured fields (Option 2), powered by Groq.

* images (png / jpg)  -> Groq vision model, JSON output
* PDFs with a text layer -> text is extracted (pypdf) and parsed by Groq text model,
  or by a regex parser when no key is available / Groq fails
Everything returned is a SUGGESTION: the user reviews the values before using them.
"""
from __future__ import annotations

import base64
import io
import json
import re

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
from .llm_client import VISION_MODELS, TEXT_MODELS
GROQ_VISION_MODEL = VISION_MODELS[0]
GROQ_TEXT_MODEL = TEXT_MODELS[0]

FIELD_LABELS = {
    "reference_no": "Reference no.", "consumer_name": "Consumer name", "disco": "DISCO", "bill_month": "Bill month",
    "due_date": "Due date", "units": "Units consumed", "previous_units": "Previous units", "current_bill": "Payable (Rs)",
    "energy_charges": "Energy charges (Rs)", "fixed_charges": "Fixed charges (Rs)", "fca_amount": "FCA / FPA (Rs)",
    "qta_amount": "QTA (Rs)", "gst_amount": "GST (Rs)", "duty_amount": "Electricity duty (Rs)",
    "sanctioned_load_kw": "Sanctioned load (kW)", "tariff": "Tariff", "meter_no": "Meter no.",
}
NUMERIC = {"units", "previous_units", "current_bill", "energy_charges", "fixed_charges", "fca_amount",
           "qta_amount", "gst_amount", "duty_amount", "sanctioned_load_kw"}

PROMPT = (
    "This is a Pakistani electricity bill (a WAPDA DISCO such as LESCO/IESCO/GEPCO/FESCO/MEPCO, or K-Electric). "
    "Read it and return ONLY a JSON object with exactly these keys: " + ", ".join(FIELD_LABELS) + ". "
    "Rules: numbers must be plain numbers with no commas or currency text; use null when a value is not visible; "
    "never guess. 'units' = units consumed in this billing month. 'current_bill' = amount payable within the due date "
    "(not arrears, not the late-payment amount). Amount fields are in Rupees. 'reference_no' = the reference/account number."
)


# ------------------------------------------------------------------ helpers
def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    if s in ("", "-", ".", "-."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def normalize(raw: dict) -> dict:
    """Clean raw model/regex output into typed fields + a list of issues for the user."""
    fields, issues = {}, []
    for k in FIELD_LABELS:
        v = (raw or {}).get(k)
        if k in NUMERIC:
            v = _num(v)
        elif v is not None:
            v = str(v).strip() or None
        fields[k] = v
    if fields["reference_no"]:
        fields["reference_no"] = re.sub(r"[^\dA-Za-z]", "", fields["reference_no"])
        digits = re.sub(r"\D", "", fields["reference_no"])
        if len(digits) != 14:
            issues.append(f"Reference number has {len(digits)} digits (WAPDA DISCO references are normally 14). Check it.")
    u, bill = fields["units"], fields["current_bill"]
    if u is not None and not 0 < u <= 20000:
        issues.append("Units look unrealistic; please check.")
        fields["units"] = None
    if bill is not None and bill <= 0:
        issues.append("Payable amount is not positive; please check.")
        fields["current_bill"] = None
    if fields["energy_charges"] and fields["units"]:
        implied = fields["energy_charges"] / fields["units"]
        if not 3 <= implied <= 60:
            issues.append(f"Energy charges imply Rs {implied:.1f}/unit, which looks odd. Check units and energy charges.")
    for need, label in (("units", "units consumed"), ("current_bill", "payable amount")):
        if fields[need] is None:
            issues.append(f"Could not read {label}; enter it manually.")
    found = sum(fields[k] is not None for k in ("units", "current_bill", "reference_no"))
    return {"fields": fields, "issues": issues, "confidence": round(found / 3, 2)}


def case_values(fields: dict) -> dict:
    """Map scanned fields to sidebar values (typed for the Streamlit widgets)."""
    out, u = {}, fields.get("units")
    if u:
        out["units"] = int(round(u))
    if fields.get("current_bill"):
        out["billed"] = int(round(fields["current_bill"]))
    if fields.get("reference_no"):
        out["consumer_no"] = fields["reference_no"]
    if fields.get("sanctioned_load_kw"):
        out["sanctioned_kw"] = float(min(max(fields["sanctioned_load_kw"], 0.5), 50.0))
    if u and fields.get("fca_amount") is not None:
        out["fca"] = round(max(min(fields["fca_amount"] / u, 50.0), -50.0), 2)
    if u and fields.get("qta_amount") is not None:
        out["qta"] = round(max(min(fields["qta_amount"] / u, 50.0), -50.0), 2)
    return out


def parse_bill_text(text: str) -> dict:
    """Offline regex parser for text-layer PDFs. Best effort; always review the result."""
    t = re.sub(r"[ \t]+", " ", text or "")
    n = r"(-?[\d,]+(?:\.\d+)?)"
    gap = r"[^\d\n\-]{0,18}"

    def grab(*pats):
        for p in pats:
            m = re.search(p, t, re.I)
            if m:
                return m.group(1)
        return None

    raw = {
        "reference_no": grab(r"\b(\d{2}\s?\d{5}\s?\d{7})\s?[A-Z]?\b", r"\b(\d{14})\b"),
        "units": grab(r"units?\s*consumed" + gap + n, r"consumed\s*units?" + gap + n),
        "current_bill": grab(r"payable\s*within\s*due\s*date" + gap + n, r"current\s*bill" + gap + n,
                             r"total\s*(?:amount|bill)" + gap + n),
        "energy_charges": grab(r"(?:cost\s*of\s*electricity|energy\s*charges?)" + gap + n),
        "fixed_charges": grab(r"fixed\s*charges?" + gap + n),
        "fca_amount": grab(r"(?:\bFCA\b|\bFPA\b|fuel\s*(?:charges|price)\s*adj\w*)" + gap + n),
        "qta_amount": grab(r"\bQTA\b" + gap + n, r"quarterly\s*tariff\s*adj\w*" + gap + n),
        "gst_amount": grab(r"(?:\bGST\b|sales\s*tax)" + gap + n),
        "duty_amount": grab(r"electricity\s*duty" + gap + n),
        "sanctioned_load_kw": grab(r"(?:sanctioned\s*)?load" + gap + n + r"\s*kw"),
        "bill_month": grab(r"bill\s*month" + r"[^\w]{0,5}([A-Za-z]{3}\s?-?\s?\d{2,4})"),
    }
    return raw


def _prep_image(data: bytes, filename: str):
    """Downscale large photos so the request stays small; fall back to the raw bytes."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "jpg"
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((1800, 1800))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return data, "image/png" if ext == "png" else "image/jpeg"


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:3])
    except Exception:
        return ""


def _json_from(content: str) -> dict:
    s = (content or "").strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.M).strip()
    a, b = s.find("{"), s.rfind("}")
    return json.loads(s[a:b + 1])


def _groq(messages, model, key, post, timeout):
    r = post(GROQ_URL, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=timeout,
             json={"model": model, "messages": messages, "temperature": 0, "max_tokens": 900,
                   "response_format": {"type": "json_object"}})
    r.raise_for_status()
    return _json_from(r.json()["choices"][0]["message"]["content"])


# ------------------------------------------------------------------ public API
def extract_bill(data: bytes, filename: str, api_key: str | None = None, timeout: int = 60, post=None) -> dict:
    """Return {ok, method, fields, issues, confidence, warning, raw_text}. ``post`` is injectable for tests."""
    if post is None:
        import requests
        post = requests.post
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    res = {"ok": False, "method": "", "fields": {k: None for k in FIELD_LABELS}, "issues": [], "confidence": 0.0,
           "warning": "", "raw_text": ""}

    def done(raw, method, warning=""):
        res.update(normalize(raw))
        res.update(ok=True, method=method, warning=warning)
        return res

    if ext == "pdf":
        text = _pdf_text(data)
        res["raw_text"] = text[:4000]
        if len(text.strip()) < 40:
            res["warning"] = "This PDF has no readable text (it is probably a scan). Upload a photo/screenshot (PNG/JPG) instead."
            return res
        if api_key:
            try:
                msgs = [{"role": "user", "content": PROMPT + "\n\nBILL TEXT:\n" + text[:6000]}]
                return done(_groq(msgs, GROQ_TEXT_MODEL, api_key, post, timeout), "groq-text")
            except Exception as e:
                return done(parse_bill_text(text), "regex", f"Groq failed ({type(e).__name__}); used the offline parser. Review carefully.")
        return done(parse_bill_text(text), "regex", "No GROQ_API_KEY: used the offline parser. Review carefully.")

    if ext not in ("png", "jpg", "jpeg"):
        res["warning"] = "Unsupported file type. Upload PNG, JPG or a text PDF."
        return res
    if not api_key:
        res["warning"] = "Reading a bill photo needs your GROQ_API_KEY (add it in the sidebar)."
        return res
    img, mime = _prep_image(data, filename)
    url = f"data:{mime};base64,{base64.b64encode(img).decode()}"
    msgs = [{"role": "user", "content": [{"type": "text", "text": PROMPT},
                                          {"type": "image_url", "image_url": {"url": url}}]}]
    try:
        return done(_groq(msgs, GROQ_VISION_MODEL, api_key, post, timeout), "groq-vision")
    except Exception as e:
        res["warning"] = f"Groq could not read the image ({type(e).__name__}: {str(e)[:120]}). Enter the values manually."
        return res
