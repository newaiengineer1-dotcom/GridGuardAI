"""AI workflow automation: triage, SLA follow-up plan, calendar file, outage evidence log, one-click case file."""
from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta

CHANNELS = ["DISCO complaint center / app", "NEPRA consumer complaint", "Wafaqi Mohtasib / provincial ombudsman", "Pakistan Citizen Portal"]


def triage(case: dict, ctx: dict) -> dict:
    """Priority P1 (urgent) .. P4 (routine) from outage, bill and evidence signals."""
    ex, hrs = ctx.get("excess_hours", 0) or 0, ctx.get("outage_hours", 0) or 0
    strength = ctx.get("case_strength", 0) or 0
    score, why = 0, []
    if ex >= 6 or hrs >= 12:
        score += 45; why.append(f"Very long outage ({hrs:g}h)")
    elif ex >= 3:
        score += 30; why.append(f"Outage {ex:g}h beyond schedule")
    elif ex > 0:
        score += 15; why.append(f"Outage {ex:g}h beyond schedule")
    if (ctx.get("temp_c") or 0) >= 40 and hrs:
        score += 15; why.append("Heat risk for vulnerable household members")
    flags = [f for f in ctx.get("findings", []) if f.agent == "Bill Auditor" and f.severity != "info"]
    if flags:
        score += 20 if any(f.severity == "critical" for f in flags) else 10; why.append("Bill anomaly flagged")
    score += int(strength * 20)
    pr = "P1" if score >= 70 else "P2" if score >= 45 else "P3" if score >= 20 else "P4"
    sla = {"P1": 24, "P2": 72, "P3": 168, "P4": 336}[pr]
    start = 0 if pr in ("P1", "P2") else 1 if pr == "P3" else 2
    return {"priority": pr, "score": min(score, 100), "sla_hours": sla, "reasons": why or ["Routine case"],
            "first_channel": CHANNELS[start], "ladder": CHANNELS[start:]}


def followup_plan(priority: str, start: date | None = None) -> list[dict]:
    start = start or date.today()
    gaps = {"P1": [0, 1, 3, 7], "P2": [0, 3, 7, 15], "P3": [0, 7, 15, 30], "P4": [0, 14, 30, 45]}[priority]
    acts = ["File complaint with the DISCO and keep the complaint number", "Follow up: ask for status and written reply",
            "Escalate to NEPRA with the complaint number and evidence", "Escalate to Ombudsman / Citizen Portal if unresolved"]
    return [{"day": g, "date": (start + timedelta(days=g)).isoformat(), "action": a} for g, a in zip(gaps, acts)]


def to_ics(plan: list[dict], title: str = "GridGuard complaint") -> str:
    """RFC 5545 calendar file with one all-day reminder per follow-up step."""
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    ev = []
    for i, p in enumerate(plan):
        d = p["date"].replace("-", "")
        nxt = (date.fromisoformat(p["date"]) + timedelta(days=1)).strftime("%Y%m%d")
        ev.append(f"BEGIN:VEVENT\r\nUID:gridguard-{stamp}-{i}@gridguard.ai\r\nDTSTAMP:{stamp}\r\nDTSTART;VALUE=DATE:{d}\r\n"
                  f"DTEND;VALUE=DATE:{nxt}\r\nSUMMARY:{title}: {p['action']}\r\nEND:VEVENT")
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//GridGuard AI//EN\r\n" + "\r\n".join(ev) + "\r\nEND:VCALENDAR\r\n"


def whatsapp_text(ctx: dict, case: dict) -> str:
    d = ctx.get("draft", {}).get("ur", "")
    return f"{d}\nBill ref: {case.get('consumer_no') or '-'} | GridGuard AI"


def outage_log_summary(rows: list[dict], allowance_h: float = 2) -> dict:
    """rows: [{'date': 'YYYY-MM-DD', 'hours': float}] -> evidence of a repeated pattern."""
    rows = [r for r in rows if float(r.get("hours") or 0) > 0]
    if not rows:
        return {"days": 0, "total_h": 0, "avg_h": 0, "worst_h": 0, "over_days": 0, "excess_h": 0, "pattern": "No outages logged."}
    hs = [float(r["hours"]) for r in rows]
    over = [h for h in hs if h > allowance_h]
    excess = round(sum(h - allowance_h for h in over), 1)
    pat = ("Repeated unscheduled outages: strong evidence for escalation." if len(over) >= 5 else
           "Some outages beyond schedule: keep logging." if over else "Within the scheduled allowance.")
    return {"days": len(rows), "total_h": round(sum(hs), 1), "avg_h": round(sum(hs) / len(hs), 1), "worst_h": max(hs),
            "over_days": len(over), "excess_h": excess, "pattern": pat}


def case_file_zip(ctx: dict, case: dict, tri: dict, plan: list[dict], extra: dict[str, bytes | str] | None = None) -> bytes:
    """One-click bundle: complaint, WhatsApp text, follow-up calendar, checklist (+ optional PDF report)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("01_complaint_en.txt", ctx.get("draft", {}).get("en", ""))
        z.writestr("02_complaint_roman_urdu.txt", ctx.get("draft", {}).get("ur", ""))
        z.writestr("03_whatsapp_message.txt", whatsapp_text(ctx, case))
        z.writestr("04_followups.ics", to_ics(plan))
        z.writestr("05_checklist.txt", f"Priority {tri['priority']} (SLA {tri['sla_hours']}h)\nWhy: " + "; ".join(tri["reasons"]) +
                   "\nEscalation ladder:\n" + "\n".join(f"{i+1}. {c}" for i, c in enumerate(tri["ladder"])) +
                   "\nEvidence to attach: bill copy, meter photo, outage log.\nNothing is filed automatically; you approve and submit.")
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return buf.getvalue()
