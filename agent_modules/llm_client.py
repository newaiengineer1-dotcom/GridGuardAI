"""Direct Groq client (OpenAI-compatible REST) with dead-model fallback. No CrewAI/LiteLLM needed."""
from __future__ import annotations

import json
import os
import sys

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_URL = GROQ_BASE_URL + "/chat/completions"
# Groq retired llama-3.3-70b-versatile and llama-3.1-8b-instant on 2026-08-16 (HTTP 404 model_not_found).
TEXT_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
VISION_MODELS = ["meta-llama/llama-4-scout-17b-16e-instruct", "qwen/qwen3.6-27b"]
DEAD_MODELS = {"llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192",
               "llama-3.1-70b-versatile", "qwen/qwen3-32b"}


def clean_model(model: str | None = None) -> str:
    """Strip LiteLLM-style 'groq/' prefix and swap retired model ids for the current default."""
    m = (model or os.getenv("GROQ_MODEL") or TEXT_MODELS[0]).strip()
    if m.startswith("groq/") and m[5:] != "compound":
        m = m[5:]
    return TEXT_MODELS[0] if m in DEAD_MODELS or not m else m


def _chain(model, models):
    first = clean_model(model) if models is TEXT_MODELS else (model or models[0])
    return [first] + [m for m in models if m != first]


def chat(messages, key, model=None, models=None, post=None, timeout=45, json_mode=False, max_tokens=900) -> dict:
    """Return {ok, text, model, error}. Tries the next model when one is missing/retired."""
    if not key:
        return {"ok": False, "text": "", "model": "", "error": "No GROQ_API_KEY"}
    if post is None:
        import requests
        post = requests.post
    err = ""
    for m in _chain(model, models or TEXT_MODELS):
        body = {"model": m, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            r = post(GROQ_URL, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                     json=body, timeout=timeout)
            if getattr(r, "status_code", 200) in (400, 404):  # model gone / not allowed: try the next one
                err = f"{m}: HTTP {r.status_code}"
                continue
            r.raise_for_status()
            return {"ok": True, "text": r.json()["choices"][0]["message"]["content"].strip(), "model": m, "error": ""}
        except Exception as e:
            err = f"{m}: {type(e).__name__} {str(e)[:100]}"
            if "Timeout" in type(e).__name__ or "Connection" in type(e).__name__:
                break
    return {"ok": False, "text": "", "model": "", "error": err}


def json_chat(messages, key, **kw) -> dict:
    r = chat(messages, key, json_mode=True, **kw)
    if r["ok"]:
        try:
            s = r["text"]
            r["data"] = json.loads(s[s.index("{"): s.rindex("}") + 1])
        except Exception as e:
            r.update(ok=False, error=f"bad JSON ({e})")
    return r


def diagnose() -> dict:
    """Environment report shown in the sidebar 'Test LLM' button."""
    info = {"python": sys.version.split()[0]}
    for pkg in ("crewai", "litellm", "openai", "requests"):
        try:
            from importlib.metadata import version
            info[pkg] = version(pkg)
        except Exception:
            info[pkg] = "NOT INSTALLED"
    info["crewai_groq_route"] = ("litellm" if info["litellm"] != "NOT INSTALLED" else "native-openai/custom") \
        if info["crewai"] != "NOT INSTALLED" else "n/a"
    return info


def self_test(key, post=None) -> dict:
    r = chat([{"role": "user", "content": "Reply with the single word OK."}], key, post=post, max_tokens=20)
    return {**r, "env": diagnose()}
