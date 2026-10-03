# ⚡ GridGuard AI
Multi-agent incident response for Pakistan electricity outages and billing disputes, now powered by **CrewAI** with a premium tabbed dashboard.

## Architecture
Orchestrator → Location, Bill Auditor, Outage Detector, Weather, Regulation, Grid Analyst → Evidence → Action → Human Approval.

* `agent_modules/` : deterministic specialist agents (source of truth for numbers). `agents.py` is a compatibility facade.
* `agent_modules/crew_runner.py` : **CrewAI layer**. Each specialist is a real `crewai.Agent` with its own tool, tasks run in a sequential `crewai.Crew`, and a *Case Officer* agent writes the briefing. Falls back to the rules engine if CrewAI, the API key or the LLM is unavailable.
* `ui_theme.py` / `ui_components.py` : a single premium dark theme (Ocean Glass, edit `THEME` in `ui_theme.py`), KPI cards, pipeline stepper, gauge and bar charts.
* `app.py` : tabs 🚀 Investigate · 🕵️ Agent Trace · 📊 Analytics · 📝 Complaint & Approval · 🧠 Crew Briefing · ℹ️ About.

## Bill Center, Savings Planner and accuracy
* **Official portal link** per city (PITC `bill.pitc.com.pk` for WAPDA DISCOs, `ke.com.pk` for K-Electric) with a reference-number check. GridGuard never scrapes or logs in to those portals.
* **Bill scanner**: photo/screenshot (Groq vision `qwen/qwen3.8-27b`) or text PDF (Groq text, offline regex fallback). Values are suggestions you confirm, then one click fills the sidebar.
* **Expected bill** (`agent_modules/tariff.py`): landing-slab energy charge + fixed charge per kW + FCA + QTA + duty + GST, itemised, with a line-by-line check against the scanned bill.
* **Savings Planner**: slab-cliff alerts, what-if usage cut, appliance cost shares and "run X 1 hour less" savings.
* **Audit report** download (reference number masked) and an overcharge estimate that flows into the complaint draft.

**Accuracy honesty:** no calculator can promise 99% from units alone. The slab table comes from public sources that disagree in places, and FCA/QTA change monthly. Units only gives roughly +/-12%; adding FCA and QTA from your bill gives roughly +/-3%. Use the *Accuracy back-test* in the Bill Center with your own past bills to measure the real error, and edit `tariff.py` when NEPRA notifies new rates.

## Auto-split (units + billed amount only)
Enter **units** and the **billed amount**; GridGuard splits the bill into slab energy charge, fixed charge, monthly **FCA**,
quarterly **QTA**, surcharges / duty and GST, with an *unexplained difference* so the lines always add up to your bill.
* FCA and QTA are **looked up automatically** for the chosen bill month from `agent_modules/adjustments.json` (Jun-Oct 2026, from NEPRA decisions as reported in the press; the October FCA is only *proposed*). Add new months there each month.
* Protected / lifeline exemptions from a month's FCA are applied (for example protected consumers were exempt from the August 2026 FCA).
* Sources disagree on which surcharges and duties are still on bills, so the app tries every combination (Neelum-Jhelum, financing-cost, electricity duty, PTV fee) and keeps the **best fit**. These are inferred, not read from the bill.
* **Two overcharge numbers:** *likely* = billed minus best fit; *conservative* = billed minus the highest plausible bill (all optional charges on, load +1 kW). Complaints use the conservative one.
* Months not in the table fall back to an *indicative* combined estimate of FCA + QTA + surcharges.

## Dashboard visibility (v10)
The Bill Intelligence Dashboard is intentionally visible above the tabs whenever units are entered. It shows the billed amount, best-fit amount, plausible range, conservative gap, selected month, FCA/QTA rates, category, and every reconciliation line with amount/share. Bill Center repeats the evidence trail and adds PDF/TXT/CSV downloads.

### Evidence labels
* **CALCULATED**: tariff/slab, fixed charges and GST from the local tariff engine.
* **LOOKUP**: FCA/QTA selected by bill month or explicitly overridden by the user.
* **INFERRED**: optional surcharge/duty combinations selected only when they explain the billed amount; not proof of a printed bill line.
* **RECONCILIATION**: unexplained difference is the arithmetic remainder required to make the displayed lines equal the billed total.

### Validation
A fresh unzip now supports plain `pytest` without setting `PYTHONPATH`; the packaging includes `pytest.ini`. The test suite validates the split engine, exemptions, inference guardrails, OCR adapters, reports and dashboard renderers. Browser/Groq live calls still require an actual Streamlit/Groq environment.

## Run
    pip install -r requirements.txt     # Python 3.10 - 3.13 (CrewAI requirement)
    streamlit run app.py
    pytest

## Using CrewAI with Groq
The app runs the CrewAI crew on **Groq via its OpenAI-compatible API** (`openai/gpt-oss-120b` at `https://api.groq.com/openai/v1`). Paste your key in the sidebar
(🔑 GROQ_API_KEY) or set it as an env var / Streamlit secret named `GROQ_API_KEY`. Get a key at console.groq.com.
Without a key (or if CrewAI/Groq fails) the app falls back to the deterministic rules engine and shows a warning.

## Deploy
Push to GitHub → share.streamlit.io → main file `app.py`. Add `GROQ_API_KEY` under *Secrets*. Use a Python 3.11/3.12 runtime.

## Notes
Tariff slabs (`bill_auditor.py`) and scheduled-outage allowances (`outage_detector.py`) are ILLUSTRATIVE; update from NEPRA/DISCO notifications. Nothing is filed without human approval.


## Validation artifact
See `VALIDATION_REPORT.md` for the fresh-unzip test result, environment limitation, and regulatory-data re-check notes.
