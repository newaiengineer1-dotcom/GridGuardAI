from agents import Orchestrator
from agent_modules import workflow as wf, value_engineering as ve, llm_features as lf
import zipfile, io

CASE = {"text": "Bijli 6 ghantay se ja rahi hai", "city": "Lahore", "units": 320, "billed": 14000, "prev_units": 180,
        "area_type": "urban", "temp_c": 43}


def test_triage_plan_ics_zip():
    r = Orchestrator().investigate(dict(CASE)); ctx = r["ctx"]
    t = wf.triage(CASE, ctx)
    assert t["priority"] in ("P1", "P2") and t["sla_hours"] <= 72 and t["ladder"]
    plan = wf.followup_plan(t["priority"])
    assert [p["day"] for p in plan] == sorted(p["day"] for p in plan)
    ics = wf.to_ics(plan)
    assert ics.count("BEGIN:VEVENT") == len(plan) and ics.startswith("BEGIN:VCALENDAR")
    z = zipfile.ZipFile(io.BytesIO(wf.case_file_zip(ctx, CASE, t, plan)))
    assert "04_followups.ics" in z.namelist() and "LESCO" in z.read("01_complaint_en.txt").decode()


def test_outage_log_and_value_engineering():
    assert wf.outage_log_summary([{"hours": 5}] * 6)["over_days"] == 6
    v = ve.opportunities(320, 180, overcharge=2000)
    assert v["actions"][0]["monthly_saving"] >= v["actions"][-1]["monthly_saving"] and v["solar"]["system_kw"] > 0


def test_llm_features_without_key_degrade():
    assert not lf.polish_complaint("x", None)["ok"]
    r = Orchestrator().investigate(dict(CASE))
    assert "approve" in lf.offline_briefing(r["ctx"], CASE)
