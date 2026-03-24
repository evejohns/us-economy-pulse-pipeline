"""
US Economy Pulse — Streamlit Dashboard
Connects to Supabase PostgreSQL and visualizes US economic indicators.
"""

import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

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
    .main { background-color: #0e1117; }
    .metric-card {
        background: #1c2333;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #4c9be8;
    }
    .risk-high   { border-left-color: #ef4444 !important; }
    .risk-moderate { border-left-color: #f97316 !important; }
    .risk-emerging { border-left-color: #eab308 !important; }
    .risk-low    { border-left-color: #22c55e !important; }
    h1 { font-size: 2rem !important; }
    .stMetric label { font-size: 0.75rem !important; color: #8b9ab3 !important; text-transform: uppercase; letter-spacing: 0.05em; }
    .stMetric .metric-container div { font-size: 1.6rem !important; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── DB connection ───────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_connection():
    s = st.secrets["supabase"]
    return psycopg2.connect(
        host=s["host"],
        port=int(s.get("port", 6543)),
        dbname=s["dbname"],
        user=s["user"],
        password=s["password"],
        sslmode="require",
        connect_timeout=15,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn)


# ── Load data ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_overview() -> pd.Series:
    df = query("SELECT * FROM vw_economic_overview_dashboard LIMIT 1")
    if df.empty:
        return pd.Series()
    return df.iloc[0]


@st.cache_data(ttl=3600, show_spinner=False)
def load_inflation_history() -> pd.DataFrame:
    return query("""
        SELECT period_date_key, year_month, yoy_inflation_rate_pct,
               mom_inflation_change_pct, inflation_severity_category,
               fedfunds_rate_pct, fed_policy_stance_to_inflation
        FROM fct_inflation_analysis
        WHERE period_date_key >= '2000-01-01'
        ORDER BY period_date_key
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def load_recession_history() -> pd.DataFrame:
    return query("""
        SELECT period_date_key, year_quarter, gdp_billions_usd,
               qoq_growth_pct, unemployment_rate_pct, yoy_inflation_rate_pct,
               recession_risk_level, recession_intensity_score,
               consecutive_negative_quarters
        FROM fct_recession_analysis
        WHERE period_date_key >= '2000-01-01'
        ORDER BY period_date_key
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def load_employment_history() -> pd.DataFrame:
    return query("""
        SELECT period_date_key, year_month, unemployment_rate_pct,
               unemployment_yoy_change_pct, unemployment_trend,
               housing_starts_thousands, labor_market_health_score,
               labor_market_condition
        FROM fct_employment_analysis
        WHERE period_date_key >= '2000-01-01'
        ORDER BY period_date_key
    """)


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


# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("## 📊 US Economy Pulse")
st.markdown(
    "<p style='color:#8b9ab3; margin-top:-12px; font-size:0.9rem;'>"
    "Live indicators pulled from FRED · Transformed with dbt · Updated weekly</p>",
    unsafe_allow_html=True,
)

with st.spinner("Loading latest data..."):
    ov = load_overview()

if ov.empty:
    st.error("No data found. Make sure the pipeline has run and the views exist in Supabase.")
    st.stop()

last_updated = ov.get("dbt_loaded_at", "")
if last_updated:
    try:
        ts = pd.to_datetime(last_updated)
        st.caption(f"Last pipeline run: {ts.strftime('%B %d, %Y at %H:%M UTC')}")
    except Exception:
        pass

st.divider()

# ── KPI row ─────────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

def fmt_pct(val, decimals=1):
    try:
        return f"{float(val):.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"

def delta_color(val, invert=False):
    try:
        v = float(val)
        good = v < 0 if invert else v > 0
        return "normal" if good else "inverse"
    except (TypeError, ValueError):
        return "off"

with col1:
    st.metric(
        "Real GDP Growth (QoQ)",
        fmt_pct(ov.get("qoq_growth_pct")),
        delta=fmt_pct(ov.get("qoq_growth_pct")),
        delta_color=delta_color(ov.get("qoq_growth_pct")),
    )

with col2:
    st.metric(
        "Inflation (YoY)",
        fmt_pct(ov.get("yoy_inflation_rate_pct")),
        delta=str(ov.get("inflation_severity_category", "")),
        delta_color="off",
    )

with col3:
    st.metric(
        "Unemployment Rate",
        fmt_pct(ov.get("unemployment_rate_pct")),
        delta=fmt_pct(ov.get("unemployment_yoy_change_pct")),
        delta_color=delta_color(ov.get("unemployment_yoy_change_pct"), invert=True),
    )

with col4:
    st.metric(
        "Fed Funds Rate",
        fmt_pct(ov.get("fedfunds_rate_pct")),
        delta=str(ov.get("fedfunds_direction", "")),
        delta_color="off",
    )

with col5:
    risk = ov.get("recession_risk_level", "Unknown")
    score = ov.get("recession_intensity_score", "—")
    st.metric(
        "Recession Risk",
        str(risk),
        delta=f"Intensity score: {score}",
        delta_color="off",
    )

st.divider()

# ── Row 1: GDP + Recession risk ─────────────────────────────────────────────────
col_gdp, col_risk = st.columns([2, 1])

with col_gdp:
    st.subheader("GDP Growth — Quarter over Quarter")
    rec = load_recession_history()
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
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col_risk:
    st.subheader("Recession Risk")
    if not rec.empty:
        risk_counts = rec["recession_risk_level"].value_counts()
        recent = rec.tail(20)
        risk_recent = recent["recession_risk_level"].value_counts()

        fig = go.Figure(go.Bar(
            x=list(risk_recent.index),
            y=list(risk_recent.values),
            marker_color=[RISK_COLORS.get(r, "#8b9ab3") for r in risk_recent.index],
            hovertemplate="%{x}: %{y} quarters<extra></extra>",
        ))
        apply_layout(fig, title="Last 20 quarters", height=320,
                     yaxis=dict(gridcolor="#21262d", showline=False, zeroline=False, title="Quarters"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    risk_summary = ov.get("risk_assessment_summary", "")
    if risk_summary:
        color = RISK_COLORS.get(risk, "#8b9ab3")
        st.markdown(
            f"<div style='background:#1c2333; border-left:4px solid {color}; "
            f"border-radius:8px; padding:12px 16px; font-size:0.85rem; color:#c9d1d9; "
            f"margin-top:8px;'>{risk_summary}</div>",
            unsafe_allow_html=True,
        )

st.divider()

# ── Row 2: Inflation + Fed Funds ────────────────────────────────────────────────
st.subheader("Inflation & Monetary Policy")
infl = load_inflation_history()

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

st.divider()

# ── Row 3: Unemployment + Housing ───────────────────────────────────────────────
col_unemp, col_house = st.columns(2)

emp = load_employment_history()

with col_unemp:
    st.subheader("Unemployment Rate")
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
    st.subheader("Housing Starts (thousands)")
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

st.divider()

# ── Row 4: Recession intensity score over time ──────────────────────────────────
st.subheader("Recession Intensity Score Over Time")
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

st.divider()

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
