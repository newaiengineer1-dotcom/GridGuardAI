import os
from io import StringIO

import pandas as pd
from datetime import date
import streamlit as st

import ui_components as ui
from agent_modules.bill_ocr import FIELD_LABELS, case_values, extract_bill
from agent_modules.bill_portals import check_consumer_no, portal_for
from agent_modules.location_agent import CITIES as CITY_MAP
from agent_modules.planner import APPLIANCES, DEFAULT_ROWS, appliance_costs, bill_for, cliffs, what_if
from agent_modules.report import build_report, build_report_pdf
from agent_modules.adjustments import default_month, label as month_label, months as known_months, updated as table_updated, lookup as adjustment_lookup
from agent_modules.bill_split import split_bill
from agent_modules.tariff import CATEGORIES, TARIFF_VERSION, compare_lines
from agents import Orchestrator, crewai_available, run_crew_case
from agent_modules import workflow as wf, value_engineering as ve, llm_features as llmf
from agent_modules.llm_client import self_test, TEXT_MODELS
from ui_theme import THEME, css

st.set_page_config(page_title="GridGuard AI", page_icon="⚡", layout="wide")

CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Gujranwala", "Peshawar",
          "Quetta", "Hyderabad", "Sukkur"]


def secret(name: str) -> str:
    try:
        return st.secrets.get(name, "") or os.getenv(name, "")
    except Exception:
        return os.getenv(name, "")


WIDGET_FOR = {"units": "in_units", "billed": "in_billed", "consumer_no": "in_cno", "sanctioned_kw": "in_kw",
              "fca": "in_fca", "qta": "in_qta"}


def apply_ocr():
    vals = case_values((st.session_state.get("ocr") or {}).get("fields", {}))
    for k, widget in WIDGET_FOR.items():
        if vals.get(k) is not None:
            st.session_state[widget] = vals[k]
    if vals.get("sanctioned_kw") is not None:
        st.session_state["in_kwknown"] = True
    st.session_state["ocr_applied"] = sorted(vals)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## 🔑 Groq API")
    if not crewai_available():
        st.warning("CrewAI is not installed here. `pip install crewai` (Python 3.10-3.13).")
    api_key = st.text_input("🔑 GROQ_API_KEY", value=secret("GROQ_API_KEY"), type="password",
                            placeholder="gsk_...")

    llm_model = st.selectbox("🧠 LLM model (Groq)", TEXT_MODELS, help="llama-3.3-70b-versatile was retired by Groq on 16 Aug 2026.")
    if st.button("🧪 Test LLM connection", use_container_width=True):
        t = self_test(api_key)
        (st.success if t["ok"] else st.error)(("✅ OK via " + t["model"]) if t["ok"] else "❌ " + t["error"])
        st.json(t["env"])

    st.markdown("## 📋 Case input")
    city = st.selectbox("🏙️ City", CITIES)
    area = st.selectbox("🏘️ Area type", ["urban", "mixed", "rural"])
    name, cno = st.text_input("👤 Your name"), st.text_input("🔢 Consumer / reference no.", key="in_cno")
    units = st.number_input("⚡ Units this month", 0, key="in_units")
    billed = st.number_input("💰 Billed amount (Rs)", 0, key="in_billed")
    prev = st.number_input("📆 Units last month", 0)
    month = st.selectbox("🗓️ Bill month", known_months() + ["other"], index=(known_months() + ["other"]).index(default_month()),
                         format_func=month_label, help="Used to look up the official FCA and QTA for that month.")
    ctype = st.selectbox("🛡️ Consumer type", CATEGORIES,
                         help="Protected = 200 units or less in each of the last 6 months.")
    kw = st.number_input("🔌 Sanctioned load (kW)", 0.5, 50.0, 2.0, 0.5, key="in_kw",
                         help="Printed on your bill. Fixed charges are billed per kW.")
    kw_known = st.checkbox("📌 This load is printed on my bill", key="in_kwknown")
    hours = st.number_input("🕒 Outage hours today", 0.0, 24.0, 0.0)
    temp = st.number_input("🌡️ Temperature °C (used if offline)", 0, 55, 35)
    with st.expander("🧮 Optional overrides (only if your bill differs)"):
        st.caption("Leave at 0: GridGuard looks up the official FCA and QTA for your bill month automatically.")
        fca = st.number_input("⛽ FCA / FPA (Rs per unit)", -50.0, 50.0, 0.0, 0.1, format="%.4f", key="in_fca")
        qta = st.number_input("📅 QTA (Rs per unit)", -50.0, 50.0, 0.0, 0.1, format="%.4f", key="in_qta")
        fcau = st.number_input("📆 Units on your FCA line (0 = same as this month)", 0, key="in_fcau")

st.markdown(css(THEME), unsafe_allow_html=True)
st.markdown(ui.hero("CrewAI crew · Groq LLM", crewai_available()), unsafe_allow_html=True)

sp = (split_bill(units, billed, prev, kw, kw_known, ctype, None if month == "other" else month, fca, qta, fcau or None)
      if units else None)

# Always-visible billing intelligence: the key audit details are surfaced before the tabs.
if sp:
    adj_info = adjustment_lookup(None if month == "other" else month, sp["category"]) if month != "other" else None
    month_info = {}
    if adj_info:
        month_info = {"month_label": month_label(month), "fca": adj_info["fca"], "qta": adj_info["qta"]}
    st.markdown(ui.bill_intelligence_dashboard(sp, units, billed, month_info), unsafe_allow_html=True)

tab_go, tab_bill, tab_save, tab_trace, tab_stats, tab_act, tab_brief, tab_auto, tab_about = st.tabs(
    ["🚀 Investigate", "🧾 Bill Center", "💡 Savings Planner", "🕵️ Agent Trace", "📊 Analytics", "📝 Complaint & Approval",
     "🧠 Crew Briefing", "⚙️ Automation & Value", "ℹ️ About"])

# ---------------------------------------------------------------- investigate
with tab_go:
    text = st.text_area("🗣️ Describe the problem (Urdu / Roman Urdu / English)",
                        "Bijli 4 ghantay se ja rahi hai aur bill bhi bohat zyada aya hai.", height=110)
    launch = st.button("🚨 Launch investigation", type="primary")
    pipe = st.empty()
    pipe.markdown(ui.stepper(set()), unsafe_allow_html=True)

    if launch:
        case = dict(text=text, city=city, area_type=area, name=name, consumer_no=cno, units=units,
                    billed=billed, prev_units=prev, outage_hours=hours, temp_c=temp,
                    sanctioned_kw=kw, kw_known=kw_known, consumer_type=ctype, bill_month=None if month == "other" else month,
                    fca=fca, qta=qta, fca_units=fcau or None)
        done = set()

        def on_step(t):
            done.add(t["agent"])
            pipe.markdown(ui.stepper(done), unsafe_allow_html=True)

        with st.spinner("Crew is investigating..."):
            result = run_crew_case(case, api_key or None, llm_model, on_step)
        st.session_state.update(result=result, case=case)
        st.toast("Investigation complete", icon="✅")

    res, case = st.session_state.get("result"), st.session_state.get("case")
    if res:
        pipe.markdown(ui.stepper({t["agent"] for t in res["trace"]}), unsafe_allow_html=True)
        if res.get("warning"):
            st.warning("⚠️ " + res["warning"])
        elif res.get("mode") == "crewai":
            st.success(f"🤖 Investigated by a CrewAI crew on Groq (route: {res.get('llm_route', '-')}). Open the Crew Briefing tab.")
        st.markdown(ui.kpis(res, case), unsafe_allow_html=True)
    else:
        st.markdown('<div class="gg-note">👈 Fill in the case on the left, then press '
                    '<b>Launch investigation</b>.</div>', unsafe_allow_html=True)

res, case = st.session_state.get("result"), st.session_state.get("case")
EMPTY = '<div class="gg-note">🕵️ No investigation yet. Launch one from the first tab.</div>'

# ---------------------------------------------------------------- bill center
with tab_bill:
    disco = CITY_MAP.get(city.lower(), ("",))[0]
    info = portal_for(disco)

    # ---- Step 1: official portal
    st.markdown("### 🌐 Step 1 · Open your official bill")
    st.markdown(ui.portal_card(info, city, disco), unsafe_allow_html=True)
    ok, msg = check_consumer_no(disco, cno)
    if msg:
        (st.success if ok else st.warning if ok is False else st.info)(("✅ " if ok else "⚠️ " if ok is False else "ℹ️ ") + msg)
    st.link_button(f"🔗 Open {info['name']}", info["url"], type="primary")

    # ---- Step 2: scan
    st.markdown("### 📸 Step 2 · Scan your bill (photo or PDF)")
    up = st.file_uploader("📸 Bill photo / screenshot / PDF", type=["png", "jpg", "jpeg", "pdf"], key="bill_file")
    if up is not None and up.name.lower().endswith(("png", "jpg", "jpeg")):
        st.image(up, caption="Your bill", width=320)
    if st.button("🔍 Scan bill with Groq", disabled=up is None):
        with st.spinner("Reading your bill..."):
            st.session_state["ocr"] = extract_bill(up.getvalue(), up.name, api_key or None)
            st.session_state.pop("ocr_applied", None)
    ocr = st.session_state.get("ocr")
    if ocr:
        if ocr.get("warning"):
            st.warning("⚠️ " + ocr["warning"])
        if ocr.get("ok"):
            st.markdown(ui.field_table(ocr["fields"], FIELD_LABELS), unsafe_allow_html=True)
            for issue in ocr["issues"]:
                st.warning("🔎 " + issue)
            st.caption(f"Method: {ocr['method']} · fields found: {ocr['confidence']:.0%}. "
                       "Always compare these numbers with your paper bill before using them.")
            st.button("✅ Use these values in my case", on_click=apply_ocr, type="primary")
            if st.session_state.get("ocr_applied"):
                st.success("Filled: " + ", ".join(st.session_state["ocr_applied"]) + ". Check the sidebar.")

    # ---- Step 3: auto-split
    st.markdown("### 🧮 Step 3 · Auto-split my bill")
    if not units:
        st.markdown('<div class="gg-note">⚡ Enter <b>Units this month</b> and <b>Billed amount</b> in the sidebar (or scan a bill). '
                    'GridGuard splits it into slab, fixed charges, FCA, QTA, surcharges and taxes for you.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(ui.cards([
            ("🧾", "Best-fit expected", f"Rs {sp['modelled_total']:,.0f}", f"{sp['category']} · {sp['confidence']} confidence"),
            ("📏", "Likely range", f"Rs {sp['low']:,.0f} – {sp['high']:,.0f}", "lowest to highest plausible"),
            *([("💸", "Likely overcharge", f"Rs {sp['overcharge_likely']:,.0f}", "billed minus best fit"),
               ("🛡️", "Conservative overcharge", f"Rs {sp['overcharge_conservative']:,.0f}", "above the highest plausible bill")]
              if billed else []),
        ]), unsafe_allow_html=True)
        if billed:
            st.markdown(ui.split_view(sp["components"], billed), unsafe_allow_html=True)
            if sp["overcharge_conservative"] > 0:
                st.error(f"🔴 Your bill is Rs {sp['overcharge_conservative']:,.0f} above even the highest plausible bill. "
                         "Use the complaint draft and the audit report below.")
            elif sp["overcharge_likely"] > 0:
                st.warning(f"🟠 About Rs {sp['overcharge_likely']:,.0f} of your bill is not explained by the best-fit model. "
                           "It may be a normal charge this model does not know. Check each line on your paper bill.")
            else:
                st.success("✅ Your bill is explained by the tariff, the official FCA / QTA and standard charges.")
        else:
            st.markdown(ui.bill_table(sp["fit_result"]["lines"], sp["modelled_total"], "🧮 Expected bill (add your billed amount to detect overcharges)"),
                        unsafe_allow_html=True)
        for w in sp["warnings"]:
            st.warning("⚠️ " + w)
        st.markdown("#### 🔍 Evidence & calculation status")
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Method", {"table":"Rate lookup","manual":"Manual override","implied":"Indicative"}.get(sp["mode"], sp["mode"]))
        e2.metric("FCA", f"Rs {sp['fit_result']['parts'].get('fca',0):,.2f}")
        e3.metric("QTA", f"Rs {sp['fit_result']['parts'].get('qta',0):,.2f}")
        e4.metric("Unexplained", f"Rs {sp['unexplained']:,.2f}")
        st.markdown("**What is calculated vs inferred** — slab energy, fixed charges and GST are calculated; FCA/QTA are month-based lookups or overrides; optional surcharges/duty are inferred only when they materially explain the bill; the unexplained line is a reconciliation remainder, not automatically an overcharge.")
        with st.expander("📌 Full calculation trail", expanded=True):
            st.markdown("\n".join(f"- {n}" for n in sp["notes"]))
            if sp["fit_keys"]:
                st.markdown("- Charges inferred by best fit (not read from your bill): "
                            + ", ".join(k for k in sp["fit_keys"]))
            st.caption(f"FCA/QTA table last updated {table_updated()} · {TARIFF_VERSION}. Edit agent_modules/adjustments.json "
                       "and tariff.py when NEPRA notifies new rates.")
        rows = compare_lines(ocr["fields"], sp["fit_result"]) if ocr and ocr.get("ok") else []
        if rows:
            st.markdown(ui.line_check_table(rows), unsafe_allow_html=True)
        report_case = dict(name=name, consumer_no=cno, city=city, units=units, billed=billed, sanctioned_kw=kw)
        if billed:
            txt_report = build_report(report_case, sp, rows)
            pdf_report = build_report_pdf(report_case, sp, rows)
            csv_rows = ["Component,Amount_Rs,Share_of_Bill"] + [
                f'"{c["label"].replace(chr(34), chr(34)*2)}",{c["amount"]:.2f},{(c["amount"]/billed*100 if billed else 0):.2f}%'
                for c in sp["components"]
            ]
            d1, d2, d3 = st.columns(3)
            d1.download_button("⬇️ Audit PDF", pdf_report, "gridguard_bill_audit.pdf", "application/pdf",
                               help="Professional audit report; reference number masked.")
            d2.download_button("⬇️ Audit TXT", txt_report, "gridguard_bill_audit.txt", "text/plain")
            d3.download_button("⬇️ Split CSV", "\n".join(csv_rows), "gridguard_bill_split.csv", "text/csv")

    # ---- Accuracy back-test
    with st.expander("🎯 Accuracy back-test (use your past bills)"):
        st.caption("Enter real past bills (that you believe were correct). GridGuard splits each one and shows how much of the "
                   "bill the model could NOT explain. A low error means the model fits your DISCO well.")
        opts = known_months() + ["other"]
        seed = pd.DataFrame({"units": [0], "billed": [0.0], "prev_units": [0], "kw": [2.0], "month": [default_month()]})
        df = st.data_editor(seed, num_rows="dynamic", use_container_width=True, key="backtest",
                            column_config={"month": st.column_config.SelectboxColumn("Bill month", options=opts, required=True)})
        rows_t, errs = [], []
        for _, r in df.iterrows():
            if r["units"] and r["billed"]:
                m = None if r["month"] == "other" else r["month"]
                t = split_bill(r["units"], r["billed"], r["prev_units"], r["kw"], False, "auto", m)
                errs.append(abs(t["unexplained"]) / r["billed"])
                rows_t.append((f"{r['units']:g}", f"{r['billed']:,.0f}", f"{t['modelled_total']:,.0f}",
                               f"{t['unexplained'] / r['billed']:+.1%}", t["confidence"]))
        if rows_t:
            st.markdown(ui.simple_table(["Units", "Billed (Rs)", "Best fit (Rs)", "Unexplained", "Confidence"], rows_t),
                        unsafe_allow_html=True)
            st.metric("Average unexplained share", f"{sum(errs) / len(errs):.1%}", help="Lower is better.")
            st.caption(f"{sum(x <= 0.01 for x in errs)} of {len(errs)} bills were explained within 1%. Months outside the "
                       "FCA/QTA table use a looser, combined estimate.")

# ---------------------------------------------------------------- rate intelligence
with st.expander("📚 Rate Card & Evidence Explorer", expanded=False):
    st.markdown("#### Monthly FCA / QTA register")
    rate_rows = []
    for m in known_months():
        z = adjustment_lookup(m, sp["category"] if sp else "unprotected") if sp else adjustment_lookup(m, "unprotected")
        rate_rows.append((month_label(m), z["fca"], z["qta"], z.get("status",""), ", ".join(z.get("fca_exempt",[])), ", ".join(z.get("qta_exempt",[]))))
    st.markdown(ui.simple_table(["Bill month","FCA Rs/u","QTA Rs/u","Status","FCA exemptions","QTA exemptions"], rate_rows), unsafe_allow_html=True)
    st.caption("Rates are stored locally in agent_modules/adjustments.json. Approved/notification evidence and proposed requests are deliberately labelled separately.")
    st.link_button("↗ Open NEPRA official site", "https://nepra.org.pk/", use_container_width=True)

# ---------------------------------------------------------------- savings planner
with tab_save:
    st.markdown("### 💡 Savings planner")
    if not units:
        st.markdown('<div class="gg-note">⚡ Enter <b>Units this month</b> in the sidebar to see how to cut your bill.</div>',
                    unsafe_allow_html=True)
    else:
        kk = sp["fit_params"]
        now = bill_for(units, prev, **kk)
        cl = cliffs(units, prev, **kk)
        items = [("🧾", "Estimated bill", f"Rs {now:,.0f}", f"{units:g} units · {cl['category']}")]
        if cl["next_slab"]:
            n = cl["next_slab"]
            items.append(("🚧", "Next slab in", f"{n['units_left']} units",
                          f"Crossing {n['boundary']} units adds about Rs {n['jump']:,.0f}"))
        if cl["drop_to"]:
            d = cl["drop_to"]
            items.append(("⬇️", f"Drop to {d['boundary']} units", f"Save Rs {d['saving']:,.0f}",
                          f"by using {d['units_to_cut']} fewer units"))
        st.markdown(ui.cards(items), unsafe_allow_html=True)
        if cl["protected_cliff"]:
            pc = cl["protected_cliff"]
            st.info(f"🛡️ At 200 units a protected household would pay about Rs {pc['bill_at_200_protected']:,.0f}. "
                    f"That is {pc['units_to_cut']} units less than now. " + pc["note"])
        if cl["next_slab"] and cl["next_slab"]["units_left"] <= 15:
            st.warning(f"⚠️ You are only {cl['next_slab']['units_left']} units below a slab boundary. "
                       "Landing-slab billing re-prices ALL units once you cross it.")

        st.markdown("#### 🎚️ What if I use less?")
        red = st.slider("Cut my usage by (units)", 0, int(units), min(20, int(units)))
        w = what_if(units, red, prev, **kk)
        st.markdown(ui.cards([("📉", "Units after", f"{w['units_after']:g}", f"-{red} units"),
                              ("🧾", "New bill", f"Rs {w['bill_after']:,.0f}", f"was Rs {w['bill_now']:,.0f}"),
                              ("💰", "You save", f"Rs {w['saving']:,.0f}", "per month")]), unsafe_allow_html=True)

        st.markdown("#### 🔌 Where do my units go?")
        st.caption("Typical power draw, so treat this as a guide. Change the quantity and hours per day.")
        base = pd.DataFrame(DEFAULT_ROWS, columns=["appliance", "qty", "hours_per_day"])
        edited = st.data_editor(
            base, num_rows="dynamic", use_container_width=True, key="appliances",
            column_config={"appliance": st.column_config.SelectboxColumn("Appliance", options=list(APPLIANCES), required=True),
                           "qty": st.column_config.NumberColumn("Qty", min_value=0, step=1),
                           "hours_per_day": st.column_config.NumberColumn("Hours/day", min_value=0.0, max_value=24.0, step=0.5)})
        rows_a = [(r["appliance"], r["qty"], r["hours_per_day"]) for _, r in edited.iterrows()
                  if r["appliance"] in APPLIANCES and r["qty"] and r["hours_per_day"]]
        if rows_a:
            costs = appliance_costs(rows_a, units, prev, **kk)
            total_est = sum(c["units"] for c in costs) or 1
            st.markdown(ui.bars([(f"{c['name']} · {c['units']:g} units", c["units"] / total_est) for c in costs],
                                "Share of estimated usage", "🔌"), unsafe_allow_html=True)
            best = max(costs, key=lambda c: c["saving_per_hour_less"])
            st.success(f"💡 Biggest quick win: run **{best['name']}** 1 hour less per day to save about "
                       f"Rs {best['saving_per_hour_less']:,.0f} a month.")
            cover = sum(c["units"] for c in costs) / units
            st.caption(f"These appliances explain about {cover:.0%} of your {units:g} units. "
                       + ("Add more appliances to find the rest." if cover < 0.8 else
                          "More than your meter shows: reduce hours or check the numbers." if cover > 1.2 else "Close to your meter."))

# ---------------------------------------------------------------- trace
with tab_trace:
    if not res:
        st.markdown(EMPTY, unsafe_allow_html=True)
    else:
        for t in res["trace"]:
            st.markdown(ui.agent_card(t), unsafe_allow_html=True)
            with st.expander(f"🔬 Raw data · {t['agent']}"):
                st.json(t["finding"].data)

# ---------------------------------------------------------------- analytics
with tab_stats:
    if not res:
        st.markdown(EMPTY, unsafe_allow_html=True)
    else:
        by = {t["agent"]: t["finding"] for t in res["trace"]}
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown('<div class="gg-panel"><h4>🎯 Case strength</h4>'
                        + ui.gauge(res["ctx"].get("case_strength", 0)) + "</div>", unsafe_allow_html=True)
        with c2:
            ranked = (by["Grid Analyst"].data or {}).get("ranked", [])
            st.markdown(ui.bars(ranked, "Likely cause of outage", "📡"), unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            ba = by["Bill Auditor"].data or {}
            if ba.get("expected") and case["billed"]:
                st.markdown(ui.bill_compare(ba["expected"], case["billed"]), unsafe_allow_html=True)
            else:
                st.markdown('<div class="gg-note">🧾 Enter units and billed amount to see the bill audit.</div>',
                            unsafe_allow_html=True)
        with c4:
            st.markdown(ui.confidence_bars(res["trace"]), unsafe_allow_html=True)
        notes = (by["Regulation Agent"].data or {}).get("notes", [])
        if notes:
            st.markdown('<div class="gg-panel"><h4>⚖️ Regulatory notes</h4>'
                        + "".join(f"<div>📌 {n}</div>" for n in notes) + "</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- complaint & approval
with tab_act:
    if not res:
        st.markdown(EMPTY, unsafe_allow_html=True)
    else:
        ctx = res["ctx"]
        st.markdown("### 🧑‍⚖️ Human approval")
        draft = st.text_area("✏️ Review / edit complaint", ctx["draft"]["en"], height=280)
        st.text_area("🗣️ Roman Urdu summary", ctx["draft"]["ur"], height=90)
        c1, c2 = st.columns(2)
        if c1.button("✅ Approve", use_container_width=True):
            Orchestrator.approve(res, True, draft)
        if c2.button("❌ Reject", use_container_width=True):
            Orchestrator.approve(res, False)
        badge = {"APPROVED": "success", "REJECTED": "error"}.get(res["status"], "info")
        getattr(st, badge)(f"📌 Status: {res['status']}")
        if res["status"] == "APPROVED":
            st.download_button("⬇️ Download complaint", ctx["draft"]["en"], "gridguard_complaint.txt")
            st.markdown("**🪜 Next: submit via** " + " → ".join(ctx["escalation"]))
        a1, a2 = st.columns(2)
        if a1.button("✨ Polish with AI", use_container_width=True, disabled=not api_key):
            r = llmf.polish_complaint(draft, api_key)
            st.text_area("Polished (copy into the box above if you like it)", r["text"] if r["ok"] else "", height=220) if r["ok"] else st.error(r["error"])
        if a2.button("اردو Urdu script", use_container_width=True, disabled=not api_key):
            r = llmf.urdu_script(draft, api_key)
            st.text_area("Urdu", r["text"], height=220) if r["ok"] else st.error(r["error"])

# ---------------------------------------------------------------- crew briefing
with tab_brief:
    if not res:
        st.markdown(EMPTY, unsafe_allow_html=True)
    elif res.get("crew_report"):
        st.markdown("### 🤖 Case Officer briefing (CrewAI)")
        st.markdown(ui.briefing(res["crew_report"]), unsafe_allow_html=True)
    else:
        st.markdown('<div class="gg-note">🤖 No CrewAI briefing for this run. Add your <b>GROQ_API_KEY</b> '
                    'in the sidebar and launch again.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- automation & value
with tab_auto:
    if not res:
        st.markdown(EMPTY, unsafe_allow_html=True)
    else:
        ctx = res["ctx"]
        tri = wf.triage(case, ctx)
        plan = wf.followup_plan(tri["priority"])
        st.markdown("### ⚙️ AI workflow automation")
        c1, c2, c3 = st.columns(3)
        c1.metric("Priority", f"{tri['priority']} · {tri['score']}/100")
        c2.metric("Response SLA", f"{tri['sla_hours']} h")
        c3.metric("Start with", tri["first_channel"])
        st.caption("Why: " + "; ".join(tri["reasons"]))
        st.dataframe([{"Day": p["day"], "Date": p["date"], "Action": p["action"]} for p in plan], hide_index=True, use_container_width=True)
        try:
            pdf = build_report_pdf(case, (sp or {}), None)
        except Exception:
            pdf = None
        extra = {"06_report.pdf": pdf} if pdf else None
        d1, d2 = st.columns(2)
        d1.download_button("📅 Follow-up reminders (.ics)", wf.to_ics(plan), "gridguard_followups.ics", use_container_width=True)
        d2.download_button("📦 One-click case file (.zip)", wf.case_file_zip(ctx, case, tri, plan, extra), "gridguard_case_file.zip", use_container_width=True)
        st.text_area("💬 WhatsApp-ready message", wf.whatsapp_text(ctx, case), height=90)
        st.markdown("#### 📓 Outage evidence log")
        log = st.data_editor([{"date": str(date.today()), "hours": float(ctx.get("outage_hours") or 0)}], num_rows="dynamic", key="outlog")
        ls = wf.outage_log_summary(list(log), ctx.get("excess_hours", 0) and 2 or 2)
        st.info(f"{ls['days']} outage days · {ls['total_h']} h total · {ls['over_days']} beyond schedule ({ls['excess_h']} h). {ls['pattern']}")
        st.markdown("### 💎 Value engineering: biggest savings first")
        sp = (sp or {})
        vo = ve.opportunities(case.get("units") or 0, case.get("prev_units") or 0, overcharge=sp.get("overcharge_likely", 0) or 0)
        st.caption(f"Bill now ≈ Rs {vo['bill_now']:,} · avg Rs {vo['avg_rate']}/unit · potential ≈ Rs {vo['annual_potential']:,}/year from the top two actions. Solar figures are assumptions.")
        st.dataframe([{"Action": a["action"], "Rs / month": a["monthly_saving"], "Effort": a["effort"], "Confidence": a["confidence"], "How": a["how"]}
                      for a in vo["actions"]], hide_index=True, use_container_width=True)
        st.markdown("### 🤖 Ask the Copilot about your case")
        q = st.text_input("Ask anything (e.g. 'Which office should I go to first and why?')")
        if q and api_key:
            r = llmf.copilot(q, ctx, case, api_key)
            st.markdown(r["text"]) if r["ok"] else st.error(r["error"])
        elif q:
            st.info("Add your GROQ_API_KEY to use the Copilot.")

# ---------------------------------------------------------------- about
with tab_about:
    st.markdown("""
### ℹ️ How GridGuard works
**🛰️ Pipeline:** 📍 Location → 🧾 Bill Auditor → 🔌 Outage Detector → 🌡️ Weather → ⚖️ Regulation →
📡 Grid Analyst → 🕵️ Evidence → ✍️ Action → 🧑‍⚖️ Human approval

**🤖 CrewAI + Groq:** every specialist is a real CrewAI agent with its own tool, running in a sequential crew
powered by Groq, plus a Case Officer agent that writes the final briefing. If CrewAI or the GROQ_API_KEY is
missing, it falls back to a direct Groq call, then to the deterministic rules engine.

**🧾 Bill Center:** opens the official portal for your DISCO, scans a bill photo or PDF with Groq vision, and rebuilds the
expected bill line by line (slab rate, fixed charge, FCA, QTA, GST). Add FCA / QTA from your bill for the closest match.

**⚠️ Note:** tariff slabs and outage allowances come from public sources and may change. Verify against NEPRA / DISCO notifications
before filing.
""")
