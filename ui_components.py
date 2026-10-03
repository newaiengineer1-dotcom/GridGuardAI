"""Small HTML renderers for the dashboard (kept dependency-free)."""
from html import escape

from ui_theme import AGENT_ICONS, SEV

AGENT_ORDER = list(AGENT_ICONS)


def _h(s: str) -> str:
    # Streamlit markdown treats 4+ leading spaces as a code block, so flatten the HTML.
    return "".join(line.strip() for line in s.splitlines())


def hero(mode: str, crew_ok: bool) -> str:
    crew = "🤖 CrewAI ready" if crew_ok else "🤖 CrewAI not installed"
    return _h(f"""
<div class="gg-hero">
  <h1>⚡ GridGuard AI</h1>
  <p>Autonomous multi-agent incident response for Pakistan's electricity outages and billing disputes.
     🛡️ Nothing is filed without your approval.</p>
  <div class="gg-badges">
    <span class="gg-chip on">🧠 {escape(mode)}</span>
    <span class="gg-chip {'on' if crew_ok else ''}">{crew}</span>
    <span class="gg-chip">🇵🇰 11 cities · 10 DISCOs</span>
    <span class="gg-chip">🗣️ Urdu · Roman Urdu · English</span>
  </div>
</div>""")


def kpis(res: dict, case: dict) -> str:
    ctx, trace = res["ctx"], {t["agent"]: t["finding"] for t in res["trace"]}
    ba = trace.get("Bill Auditor")
    exp = (ba.data or {}).get("expected") if ba else None
    var = (ba.data or {}).get("variance") if ba else None
    ev = trace.get("Investigation / Evidence Agent")
    verdict = (ev.data or {}).get("verdict", "-") if ev else "-"
    cards = [
        ("🎯", "Case strength", f"{ctx.get('case_strength', 0):.0%}", f"Verdict: {verdict}"),
        ("🏢", "Your DISCO", ctx.get("disco", "n/a"), case.get("city", "")),
        ("🔌", "Outage", f"{ctx.get('outage_hours', 0):g} h", f"Excess over schedule: {ctx.get('excess_hours', 0):g} h"),
        ("🧾", "Bill variance", f"{var:+.0%}" if var is not None else "n/a",
         f"Expected Rs {exp:,.0f}" if exp else "No bill data"),
        ("💸", "Possible overcharge", f"Rs {ctx.get('overcharge_est', 0):,.0f}", "Conservative estimate"),
        ("🌡️", "Weather", f"{ctx.get('temp_c', '-')}°C", f"Wind {ctx.get('wind_kmh', 0)} km/h"),
    ]
    body = "".join(f'<div class="gg-kpi"><div class="ic">{i}</div><div class="lb">{l}</div>'
                   f'<div class="vl">{escape(str(v))}</div><div class="sb">{escape(str(s))}</div></div>'
                   for i, l, v, s in cards)
    return _h(f'<div class="gg-kpis">{body}</div>')


def stepper(done: set, running: str | None = None) -> str:
    short = {"Weather / Environment Agent": "Weather", "Investigation / Evidence Agent": "Evidence"}
    out = []
    for n in AGENT_ORDER:
        cls = "done" if n in done else "run" if n == running else ""
        out.append(f'<div class="gg-step {cls}"><span class="si">{AGENT_ICONS[n]}</span>'
                   f'{escape(short.get(n, n.replace(" Agent", "")))}</div>')
    return _h(f'<div class="gg-panel"><h4>🛰️ Agent pipeline</h4><div class="gg-steps">{"".join(out)}</div></div>')


def agent_card(t: dict) -> str:
    f = t["finding"]
    dot, label = SEV[f.severity]
    return _h(f"""
<div class="gg-agent {f.severity}">
  <div class="ai">{AGENT_ICONS.get(t['agent'], '🤖')}</div>
  <div><div class="an">{escape(t['agent'])}</div><div class="as">{escape(f.summary)}</div></div>
  <div class="am"><span class="gg-pill {f.severity}">{dot} {label}</span><br>
     ⏱️ {t['ms']} ms<br>📶 {f.confidence:.0%} confidence</div>
</div>""")


def gauge(score: float, label: str = "CASE STRENGTH") -> str:
    return _h(f'<div class="gg-gauge" style="--p:{score * 100:.0f}"><div class="in"><div>'
              f'<div class="n">{score:.0%}</div><div class="l">{label}</div></div></div></div>')


def bars(items, title: str, icon: str = "📊") -> str:
    rows = "".join(f'<div class="gg-bar"><div class="t"><span>{escape(n)}</span><b>{v:.0%}</b></div>'
                   f'<div class="tr"><div class="fi" style="width:{min(max(v, 0), 1) * 100:.0f}%"></div></div></div>'
                   for n, v in items)
    return _h(f'<div class="gg-panel"><h4>{icon} {escape(title)}</h4>{rows}</div>')


def bill_compare(expected: float, billed: float) -> str:
    top = max(expected, billed, 1)
    rows = bars([("Expected (tariff model)", expected / top), ("Billed", billed / top)], "Bill vs expected", "🧾")
    return rows + _h(f'<div class="gg-note">Expected Rs {expected:,.0f} · Billed Rs {billed:,.0f} · '
                     f'Difference Rs {billed - expected:+,.0f}</div>')


def confidence_bars(trace) -> str:
    return bars([(t["agent"], t["finding"].confidence) for t in trace], "Confidence by agent", "📶")


def briefing(text: str) -> str:
    return _h(f'<div class="gg-brief">🧠 {escape(text).replace(chr(10), "<br>")}</div>')


# ---------------------------------------------------------------- Bill Center renderers
def _rs(v: float) -> str:
    return f"Rs {v:,.2f}"


def bill_table(lines, total: float, title: str = "🧮 Expected bill (itemised)") -> str:
    rows = "".join(f'<tr><td>{escape(l)}</td><td class="num">{_rs(v)}</td></tr>' for l, v in lines)
    rows += f'<tr class="tot"><td>Expected total</td><td class="num">{_rs(total)}</td></tr>'
    return _h(f'<div class="gg-panel"><h4>{escape(title)}</h4><table class="gg-table">{rows}</table></div>')


def line_check_table(rows) -> str:
    icon = {"ok": "✅", "watch": "🟡", "mismatch": "🔴"}
    body = "".join(f'<tr><td>{escape(l)}</td><td class="num">{_rs(b)}</td><td class="num">{_rs(e)}</td>'
                   f'<td class="num">{d:+.1%}</td><td>{icon[s]} {s}</td></tr>' for l, b, e, d, s in rows)
    head = "<tr><th>Line</th><th>On your bill</th><th>Expected</th><th>Diff</th><th>Status</th></tr>"
    return _h(f'<div class="gg-panel"><h4>🔎 Line-by-line check</h4><table class="gg-table">{head}{body}</table></div>')


def field_table(fields: dict, labels: dict) -> str:
    rows = "".join(f'<tr><td>{escape(labels[k])}</td><td class="num">{escape(f"{v:,.2f}" if isinstance(v, float) else str(v))}</td></tr>'
                   for k, v in fields.items() if v is not None)
    return _h(f'<div class="gg-panel"><h4>📄 Values read from your bill</h4><table class="gg-table">{rows}</table></div>')


def simple_table(headers, rows, title: str = "") -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f'<td class="num">{escape(str(c))}</td>' for c in r) + "</tr>" for r in rows)
    t = f"<h4>{escape(title)}</h4>" if title else ""
    return _h(f'<div class="gg-panel">{t}<table class="gg-table"><tr>{head}</tr>{body}</table></div>')


def portal_card(info: dict, city: str, disco: str) -> str:
    steps = "".join(f"<li>{escape(s)}</li>" for s in info["steps"])
    return _h(f"""
<div class="gg-panel"><h4>🌐 Official bill portal for {escape(city)}</h4>
<div class="gg-chips2"><span class="gg-chip on">🏢 {escape(disco or 'DISCO')}</span>
<span class="gg-chip">🔗 {escape(info['url'].replace('https://', ''))}</span>
<span class="gg-chip">🔢 {escape(info['id_label'])}</span></div>
<ol class="gg-steps-list">{steps}</ol>
<div class="gg-note">🛡️ Only use the link below. Look-alike sites collect reference numbers for fraud.
GridGuard never logs in or scrapes these portals for you.</div></div>""")


def cards(items) -> str:
    """Generic KPI cards: items = [(icon, label, value, sub)]."""
    body = "".join(f'<div class="gg-kpi"><div class="ic">{i}</div><div class="lb">{escape(l)}</div>'
                   f'<div class="vl">{escape(str(v))}</div><div class="sb">{escape(str(s))}</div></div>'
                   for i, l, v, s in items)
    return _h(f'<div class="gg-kpis">{body}</div>')


def split_view(components, billed: float) -> str:
    """Stacked bar + table of the auto-split bill (amounts add up to the billed total)."""
    pos = [c for c in components if c["amount"] > 0]
    tot = sum(c["amount"] for c in pos) or 1
    bar = "".join(f'<div class="seg k-{c["kind"]}" style="width:{c["amount"] / tot * 100:.2f}%" title="{escape(c["label"])}"></div>'
                  for c in pos)
    rows = "".join(f'<tr class="r-{c["kind"]}"><td><span class="dot k-{c["kind"]}"></span>{escape(c["label"])}</td>'
                   f'<td class="num">{_rs(c["amount"])}</td><td class="num">{c["amount"] / billed:+.1%}</td></tr>'
                   for c in components) if billed else ""
    rows += f'<tr class="tot"><td>Billed total</td><td class="num">{_rs(billed)}</td><td class="num">100%</td></tr>'
    return _h(f'<div class="gg-panel"><h4>🧩 Your bill, split automatically</h4><div class="gg-splitbar">{bar}</div>'
              f'<table class="gg-table">{rows}</table></div>')


def bill_intelligence_dashboard(sp: dict, units: float, billed: float, month_info: dict | None = None) -> str:
    """Always-visible dashboard summary so bill-split details are not hidden in an expander."""
    if not sp or not units:
        return ""
    billed = float(billed or 0)
    comp_rows = ""
    for c in sp["components"]:
        pct = (c["amount"] / billed * 100) if billed else 0
        tag = {"energy":"CALCULATED","fixed":"CALCULATED","adjust":"LOOKUP",
               "surcharge":"INFERRED","tax":"CALCULATED","unexplained":"RECONCILIATION"}.get(c["kind"],"")
        comp_rows += f"""<tr><td><b>{escape(c['label'])}</b><br><span class="gg-mini-tag">{tag}</span></td>
        <td class="num">{_rs(c['amount'])}</td><td class="num">{pct:.1f}%</td></tr>"""
    status = "🟢 Reconciled" if abs(sum(c["amount"] for c in sp["components"]) - billed) < .02 else "🟠 Check"
    mode_label = {"table":"Official-rate lookup","manual":"User override","implied":"Indicative / combined estimate"}.get(sp["mode"],sp["mode"].title())
    info = month_info or {}
    return _h(f"""
<div class="gg-panel gg-bill-dashboard">
  <div class="gg-bill-head">
    <div><h3>🧾 Bill Intelligence Dashboard</h3>
      <div class="gg-muted">Units-only input + billed amount → transparent reconciliation</div></div>
    <div class="gg-status">{status}</div>
  </div>
  <div class="gg-mini-grid">
    <div><b>Bill</b><span>Rs {billed:,.2f}</span><small>{units:g} units</small></div>
    <div><b>Best-fit</b><span>Rs {sp['modelled_total']:,.2f}</span><small>{sp['confidence']} confidence</small></div>
    <div><b>Plausible range</b><span>Rs {sp['low']:,.0f} – {sp['high']:,.0f}</span><small>load sensitivity included</small></div>
    <div><b>Conservative gap</b><span>Rs {sp['overcharge_conservative']:,.0f}</span><small>complaint metric</small></div>
  </div>
  <div class="gg-rate-strip">
    <span>📅 {escape(str(info.get('month_label') or sp.get('month') or 'Month not selected'))}</span>
    <span>⛽ FCA: <b>{escape(str(info.get('fca','—')))}</b> Rs/unit · basis {sp.get('fca_units_used', units):g}u</span>
    <span>📊 QTA: <b>{escape(str(info.get('qta','—')))}</b> Rs/unit</span>
    <span>🧠 Method: <b>{escape(mode_label)}</b></span>
    <span>🏷️ Category: <b>{escape(sp['category'])}</b></span>
    <span>📚 Status: <b>{escape(str(sp.get('adjustment_status','—')).upper())}</b></span>
  </div>
  <table class="gg-table"><tr><th>Bill line / classification</th><th>Amount</th><th>Share</th></tr>{comp_rows}
  <tr class="tot"><td>Billed total</td><td class="num">{_rs(billed)}</td><td class="num">100%</td></tr></table>
  <div class="gg-evidence-grid">
    <div><b>✓ Calculated</b><br><small>Slab energy · fixed charges · GST</small></div>
    <div><b>↗ Looked up</b><br><small>FCA · QTA for selected month</small></div>
    <div><b>⚠ Inferred</b><br><small>Optional surcharges/duty only when they explain the amount</small></div>
    <div><b>↔ Reconciled</b><br><small>Unexplained difference closes the arithmetic to your billed amount</small></div>
  </div>
</div>""")
