"""
US Economy Pulse — Streamlit Dashboard
Connects to Supabase PostgreSQL and visualizes US economic indicators.
"""

import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="US Economy Pulse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.block-container { padding-top: 0 !important; padding-bottom: 3rem !important; max-width: 1400px !important; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #f0f7ff 0%, #e0efff 55%, #f0f7ff 100%);
    border-bottom: 1px solid rgba(76,155,232,0.15);
    padding: 40px 4px 30px;
    margin: 0 -4rem 2rem -4rem;
    position: relative; overflow: hidden;
}
.hero::before {
    content: ''; position: absolute; top: -120px; left: -80px;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(76,155,232,0.12) 0%, transparent 65%);
    pointer-events: none;
}
.hero::after {
    content: ''; position: absolute; bottom: -80px; right: 5%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(129,140,248,0.1) 0%, transparent 65%);
    pointer-events: none;
}
.hero-title {
    font-size: 2.4rem; font-weight: 800; letter-spacing: -0.035em;
    line-height: 1.05; margin: 0 0 8px 0; color: #0a2351;
}
.hero-title .grad {
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero-sub { color: #5a7a95; font-size: 0.9rem; font-weight: 400; margin: 0 0 22px 0; }
.hero-badges { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.badge-live {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.25);
    border-radius: 20px; padding: 5px 14px;
    font-size: 0.7rem; font-weight: 700; color: #22c55e;
    text-transform: uppercase; letter-spacing: 0.07em;
}
.dot-live {
    width: 7px; height: 7px; background: #22c55e; border-radius: 50%;
    animation: livepulse 2.2s ease-in-out infinite;
}
@keyframes livepulse {
    0%,100% { opacity:1; box-shadow: 0 0 0 0 rgba(34,197,94,0.5); }
    50%      { opacity:0.6; box-shadow: 0 0 0 5px rgba(34,197,94,0); }
}
.badge-run {
    font-size: 0.72rem; color: #5a7a95;
    background: rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.08);
    border-radius: 20px; padding: 5px 14px;
}

/* ── KPI cards ── */
.kpi-row { display: grid; grid-template-columns: repeat(5,1fr); gap: 14px; margin-bottom: 6px; }
.kpi-card {
    background: #ffffff; border: 1px solid #e5ecf2;
    border-radius: 14px; padding: 20px 18px 16px;
    position: relative; overflow: hidden;
    transition: border-color .25s, box-shadow .25s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.kpi-card:hover { border-color: #4c9be8; box-shadow: 0 4px 12px rgba(76,155,232,0.15); }
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #4c9be8, #818cf8); border-radius: 14px 14px 0 0;
}
.kpi-card.c-green::before  { background: linear-gradient(90deg,#22c55e,#16a34a); }
.kpi-card.c-yellow::before { background: linear-gradient(90deg,#eab308,#ca8a04); }
.kpi-card.c-orange::before { background: linear-gradient(90deg,#f97316,#ea580c); }
.kpi-card.c-red::before    { background: linear-gradient(90deg,#ef4444,#dc2626); }
.kpi-lbl {
    font-size: 0.62rem; font-weight: 700; color: #7a8fa0;
    text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 10px;
}
.kpi-val { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1; margin-bottom: 10px; letter-spacing: -0.03em; }
.kpi-dl { font-size: 0.74rem; font-weight: 600; padding: 3px 9px; border-radius: 6px; display: inline-block; }
.kpi-dl.pos  { color: #22c55e; background: rgba(34,197,94,0.1); }
.kpi-dl.neg  { color: #ef4444; background: rgba(239,68,68,0.1); }
.kpi-dl.info { color: #7a8fa0; background: rgba(122,143,160,0.1); }
.kpi-sub { font-size: 0.71rem; color: #7a8fa0; margin-top: 7px; }
.period-note { font-size: 0.68rem; color: #a5b4c1; margin: 5px 0 24px 2px; letter-spacing: 0.01em; }

/* ── Economy Snapshot card ── */
.snapshot {
    background: #ffffff; border: 1px solid #e5ecf2;
    border-radius: 16px; padding: 24px 28px; margin-bottom: 8px;
    position: relative; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.snapshot::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #4c9be8 0%, #818cf8 50%, #4c9be8 100%);
}
.snap-title {
    font-size: 0.7rem; font-weight: 700; color: #7a8fa0;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
}
.snap-status {
    font-size: 1.05rem; font-weight: 600; color: #0f172a;
    margin-bottom: 12px; line-height: 1.5;
}
.snap-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 14px; }
.snap-col-title { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
.snap-col-title.green { color: #16a34a; }
.snap-col-title.red   { color: #dc2626; }
.snap-col-title.blue  { color: #3b82f6; }
.snap-item { font-size: 0.82rem; color: #5a7a95; margin-bottom: 5px; padding-left: 12px; position: relative; }
.snap-item::before { content: '·'; position: absolute; left: 0; color: #a5b4c1; }
.snap-action {
    margin-top: 16px; padding-top: 14px; border-top: 1px solid #e5ecf2;
    font-size: 0.82rem; color: #5a7a95; line-height: 1.6;
}
.snap-action strong { color: #2c5a9a; font-weight: 600; }

/* ── Section headers ── */
.sec-hdr { display: flex; align-items: center; gap: 10px; margin: 8px 0 4px 0; }
.sec-bar { width: 3px; height: 18px; border-radius: 2px; flex-shrink: 0; background: linear-gradient(180deg,#4c9be8,#818cf8); }
.sec-txt { font-size: 1.05rem; font-weight: 600; color: #0f172a; letter-spacing: -0.01em; }

/* ── Divider ── */
.sec-div { height: 1px; background: linear-gradient(to right,#e5ecf2,transparent); margin: 24px 0; }

footer, #MainMenu, header { visibility: hidden !important; }
</style>
""", unsafe_allow_html=True)


# ── DB connection ───────────────────────────────────────────────────────────────
def _get_secret(key, fallback_keys=None):
    """Try [supabase] section first, then top-level keys, then env vars."""
    import os
    # 1. Try nested [supabase] section
    try:
        return st.secrets["supabase"][key]
    except (KeyError, Exception):
        pass
    # 2. Try top-level secret with the same key name
    try:
        return st.secrets[key]
    except (KeyError, Exception):
        pass
    # 3. Try alternate key names passed in
    for alt in (fallback_keys or []):
        try:
            return st.secrets[alt]
        except (KeyError, Exception):
            pass
        if os.environ.get(alt):
            return os.environ[alt]
    # 4. Try env vars
    return os.environ.get(key.upper(), "")



def _run_query(sql: str) -> pd.DataFrame:
    """Execute a single query — reads secrets fresh every time."""
    host     = str(_get_secret("host",     ["SUPABASE_HOST", "DBT_HOST"]))
    port     = int(_get_secret("port",     ["SUPABASE_PORT", "DBT_PORT"]) or 6543)
    dbname   = str(_get_secret("dbname",   ["SUPABASE_DBNAME", "DBT_DATABASE"]) or "postgres")
    user     = str(_get_secret("user",     ["SUPABASE_USER", "DBT_USER"]))
    password = str(_get_secret("password", ["SUPABASE_PASSWORD", "DBT_PASSWORD"]))

    if not host or not password:
        raise RuntimeError("Missing Supabase credentials in secrets.")

    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password,
        sslmode="require", connect_timeout=15,
    )
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


# ── Schema + queries ─────────────────────────────────────────────────────────────
# Supabase transaction pooler (PgBouncer) ignores search_path options,
# so we use fully qualified schema.table names in every query.
_S = _get_secret("schema", ["SUPABASE_SCHEMA", "DBT_SCHEMA"]) or "public_analytics"

QUERIES = {
    "overview": f"SELECT * FROM {_S}.vw_economic_overview_dashboard LIMIT 1",
    "inflation": (
        "SELECT period_date_key, year_month, yoy_inflation_rate_pct, "
        "mom_inflation_change_pct, inflation_severity_category, "
        "fedfunds_rate_pct, fed_policy_stance_to_inflation "
        f"FROM {_S}.fct_inflation_analysis "
        "WHERE period_date_key > '1999-12-31' "
        "ORDER BY period_date_key"
    ),
    "recession": (
        "SELECT period_date_key, year_quarter, gdp_billions_usd, "
        "qoq_growth_pct, unemployment_rate_pct, yoy_inflation_rate_pct, "
        "recession_risk_level, recession_intensity_score, "
        "consecutive_negative_quarters "
        f"FROM {_S}.fct_recession_analysis "
        "WHERE period_date_key > '1999-12-31' "
        "ORDER BY period_date_key"
    ),
    "employment": (
        "SELECT period_date_key, year_month, unemployment_rate_pct, "
        "unemployment_yoy_change_pct, unemployment_trend, "
        "housing_starts_thousands, labor_market_health_score, "
        "labor_market_condition "
        f"FROM {_S}.fct_employment_analysis "
        "WHERE period_date_key > '1999-12-31' "
        "ORDER BY period_date_key"
    ),
}


@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data() -> dict:
    """Fetch all four datasets in parallel threads."""
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_run_query, sql): name for name, sql in QUERIES.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                st.warning(f"Could not load {name}: {e}")
                results[name] = pd.DataFrame()
    return results


def load_overview(data) -> pd.Series:
    df = data.get("overview", pd.DataFrame())
    return df.iloc[0] if not df.empty else pd.Series()


def load_inflation_history(data) -> pd.DataFrame:
    return data.get("inflation", pd.DataFrame())


def load_recession_history(data) -> pd.DataFrame:
    return data.get("recession", pd.DataFrame())


def load_employment_history(data) -> pd.DataFrame:
    return data.get("employment", pd.DataFrame())


# ── Color helpers ───────────────────────────────────────────────────────────────
RISK_COLORS = {"Low": "#22c55e", "Emerging": "#eab308", "Moderate": "#f97316", "High": "#ef4444"}
SEVERITY_COLORS = {"Mild": "#22c55e", "Moderate": "#eab308", "High": "#f97316", "Severe": "#ef4444"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#c9d1d9", family="Inter, sans-serif", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="#21262d", showline=False, zeroline=False),
    yaxis=dict(gridcolor="#21262d", showline=False, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
    hovermode="x unified",
)


def apply_layout(fig, **kwargs):
    layout = {**PLOTLY_LAYOUT, **kwargs}
    fig.update_layout(**layout)
    return fig


# ── UI helpers ──────────────────────────────────────────────────────────────────
def sec_header(title):
    st.markdown(
        f'<div class="sec-hdr"><div class="sec-bar"></div><div class="sec-txt">{title}</div></div>',
        unsafe_allow_html=True,
    )

def sec_div():
    st.markdown('<div class="sec-div"></div>', unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">US Economy <span class="grad">Pulse</span></div>
  <div class="hero-sub">Live indicators from FRED · Transformed with dbt · Updated weekly</div>
  <div class="hero-badges">
    <span class="badge-live"><span class="dot-live"></span>Live</span>
  </div>
</div>
""", unsafe_allow_html=True)

with st.spinner("Loading latest data..."):
    _data = load_all_data()
    ov   = load_overview(_data)
    infl = load_inflation_history(_data)
    rec  = load_recession_history(_data)
    emp  = load_employment_history(_data)

if ov.empty:
    st.error("No data found. Make sure the pipeline has run and the views exist in Supabase.")
    st.stop()

# Append "last run" badge into hero area
last_updated = ov.get("dbt_loaded_at", "")
if last_updated:
    try:
        ts = pd.to_datetime(last_updated)
        st.markdown(
            f"<div style='margin:-18px 0 20px 2px'>"
            f"<span class='badge-run'>Last pipeline run: {ts.strftime('%b %d, %Y · %H:%M UTC')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

# ── KPI row ─────────────────────────────────────────────────────────────────────
def _pct(v, d=1):
    try: return f"{float(v):.{d}f}%"
    except: return "N/A"

def _dl(val, invert=False, label=None):
    if label is not None:
        return f'<span class="kpi-dl info">{label}</span>'
    try:
        v = float(val)
        good = (v < 0) if invert else (v > 0)
        cls  = "pos" if good else "neg"
        arr  = "↑" if v > 0 else "↓"
        return f'<span class="kpi-dl {cls}">{arr} {abs(v):.1f}%</span>'
    except:
        return '<span class="kpi-dl info">—</span>'

risk        = str(ov.get("recession_risk_level", "Unknown"))
score       = ov.get("recession_intensity_score", "—")
sev         = str(ov.get("inflation_severity_category", ""))
fed_dir     = str(ov.get("fedfunds_direction", ""))
_rmap       = {"Low":"c-green","Emerging":"c-yellow","Moderate":"c-orange","High":"c-red"}
risk_cls    = _rmap.get(risk, "")

try:
    _gdp_cls = "" if float(ov.get("qoq_growth_pct", 0) or 0) >= 0 else "c-red"
except: _gdp_cls = ""
try:
    _uchg = float(ov.get("unemployment_yoy_change_pct", 0) or 0)
    _unemp_cls = "c-red" if _uchg > 1.5 else "c-yellow" if _uchg > 0.5 else ""
except: _unemp_cls = ""

_q_period = rec["year_quarter"].iloc[-1] if not rec.empty else ""
_m_period = infl["year_month"].iloc[-1] if not infl.empty else ""
_period_txt = " · ".join(filter(None, [
    f"GDP & recession: {_q_period}" if _q_period else "",
    f"inflation, employment & rates: {_m_period}" if _m_period else "",
]))

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card {_gdp_cls}">
    <div class="kpi-lbl">Real GDP Growth (QoQ)</div>
    <div class="kpi-val">{_pct(ov.get("qoq_growth_pct"))}</div>
    {_dl(ov.get("qoq_growth_pct"))}
  </div>
  <div class="kpi-card">
    <div class="kpi-lbl">Inflation (YoY)</div>
    <div class="kpi-val">{_pct(ov.get("yoy_inflation_rate_pct"))}</div>
    {_dl(None, label=sev) if sev else ""}
  </div>
  <div class="kpi-card {_unemp_cls}">
    <div class="kpi-lbl">Unemployment Rate</div>
    <div class="kpi-val">{_pct(ov.get("unemployment_rate_pct"))}</div>
    {_dl(ov.get("unemployment_yoy_change_pct"), invert=True)}
  </div>
  <div class="kpi-card">
    <div class="kpi-lbl">Fed Funds Rate</div>
    <div class="kpi-val">{_pct(ov.get("fedfunds_rate_pct"))}</div>
    {_dl(None, label=fed_dir) if fed_dir else ""}
  </div>
  <div class="kpi-card {risk_cls}">
    <div class="kpi-lbl">Recession Risk</div>
    <div class="kpi-val">{risk}</div>
    <div class="kpi-sub">Intensity: {score} / 15</div>
  </div>
</div>
{"<div class='period-note'>Latest data — " + _period_txt + "</div>" if _period_txt else ""}
""", unsafe_allow_html=True)

sec_div()

# ── Economy Snapshot ────────────────────────────────────────────────────────────
def _build_snapshot(ov, rec, infl):
    """Synthesise all indicators into a plain-English big-picture card."""
    risk      = str(ov.get("recession_risk_level", "Unknown"))
    score     = ov.get("recession_intensity_score", 1)
    positives, concerns, signals = [], [], []

    # GDP
    try:
        g = float(ov.get("qoq_growth_pct", 0) or 0)
        if g > 0.5:   positives.append(f"GDP is growing (+{g:.1f}% QoQ)")
        elif g > 0:   signals.append(f"GDP growth is modest but positive (+{g:.1f}% QoQ)")
        else:         concerns.append(f"GDP contracted this quarter ({g:.1f}% QoQ)")
    except: pass

    # Unemployment
    try:
        u   = float(ov.get("unemployment_rate_pct", 0) or 0)
        uc  = float(ov.get("unemployment_yoy_change_pct", 0) or 0)
        if u < 4.5 and uc < 0.5:  positives.append(f"unemployment near historical lows ({u:.1f}%)")
        elif uc > 1.5:             concerns.append(f"unemployment rising fast (+{uc:.1f}% YoY) — a classic early-recession signal")
        elif uc > 0:               signals.append(f"unemployment ticking up ({u:.1f}%, +{uc:.1f}% YoY) — worth watching")
        else:                      positives.append(f"unemployment stable at {u:.1f}%")
    except: pass

    # Inflation
    try:
        inf = float(ov.get("yoy_inflation_rate_pct", 0) or 0)
        if inf <= 2.5:   positives.append(f"inflation near the Fed's 2% target ({inf:.1f}% YoY)")
        elif inf <= 4.0: signals.append(f"inflation is moderating but still elevated ({inf:.1f}% YoY)")
        else:            concerns.append(f"inflation running hot at {inf:.1f}% — above the 2% target")
    except: pass

    # Fed funds
    try:
        fed = float(ov.get("fedfunds_rate_pct", 0) or 0)
        fd  = str(ov.get("fedfunds_direction", ""))
        if fd == "Falling":   signals.append(f"Fed cutting rates ({fed:.1f}%) — easing financial conditions")
        elif fd == "Rising":  concerns.append(f"Fed raising rates ({fed:.1f}%) — tightening credit conditions")
        else:                 signals.append(f"Fed holding rates steady at {fed:.1f}%")
    except: pass

    # Overall verdict
    verdict_map = {
        "Low":      ("🟢", "Economy looks healthy.", "No recession signals. Growth is on track and conditions are stable."),
        "Emerging": ("🟡", "Early warning signs are appearing.", "The economy is still growing but cracks are forming. Monitor closely over the next 1–2 quarters."),
        "Moderate": ("🟠", "Multiple caution signals active.", "Several indicators are deteriorating simultaneously. Historically, this pattern precedes slowdowns within 6–12 months."),
        "High":     ("🔴", "Conditions consistent with recession.", "Most indicators are flashing red. Historical patterns suggest elevated probability of contraction."),
    }
    icon, headline, detail = verdict_map.get(risk, ("⚪", "Data unavailable.", ""))

    # Action implications
    action_map = {
        "Low":      "For investors: risk assets typically perform well in this environment. For businesses: a reasonable time to plan expansion. For consumers: labor market is supportive.",
        "Emerging": "For investors: consider reviewing portfolio defensiveness. For businesses: revisit hiring and capex plans. For policymakers: pre-emptive monitoring warranted.",
        "Moderate": "For investors: consider tilting toward defensive sectors (utilities, healthcare, consumer staples). For businesses: conserve cash, delay non-essential capex. For policymakers: stimulus tools should be on standby.",
        "High":     "For investors: defensive positioning advised — bonds, cash, defensive equities. For businesses: protect margins, freeze non-critical hiring. For policymakers: coordinated fiscal and monetary response may be needed.",
    }
    action = action_map.get(risk, "")

    return icon, headline, detail, positives, concerns, signals, action

_icon, _headline, _detail, _pos, _con, _sig, _action = _build_snapshot(ov, rec, infl)

_pos_html = "".join(f'<div class="snap-item">{p}</div>' for p in _pos)
_con_html = "".join(f'<div class="snap-item">{c}</div>' for c in _con)
_sig_html = "".join(f'<div class="snap-item">{s}</div>' for s in _sig)

_pos_section = f"<div class='snap-col-title green'>✓ What's working</div>{_pos_html}" if _pos else ""
_sig_section = f"<div class='snap-col-title blue' style='margin-top:10px'>→ Neutral signals</div>{_sig_html}" if _sig else ""
_con_section = f"<div class='snap-col-title red'>⚠ Concerns</div>{_con_html}" if _con else ""
_action_section = f"<div class='snap-action'><strong>What this means →</strong> {_action}</div>" if _action else ""

snapshot_html = f"""
<div class="snapshot">
  <div class="snap-title">📡 Economy Snapshot</div>
  <div class="snap-status">{_icon} <strong>{_headline}</strong> {_detail}</div>
  <div class="snap-cols">
    <div>{_pos_section}{_sig_section}</div>
    <div>{_con_section}</div>
  </div>
  {_action_section}
</div>
"""

st.markdown(snapshot_html, unsafe_allow_html=True)

sec_div()

# ── Row 1: GDP (full width) ─────────────────────────────────────────────────────
sec_header("GDP Growth — Quarter over Quarter")
if not rec.empty:
    colors = ["#ef4444" if v < 0 else "#4c9be8" for v in rec["qoq_growth_pct"].fillna(0)]
    fig = go.Figure(go.Bar(
        x=rec["year_quarter"],
        y=rec["qoq_growth_pct"],
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>QoQ Growth: %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#555", line_width=1)
    apply_layout(fig, title="", height=320)
    fig.update_xaxes(
        tickmode="array",
        tickvals=[q for q in rec["year_quarter"] if q.endswith("-Q1")],
        ticktext=[q.split("-")[0] for q in rec["year_quarter"] if q.endswith("-Q1")],
        tickangle=0,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── Row 1b: Recession Risk timeline strip ───────────────────────────────────────
sec_header("Recession Risk — Quarter by Quarter")
if not rec.empty:
    bar_colors = rec["recession_risk_level"].map(RISK_COLORS).fillna("#8b9ab3")

    fig_risk = go.Figure()
    # One bar per quarter, uniform height, colored by risk level
    fig_risk.add_trace(go.Bar(
        x=rec["year_quarter"],
        y=[1] * len(rec),
        marker_color=bar_colors.tolist(),
        customdata=rec["recession_risk_level"],
        hovertemplate="<b>%{x}</b><br>Risk: %{customdata}<extra></extra>",
        showlegend=False,
    ))
    # Dummy traces for legend only
    for label, color in RISK_COLORS.items():
        fig_risk.add_trace(go.Bar(x=[None], y=[None], name=label, marker_color=color))

    fig_risk.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis", "xaxis", "margin", "legend", "hovermode")},
        barmode="stack",
        bargap=0.05,
        height=130,
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        xaxis=dict(
            gridcolor="#21262d", showline=False, zeroline=False,
            tickangle=-45, tickfont=dict(size=10),
            tickmode="array",
            tickvals=[q for q in rec["year_quarter"] if q.endswith("-Q1")],
            ticktext=[q.split("-")[0] for q in rec["year_quarter"] if q.endswith("-Q1")],
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                    orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=40, b=70),
    )
    st.plotly_chart(fig_risk, use_container_width=True, config={"displayModeBar": False})

    risk_summary = ov.get("risk_assessment_summary", "")
    if risk_summary:
        color = RISK_COLORS.get(risk, "#8b9ab3")
        st.markdown(
            f"<div style='background:#1c2333; border-left:4px solid {color}; "
            f"border-radius:8px; padding:12px 16px; font-size:0.85rem; color:#c9d1d9; "
            f"margin-top:8px;'>{risk_summary}</div>",
            unsafe_allow_html=True,
        )

sec_div()

# ── Row 2: Inflation + Fed Funds ────────────────────────────────────────────────
sec_header("Inflation & Monetary Policy")
if not infl.empty:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=infl["period_date_key"],
        y=infl["yoy_inflation_rate_pct"],
        name="Inflation (YoY %)",
        line=dict(color="#f97316", width=2),
        hovertemplate="%{y:.2f}%<extra>Inflation</extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=infl["period_date_key"],
        y=infl["fedfunds_rate_pct"],
        name="Fed Funds Rate",
        line=dict(color="#4c9be8", width=2, dash="dot"),
        hovertemplate="%{y:.2f}%<extra>Fed Funds</extra>",
    ), secondary_y=True)

    fig.add_hline(y=2.0, line_color="#22c55e", line_width=1, line_dash="dash",
                  annotation_text="2% target", annotation_position="top right",
                  annotation_font_color="#22c55e")

    fig.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis",)},
        height=340,
        yaxis=dict(gridcolor="#21262d", showline=False, zeroline=False, title="Inflation %"),
        yaxis2=dict(gridcolor="rgba(0,0,0,0)", showline=False, zeroline=False,
                    title="Fed Funds %", overlaying="y", side="right"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

sec_div()

# ── Row 3: Unemployment + Housing ───────────────────────────────────────────────
col_unemp, col_house = st.columns(2)

with col_unemp:
    sec_header("Unemployment Rate")
    if not emp.empty:
        trend_color_map = {"Rising": "#ef4444", "Declining": "#22c55e", "Flat": "#eab308"}
        colors = [trend_color_map.get(t, "#4c9be8") for t in emp["unemployment_trend"].fillna("Flat")]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=emp["period_date_key"],
            y=emp["unemployment_rate_pct"],
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(76, 155, 232, 0.1)",
            line=dict(color="#4c9be8", width=2),
            hovertemplate="%{y:.1f}%<extra>Unemployment</extra>",
        ))
        apply_layout(fig, height=300,
                     yaxis=dict(gridcolor="#21262d", showline=False, zeroline=False, title="%"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col_house:
    sec_header("Housing Starts (thousands)")
    if not emp.empty:
        fig = go.Figure(go.Scatter(
            x=emp["period_date_key"],
            y=emp["housing_starts_thousands"],
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(168, 85, 247, 0.1)",
            line=dict(color="#a855f7", width=2),
            hovertemplate="%{y:.0f}K units<extra>Housing Starts</extra>",
        ))
        apply_layout(fig, height=300,
                     yaxis=dict(gridcolor="#21262d", showline=False, zeroline=False, title="Thousands"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

sec_div()

# ── Row 4: Recession intensity score over time ──────────────────────────────────
sec_header("Recession Intensity Score Over Time")
if not rec.empty:
    risk_level_colors = [RISK_COLORS.get(r, "#8b9ab3") for r in rec["recession_risk_level"].fillna("Low")]
    fig = go.Figure(go.Scatter(
        x=rec["period_date_key"],
        y=rec["recession_intensity_score"],
        mode="lines+markers",
        line=dict(color="#4c9be8", width=1.5),
        marker=dict(color=risk_level_colors, size=7, line=dict(width=0)),
        customdata=rec[["recession_risk_level", "year_quarter"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Score: %{y}/15<br>"
            "Risk: %{customdata[0]}<extra></extra>"
        ),
    ))

    # Reference bands
    fig.add_hrect(y0=0, y1=3, fillcolor="rgba(34,197,94,0.06)", line_width=0, annotation_text="Low", annotation_position="right")
    fig.add_hrect(y0=3, y1=6, fillcolor="rgba(234,179,8,0.06)", line_width=0, annotation_text="Emerging", annotation_position="right")
    fig.add_hrect(y0=6, y1=10, fillcolor="rgba(249,115,22,0.06)", line_width=0, annotation_text="Moderate", annotation_position="right")
    fig.add_hrect(y0=10, y1=15, fillcolor="rgba(239,68,68,0.06)", line_width=0, annotation_text="High", annotation_position="right")

    apply_layout(fig, height=300,
                 yaxis=dict(gridcolor="#21262d", showline=False, zeroline=False,
                            title="Intensity (0–15)", range=[0, 15]))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

sec_div()

# ── Data table (expandable) ──────────────────────────────────────────────────────
with st.expander("📋 View raw recession data table", expanded=False):
    if not rec.empty:
        display_cols = ["year_quarter", "gdp_billions_usd", "qoq_growth_pct",
                        "unemployment_rate_pct", "yoy_inflation_rate_pct",
                        "recession_risk_level", "recession_intensity_score"]
        st.dataframe(
            rec[display_cols].sort_values("year_quarter", ascending=False).head(40),
            use_container_width=True,
            hide_index=True,
        )

with st.expander("📋 View raw inflation data table", expanded=False):
    if not infl.empty:
        display_cols = ["year_month", "yoy_inflation_rate_pct", "mom_inflation_change_pct",
                        "inflation_severity_category", "fedfunds_rate_pct",
                        "fed_policy_stance_to_inflation"]
        st.dataframe(
            infl[display_cols].sort_values("year_month", ascending=False).head(40),
            use_container_width=True,
            hide_index=True,
        )

# ── Footer ───────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center; color:#4a5568; font-size:0.75rem; padding:24px 0 8px;'>"
    "Data sourced from <a href='https://fred.stlouisfed.org' style='color:#4c9be8;'>FRED (Federal Reserve Bank of St. Louis)</a> · "
    "Pipeline: dbt + Supabase + GitHub Actions · "
    "Built with Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
