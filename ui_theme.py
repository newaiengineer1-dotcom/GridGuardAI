"""Premium themes + CSS for the GridGuard AI dashboard."""

# The single GridGuard theme (Ocean Glass). Edit these colours to restyle the whole dashboard.
THEME = dict(bg1="#04101c", bg2="#0a2540", card="rgba(14,44,76,.60)", line="rgba(125,211,252,.22)",
             a1="#38bdf8", a2="#6366f1", text="#e6f4ff", muted="#8fb4d4", glow="rgba(56,189,248,.35)")

# Data-entry boxes (text, number, text areas, dropdowns, file upload).
# Default = bright YELLOW box with BLACK text. For a black box with yellow text, swap in INPUT_BLACK.
INPUT_YELLOW = dict(bg="#fde047", text="#111111", placeholder="#5c4a00", border="#f59e0b", hover="#facc15")
INPUT_BLACK = dict(bg="#000000", text="#fde047", placeholder="#d9c34a", border="#fde047", hover="#27272a")
INPUT = INPUT_YELLOW

AGENT_ICONS = {
    "Location Agent": "📍", "Bill Auditor": "🧾", "Outage Detector": "🔌", "Weather / Environment Agent": "🌡️",
    "Regulation Agent": "⚖️", "Grid Analyst": "📡", "Investigation / Evidence Agent": "🕵️", "Action Agent": "✍️",
}
SEV = {"info": ("🟢", "OK"), "warn": ("🟠", "WARN"), "critical": ("🔴", "CRITICAL")}


def css(t: dict) -> str:
    i = INPUT
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {{ --a1:{t['a1']}; --a2:{t['a2']}; --card:{t['card']}; --line:{t['line']}; --text:{t['text']};
         --muted:{t['muted']}; --glow:{t['glow']}; }}
html, body, [class*="css"], .stApp {{ font-family:'Inter',system-ui,sans-serif; color:var(--text); }}
.stApp {{ background: radial-gradient(1200px 600px at 10% -10%, {t['bg2']} 0%, transparent 60%),
          radial-gradient(900px 500px at 100% 0%, {t['glow']} 0%, transparent 55%), {t['bg1']}; }}
#MainMenu, footer {{ visibility:hidden; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:1.4rem; max-width:1250px; }}
section[data-testid="stSidebar"] {{ background:linear-gradient(180deg,{t['bg2']},{t['bg1']});
          border-right:1px solid var(--line); }}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3 {{ color:var(--a1); }}

.gg-hero {{ position:relative; overflow:hidden; border:1px solid var(--line); border-radius:22px; padding:26px 30px;
  background:linear-gradient(135deg,var(--card),rgba(0,0,0,.25)); backdrop-filter:blur(14px);
  box-shadow:0 10px 40px rgba(0,0,0,.45), 0 0 60px var(--glow) inset; margin-bottom:14px; }}
.gg-hero:before {{ content:""; position:absolute; inset:-40% auto auto 60%; width:420px; height:420px; border-radius:50%;
  background:radial-gradient(circle,var(--glow),transparent 70%); filter:blur(10px); }}
.gg-hero h1 {{ margin:0; font-size:2.3rem; font-weight:800; letter-spacing:-.5px;
  background:linear-gradient(90deg,var(--a1),var(--a2)); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.gg-hero p {{ margin:.35rem 0 0; color:var(--muted); font-size:1rem; }}
.gg-badges {{ margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; position:relative; }}
.gg-chip {{ display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:999px; font-size:.78rem;
  font-weight:600; border:1px solid var(--line); background:rgba(255,255,255,.04); color:var(--text); }}
.gg-chip.on {{ border-color:var(--a1); box-shadow:0 0 14px var(--glow); }}

.gg-kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; margin:10px 0 18px; }}
.gg-kpi {{ border:1px solid var(--line); border-radius:18px; padding:16px 18px; background:var(--card);
  backdrop-filter:blur(10px); box-shadow:0 6px 24px rgba(0,0,0,.35); transition:transform .2s, box-shadow .2s; }}
.gg-kpi:hover {{ transform:translateY(-3px); box-shadow:0 12px 32px rgba(0,0,0,.5), 0 0 24px var(--glow); }}
.gg-kpi .ic {{ font-size:1.5rem; }}
.gg-kpi .lb {{ color:var(--muted); font-size:.72rem; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; margin-top:6px; }}
.gg-kpi .vl {{ font-size:1.7rem; font-weight:800; margin-top:2px;
  background:linear-gradient(90deg,var(--a1),var(--a2)); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.gg-kpi .sb {{ color:var(--muted); font-size:.78rem; margin-top:2px; }}

.gg-panel {{ border:1px solid var(--line); border-radius:18px; padding:18px 20px; background:var(--card);
  backdrop-filter:blur(10px); margin-bottom:14px; }}
.gg-panel h4 {{ margin:0 0 12px; font-size:1rem; font-weight:700; }}

.gg-steps {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(118px,1fr)); gap:10px; }}
.gg-step {{ text-align:center; padding:12px 6px; border-radius:14px; border:1px solid var(--line);
  background:rgba(255,255,255,.05); font-size:.78rem; font-weight:600; color:var(--text); }}
.gg-step .si {{ font-size:1.7rem; display:block; margin-bottom:4px; filter:none; opacity:1;
  font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji','Twemoji Mozilla',sans-serif; }}
.gg-step.done {{ color:var(--text); border-color:var(--a1); box-shadow:0 0 16px var(--glow); }}
.gg-step.done .si {{ filter:drop-shadow(0 0 6px var(--glow)); }}
.gg-step.run {{ border-color:var(--a2); animation:pulse 1s infinite; }}
@keyframes pulse {{ 50% {{ box-shadow:0 0 22px var(--glow); }} }}

.gg-agent {{ display:flex; gap:14px; align-items:flex-start; border:1px solid var(--line); border-radius:16px;
  padding:14px 16px; margin-bottom:10px; background:var(--card); border-left:4px solid var(--a1); }}
.gg-agent.warn {{ border-left-color:#f59e0b; }} .gg-agent.critical {{ border-left-color:#ef4444; }}
.gg-agent .ai {{ font-size:1.8rem; line-height:1; }}
.gg-agent .an {{ font-weight:700; }} .gg-agent .as {{ color:var(--muted); font-size:.9rem; margin-top:2px; }}
.gg-agent .am {{ margin-left:auto; text-align:right; font-size:.72rem; color:var(--muted); white-space:nowrap; }}
.gg-pill {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:.68rem; font-weight:700; margin-bottom:4px;
  border:1px solid var(--line); }}
.gg-pill.info {{ color:#34d399; }} .gg-pill.warn {{ color:#f59e0b; }} .gg-pill.critical {{ color:#ef4444; }}

.gg-gauge {{ --p:0; width:170px; height:170px; border-radius:50%; margin:6px auto; display:grid; place-items:center;
  background:conic-gradient(var(--a1) calc(var(--p)*1%), rgba(255,255,255,.08) 0); box-shadow:0 0 34px var(--glow); }}
.gg-gauge .in {{ width:132px; height:132px; border-radius:50%; background:{t['bg1']}; display:grid; place-items:center; text-align:center; }}
.gg-gauge .n {{ font-size:2rem; font-weight:800; }} .gg-gauge .l {{ font-size:.7rem; color:var(--muted); letter-spacing:1px; }}

.gg-bar {{ margin:9px 0; }} .gg-bar .t {{ display:flex; justify-content:space-between; font-size:.84rem; margin-bottom:4px; }}
.gg-bar .tr {{ height:10px; border-radius:99px; background:rgba(255,255,255,.08); overflow:hidden; }}
.gg-bar .fi {{ height:100%; border-radius:99px; background:linear-gradient(90deg,var(--a1),var(--a2)); box-shadow:0 0 12px var(--glow); }}

.gg-note {{ border:1px dashed var(--line); border-radius:14px; padding:10px 14px; color:var(--muted); font-size:.85rem; }}
.gg-brief {{ border:1px solid var(--a2); border-radius:16px; padding:16px 18px; background:rgba(255,255,255,.04); line-height:1.6; }}

/* Streamlit widgets */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; background:var(--card); padding:6px; border-radius:16px; border:1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ height:44px; border-radius:12px; padding:0 18px; font-weight:600; color:var(--muted); }}
.stTabs [aria-selected="true"] {{ background:linear-gradient(90deg,var(--a1),var(--a2)); color:#04101c !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
.stButton>button, .stDownloadButton>button {{ border-radius:12px; font-weight:700; border:1px solid var(--line);
  transition:all .2s; }}
.stButton>button[kind="primary"] {{ background:linear-gradient(90deg,var(--a1),var(--a2)); color:#04101c; border:none;
  box-shadow:0 6px 22px var(--glow); }}
.stButton>button:hover, .stDownloadButton>button:hover {{ transform:translateY(-2px); box-shadow:0 8px 24px var(--glow); }}
div[data-testid="stExpander"] {{ border:1px solid var(--line); border-radius:14px; background:var(--card); }}

/* ===== VISIBILITY FIX: force readable text on every Streamlit widget ===== */
:root, html, body {{ color-scheme: dark; }}
.stApp, .stApp p, .stApp span, .stApp li, .stApp label, .stApp small, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp div[data-testid="stMarkdownContainer"], .stApp div[data-testid="stMarkdownContainer"] * {{ color:{t['text']}; }}
/* widget labels (Case input, City, Area type, Your name, Units..., Describe the problem...) */
.stApp [data-testid="stWidgetLabel"], .stApp [data-testid="stWidgetLabel"] *,
.stApp label, .stApp label *, .stApp [data-testid="stFileUploader"] label, .stApp [data-testid="stFileUploader"] small,
.stApp [data-testid="stFileUploaderDropzoneInstructions"] *, .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] * {{
  color:{t['text']} !important; opacity:1 !important; }}
section[data-testid="stSidebar"], section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] label *, section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] * {{
  color:{t['text']} !important; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h2 *, section[data-testid="stSidebar"] h3 * {{ color:{t['a1']} !important; }}
/* radio options (Rules engine / CrewAI crew) */
.stApp [data-testid="stRadio"] label, .stApp [data-testid="stRadio"] label p, .stApp [data-testid="stRadio"] div[role="radiogroup"] * {{
  color:{t['text']} !important; opacity:1 !important; }}
/* tabs (Investigate, Agent Trace, Analytics, ...) */
.stTabs [data-baseweb="tab"], .stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span, .stTabs [data-baseweb="tab"] div {{
  color:{t['text']} !important; opacity:1 !important; }}
.stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] span, .stTabs [aria-selected="true"] div {{
  color:#04101c !important; }}
/* buttons: secondary buttons readable, primary keeps dark text on gradient */
.stButton>button, .stDownloadButton>button {{ color:{t['text']} !important; background:rgba(255,255,255,.06); }}
.stButton>button *, .stDownloadButton>button * {{ color:inherit !important; }}
.stButton>button[kind="primary"], .stButton>button[kind="primary"] * {{ color:#04101c !important; }}
/* expanders, alerts, toasts, tooltips */
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary *, div[data-testid="stExpander"] p {{ color:{t['text']} !important; }}
div[data-testid="stAlert"] {{ background:rgba(255,255,255,.07) !important; border:1px solid {t['line']}; }}
div[data-testid="stAlert"], div[data-testid="stAlert"] * {{ color:{t['text']} !important; }}
div[data-testid="stToast"], div[data-testid="stToast"] * {{ color:{t['text']} !important; }}
div[data-testid="stToast"] {{ background:{t['bg2']} !important; }}
div[data-baseweb="tooltip"] *, div[data-testid="stTooltipContent"] * {{ color:{t['text']} !important; }}
div[data-baseweb="tooltip"] > div, div[data-testid="stTooltipContent"] {{ background:{t['bg2']} !important; }}
/* JSON viewer inside expanders: dark panel + light text */
div[data-testid="stJson"] {{ background:rgba(0,0,0,.35) !important; border-radius:12px; padding:8px; }}
div[data-testid="stJson"] * {{ color:{t['text']} !important; }}
/* custom dashboard components keep their own colours */
.gg-kpi .vl, .gg-hero h1 {{ color:transparent !important; }}
.gg-kpi .lb, .gg-kpi .sb, .gg-hero p, .gg-agent .as, .gg-agent .am, .gg-note, .gg-gauge .l {{ color:{t['muted']} !important; }}
.gg-step {{ color:{t['text']} !important; }}
.gg-step .si {{ filter:none !important; opacity:1 !important; }}
.gg-step.done .si {{ filter:drop-shadow(0 0 6px {t['glow']}) !important; }}
.gg-pill.info {{ color:#34d399 !important; }} .gg-pill.warn {{ color:#f59e0b !important; }} .gg-pill.critical {{ color:#ef4444 !important; }}

/* ===== DATA-ENTRY BOXES: solid, high-contrast (yellow box + black text by default) ===== */
.stApp div[data-baseweb="input"], .stApp div[data-baseweb="base-input"], .stApp div[data-baseweb="textarea"],
.stApp div[data-baseweb="select"] > div, .stApp [data-testid="stNumberInputContainer"],
.stApp [data-testid="stTextInputRootElement"], .stApp [data-testid="stTextAreaRootElement"] {{
  background:{i['bg']} !important; border:2px solid {i['border']} !important; border-radius:12px !important; }}
.stApp div[data-baseweb="input"]:focus-within, .stApp div[data-baseweb="textarea"]:focus-within,
.stApp div[data-baseweb="select"] > div:focus-within {{ box-shadow:0 0 0 3px {t['glow']}, 0 0 14px {t['glow']} !important; }}
.stApp div[data-baseweb="input"] input, .stApp div[data-baseweb="base-input"] input, .stApp div[data-baseweb="textarea"] textarea,
.stApp [data-testid="stNumberInputContainer"] input, .stApp input[type="text"], .stApp input[type="password"],
.stApp input[type="number"], .stApp textarea {{
  background:transparent !important; color:{i['text']} !important; -webkit-text-fill-color:{i['text']} !important;
  caret-color:{i['text']} !important; font-weight:600 !important; opacity:1 !important; }}
.stApp input::placeholder, .stApp textarea::placeholder {{
  color:{i['placeholder']} !important; -webkit-text-fill-color:{i['placeholder']} !important; opacity:1 !important; }}
/* dropdown (selectbox) current value + arrow */
.stApp div[data-baseweb="select"] *, .stApp div[data-baseweb="select"] span, .stApp div[data-baseweb="select"] div {{
  color:{i['text']} !important; -webkit-text-fill-color:{i['text']} !important; font-weight:600; }}
.stApp div[data-baseweb="select"] svg, .stApp [data-testid="stNumberInputContainer"] svg,
.stApp div[data-baseweb="input"] svg {{ fill:{i['text']} !important; color:{i['text']} !important; }}
/* number +/- buttons and password eye button */
.stApp [data-testid="stNumberInputContainer"] button, .stApp div[data-baseweb="input"] button {{
  background:rgba(0,0,0,.14) !important; border:none !important; color:{i['text']} !important; }}
.stApp [data-testid="stNumberInputContainer"] button:hover {{ background:{i['hover']} !important; }}
/* dropdown list (opens in a portal outside .stApp) */
div[data-baseweb="popover"], div[data-baseweb="popover"] > div, div[data-baseweb="popover"] ul, ul[role="listbox"],
div[data-baseweb="menu"] {{ background:{i['bg']} !important; border:2px solid {i['border']}; border-radius:12px; }}
div[data-baseweb="popover"] li, div[data-baseweb="popover"] li *, ul[role="listbox"] li, ul[role="listbox"] li *,
div[data-baseweb="menu"] li, div[data-baseweb="menu"] li * {{
  background:transparent !important; color:{i['text']} !important; -webkit-text-fill-color:{i['text']} !important; font-weight:600; }}
div[data-baseweb="popover"] li:hover, ul[role="listbox"] li:hover, ul[role="listbox"] li[aria-selected="true"] {{
  background:{i['hover']} !important; }}
/* file uploader */
.stApp [data-testid="stFileUploaderDropzone"] {{ background:{i['bg']} !important; border:2px dashed {i['border']} !important; border-radius:12px; }}
.stApp [data-testid="stFileUploaderDropzone"], .stApp [data-testid="stFileUploaderDropzone"] *,
.stApp [data-testid="stFileUploaderDropzoneInstructions"], .stApp [data-testid="stFileUploaderDropzoneInstructions"] * {{
  color:{i['text']} !important; -webkit-text-fill-color:{i['text']} !important; }}
.stApp [data-testid="stFileUploaderDropzone"] svg {{ fill:{i['text']} !important; }}
.stApp [data-testid="stFileUploaderDropzone"] button {{ background:{i['text']} !important; border:none !important; }}
.stApp [data-testid="stFileUploaderDropzone"] button, .stApp [data-testid="stFileUploaderDropzone"] button * {{
  color:{i['bg']} !important; -webkit-text-fill-color:{i['bg']} !important; }}

/* ===== Bill Center ===== */
.gg-table {{ width:100%; border-collapse:collapse; font-size:.92rem; }}
.gg-table th {{ text-align:left; color:{t['a1']}; font-size:.75rem; letter-spacing:1px; text-transform:uppercase; padding:6px 8px; border-bottom:1px solid var(--line); }}
.gg-table td {{ padding:8px; border-bottom:1px solid var(--line); color:{t['text']}; }}
.gg-table td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.gg-table tr.tot td {{ font-weight:800; border-bottom:none; color:{t['a1']} !important; font-size:1.02rem; }}
.gg-steps-list {{ margin:10px 0; padding-left:20px; line-height:1.7; color:{t['text']}; }}
.gg-chips2 {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:6px; }}
.stApp [data-testid="stBaseLinkButton-primary"], .stApp [data-testid="stBaseLinkButton-secondary"], .stApp .stLinkButton a {{
  border-radius:12px !important; font-weight:700 !important; border:1px solid var(--line) !important; }}
.stApp [data-testid="stBaseLinkButton-primary"], .stApp [data-testid="stBaseLinkButton-primary"] * {{
  background:linear-gradient(90deg,var(--a1),var(--a2)) !important; color:#04101c !important; border:none !important; }}
.stApp [data-testid="stBaseLinkButton-secondary"], .stApp [data-testid="stBaseLinkButton-secondary"] * {{ color:{t['text']} !important; }}

/* split bar */
.gg-splitbar {{ display:flex; height:16px; border-radius:99px; overflow:hidden; margin:4px 0 12px; background:rgba(255,255,255,.08); }}
.gg-splitbar .seg {{ height:100%; }}
.k-energy {{ background:{t['a1']}; }} .k-fixed {{ background:{t['a2']}; }} .k-adjust {{ background:#f59e0b; }}
.k-surcharge {{ background:#a78bfa; }} .k-tax {{ background:#34d399; }} .k-unexplained {{ background:#ef4444; }}
.dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; }}
.gg-table tr.r-unexplained td {{ color:#fca5a5 !important; font-weight:700; }}

/* ===== Bill intelligence / audit visibility ===== */
.gg-bill-dashboard {{ border-color:rgba(56,189,248,.38); box-shadow:0 0 28px rgba(56,189,248,.10); }}
.gg-bill-head {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:10px; }}
.gg-bill-head h3 {{ margin:0; font-size:1.12rem; }}
.gg-muted {{ color:var(--muted); font-size:.78rem; }}
.gg-status {{ border:1px solid rgba(52,211,153,.45); color:#34d399; border-radius:999px; padding:5px 10px; font-weight:800; font-size:.72rem; }}
.gg-mini-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:8px 0; }}
.gg-mini-grid > div {{ padding:10px 11px; border:1px solid var(--line); border-radius:12px; background:rgba(255,255,255,.035); }}
.gg-mini-grid b,.gg-mini-grid span,.gg-mini-grid small {{ display:block; }}
.gg-mini-grid b {{ color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.7px; }}
.gg-mini-grid span {{ font-size:1.15rem; font-weight:800; margin-top:3px; }}
.gg-mini-grid small {{ color:var(--muted); font-size:.67rem; margin-top:2px; }}
.gg-rate-strip {{ display:flex; flex-wrap:wrap; gap:7px; margin:9px 0 12px; }}
.gg-rate-strip span {{ padding:5px 8px; border:1px solid var(--line); border-radius:8px; font-size:.68rem; color:var(--muted); }}
.gg-rate-strip b {{ color:var(--text); }}
.gg-mini-tag {{ font-size:.58rem; letter-spacing:.7px; color:var(--muted); }}
.gg-evidence-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:7px; margin-top:10px; }}
.gg-evidence-grid > div {{ border:1px dashed var(--line); border-radius:9px; padding:7px; font-size:.7rem; }}
.gg-evidence-grid small {{ color:var(--muted); }}
@media (max-width: 900px) {{
 .gg-mini-grid,.gg-evidence-grid {{ grid-template-columns:repeat(2,1fr); }}
}}
@media (max-width: 600px) {{
 .gg-mini-grid,.gg-evidence-grid {{ grid-template-columns:1fr; }}
}}

</style>
"""
