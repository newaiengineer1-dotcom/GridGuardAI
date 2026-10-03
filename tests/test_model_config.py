from pathlib import Path
from agent_modules.llm_client import clean_model, chat, TEXT_MODELS, VISION_MODELS

ROOT = Path(__file__).resolve().parents[1]


def test_retired_models_are_mapped():
    for m in ("groq/llama-3.3-70b-versatile", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
        assert clean_model(m) == "openai/gpt-oss-120b"
    assert clean_model("groq/openai/gpt-oss-20b") == "openai/gpt-oss-20b"


def test_no_retired_model_used_as_a_default():
    src = "\n".join(p.read_text(errors="ignore") for p in list(ROOT.glob("*.py")) + list((ROOT / "agent_modules").glob("*.py"))
                    if p.name != "llm_client.py")
    assert "qwen3.8" not in src and "custom_openai=True" not in src
    assert not any("llama-3.3" in m for m in TEXT_MODELS + VISION_MODELS)


def test_chat_falls_through_dead_model():
    import types
    calls = []

    def post(url, headers=None, json=None, timeout=0):
        calls.append(json["model"])
        ok = json["model"] != TEXT_MODELS[0]
        return types.SimpleNamespace(status_code=200 if ok else 404, raise_for_status=lambda: None,
                                     json=lambda: {"choices": [{"message": {"content": "hi"}}]})
    r = chat([{"role": "user", "content": "x"}], "k", post=post)
    assert r["ok"] and r["model"] == TEXT_MODELS[1] and calls[0] == TEXT_MODELS[0]
