import sys
import types

from agents import CrewSession, Orchestrator, run_crew_case
import ui_components as ui
from ui_theme import THEME, css

CASE = {"text": "Bijli 4 ghantay se ja rahi hai aur bill bhi bohat zyada aya hai", "city": "Lahore",
        "units": 320, "billed": 14000, "prev_units": 180, "area_type": "urban", "temp_c": 42}


def test_session_runs_dependencies_in_order():
    s = CrewSession(dict(CASE))
    s.run_step("Weather / Environment Agent")  # needs Location first
    assert [t["agent"] for t in s.trace][:2] == ["Location Agent", "Bill Auditor"]
    s.finish()
    assert len(s.trace) == 8 and len(set(t["agent"] for t in s.trace)) == 8


def test_fallback_without_key(monkeypatch=None):
    r = run_crew_case(dict(CASE), api_key=None)
    assert r["mode"] == "rules" and r["warning"] and len(r["trace"]) == 8
    assert Orchestrator.approve(r, True)["status"] == "APPROVED"


def _install_fake_crewai(fail=False):
    m = types.ModuleType("crewai")
    t = types.ModuleType("crewai.tools")
    t.tool = lambda name: (lambda fn: types.SimpleNamespace(name=name, func=fn))

    class Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class Crew(Obj):
        def kickoff(self):
            if fail:
                raise RuntimeError("quota")
            for a in self.agents:  # pretend the LLM calls each tool once
                for tl in (getattr(a, "tools", None) or []):
                    tl.func("go")
            return types.SimpleNamespace(raw="Briefing text. Nothing is filed until you approve.")

    m.Agent, m.Task, m.Crew, m.LLM = Obj, Obj, Crew, Obj
    m.Process = types.SimpleNamespace(sequential="sequential")
    m.tools = t
    sys.modules["crewai"], sys.modules["crewai.tools"] = m, t


def _remove_fake():
    sys.modules.pop("crewai", None)
    sys.modules.pop("crewai.tools", None)


def test_crew_mode_with_stub():
    _install_fake_crewai()
    try:
        r = run_crew_case(dict(CASE), api_key="x")
    finally:
        _remove_fake()
    assert r["mode"] == "crewai" and "Nothing is filed" in r["crew_report"]
    assert len(r["trace"]) == 8 and r["status"] == "PENDING_APPROVAL"
    assert r["ctx"]["excess_hours"] == 2 and "LESCO" in r["ctx"]["draft"]["en"]


def test_crew_failure_falls_back():
    _install_fake_crewai(fail=True)
    try:
        r = run_crew_case(dict(CASE), api_key="x")
    finally:
        _remove_fake()
    assert r["mode"] == "rules" and "failed" in r["warning"] and len(r["trace"]) == 8


def test_ui_components_render():
    r = Orchestrator().investigate(dict(CASE))
    assert "gg-kpi" in ui.kpis(r, CASE) and "gg-step" in ui.stepper({"Bill Auditor"})
    assert all("gg-agent" in ui.agent_card(t) for t in r["trace"])
    assert "gg-gauge" in ui.gauge(0.7) and "gg-bar" in ui.confidence_bars(r["trace"])
    assert "gg-hero" in ui.hero("x", True) and "gg-brief" in ui.briefing("hi")
    assert "--a1" in css(THEME)


def test_groq_routes_never_use_dead_model_or_custom_openai():
    _install_fake_crewai()
    seen = []
    orig = sys.modules["crewai"].LLM
    sys.modules["crewai"].LLM = lambda **kw: (seen.append(kw), orig(**kw))[1]
    try:
        r = run_crew_case(dict(CASE), api_key="gsk_test", model="groq/llama-3.3-70b-versatile")
    finally:
        _remove_fake()
    assert r["mode"] == "crewai" and r["llm_route"] in ("litellm", "openai-compatible")
    kw = seen[0]
    assert "custom_openai" not in kw and kw["api_key"] == "gsk_test"
    assert "llama-3.3" not in kw["model"], kw  # retired model is swapped for gpt-oss-120b
    if kw["model"].startswith("groq/"):
        assert kw["model"] == "groq/openai/gpt-oss-120b"
    else:
        assert kw["model"] == "openai/gpt-oss-120b" and kw["provider"] == "openai" and kw["base_url"].endswith("/openai/v1")


def test_crew_failure_uses_direct_groq_then_rules():
    from agent_modules import llm_client
    _install_fake_crewai(fail=True)
    ok = lambda url, headers=None, json=None, timeout=0: types.SimpleNamespace(
        status_code=200, raise_for_status=lambda: None,
        json=lambda: {"choices": [{"message": {"content": "Direct briefing. Nothing is filed until you approve."}}]})
    orig = llm_client.chat.__defaults__
    import agent_modules.llm_features as lf
    real = lf.chat
    lf.chat = lambda *a, **k: real(*a, **{**k, "post": ok})
    try:
        r = run_crew_case(dict(CASE), api_key="gsk")
    finally:
        lf.chat = real
        _remove_fake()
    assert r["mode"] == "groq-direct" and "Direct briefing" in r["crew_report"] and "CrewAI failed" in r["warning"]
