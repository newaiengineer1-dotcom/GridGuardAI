"""LLM features on top of the deterministic findings. Every function degrades gracefully without a key."""
from __future__ import annotations

import json

from .llm_client import chat

SYSTEM = ("You are GridGuard AI's Case Officer for Pakistani electricity consumers. Use ONLY the facts given. "
          "Never invent tariffs, clauses or amounts. Be calm, plain and short. Nothing is filed without the consumer's approval.")


def _facts(ctx: dict, case: dict) -> str:
    fs = [{"agent": f.agent, "severity": f.severity, "summary": f.summary} for f in ctx.get("findings", [])]
    keep = {k: v for k, v in case.items() if v not in (None, "") and k not in ("name", "consumer_no")}
    return json.dumps({"case": keep, "findings": fs, "case_strength": ctx.get("case_strength")}, default=str)[:5000]


def offline_briefing(ctx: dict, case: dict) -> str:
    bad = [f.summary for f in ctx.get("findings", []) if f.severity != "info"][:3]
    return (f"Case strength {ctx.get('case_strength', 0):.0%}. " + (" ".join(bad) or "No major issue found.")
            + " Review the complaint draft; nothing is filed until you approve.")


def briefing(ctx, case, key, model=None, post=None) -> dict:
    r = chat([{"role": "system", "content": SYSTEM},
              {"role": "user", "content": "Write a briefing of at most 120 words: what happened, how strong the case is, next step. "
               "End with: 'Nothing is filed until you approve.'\nFACTS: " + _facts(ctx, case)}], key, model=model, post=post)
    return r


def urdu_script(text: str, key, post=None) -> dict:
    """Translate a Roman-Urdu/English complaint into Urdu script (نستعلیق-ready plain Unicode)."""
    return chat([{"role": "system", "content": "Translate into formal Urdu script. Keep numbers, names and reference numbers unchanged. Output only the translation."},
                 {"role": "user", "content": text[:3000]}], key, post=post, max_tokens=1200)


def polish_complaint(draft: str, key, post=None) -> dict:
    return chat([{"role": "system", "content": "Improve clarity and politeness of this complaint letter. Keep every fact, number and request unchanged. Do not add claims. Output only the letter."},
                 {"role": "user", "content": draft[:4000]}], key, post=post, max_tokens=1200)


def copilot(question: str, ctx: dict, case: dict, key, post=None) -> dict:
    """Grounded Q&A about the consumer's own case."""
    return chat([{"role": "system", "content": SYSTEM + " If the facts do not answer the question, say what is missing."},
                 {"role": "user", "content": f"FACTS: {_facts(ctx, case)}\n\nQUESTION: {question[:500]}"}], key, post=post)
