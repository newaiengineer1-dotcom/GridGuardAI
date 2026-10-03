from agents import Orchestrator


def test_pipeline_end_to_end():
    case = {"text": "Bijli 4 ghantay se ja rahi hai aur bill bhi bohat zyada aya hai", "city": "Lahore",
            "units": 320, "billed": 14000, "prev_units": 180, "area_type": "urban", "temp_c": 42}
    r = Orchestrator().investigate(case)
    assert r["status"] == "PENDING_APPROVAL" and len(r["trace"]) == 8
    assert r["ctx"]["excess_hours"] == 2 and "LESCO" in r["ctx"]["draft"]["en"]
    assert Orchestrator.approve(r, True)["status"] == "APPROVED"
