"""
JEM Backorders SLA — Exploratory Data Analysis & Dashboard
==========================================================
Run:  streamlit run dashboard.py
Requirements: streamlit, pandas, plotly
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="JEM Backorders SLA Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
}

/* Header */
.main-header {
    background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.6rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}

/* KPI cards */
.kpi-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    backdrop-filter: blur(10px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(79,70,229,0.3);
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.kpi-label {
    font-size: 0.8rem;
    color: rgba(255,255,255,0.55);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.25rem;
}

/* Section titles */
.section-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: #c4b5fd;
    border-left: 4px solid #7c3aed;
    padding-left: 0.75rem;
    margin: 1.5rem 0 0.75rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(15,15,26,0.9);
    border-right: 1px solid rgba(255,255,255,0.08);
}

.st-emotion-cache-1d391kg { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING & CLEANING
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    csv_path = Path(__file__).parent / "JEM Backorders SLA csv.csv"
    df = pd.read_csv(
        csv_path,
        encoding="utf-8",
        on_bad_lines="skip",
    )

    # ── Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # ── Parse dates  (format: MM/DD/YYYY HH:MM:SS.000 AM/PM)
    date_fmt = "%m/%d/%Y %I:%M:%S.000 %p"
    for col in ["created_date", "reached_bo_date"]:
        df[col] = pd.to_datetime(df[col], format=date_fmt, errors="coerce")

    # ── Numeric cleanup — remove commas from so_amount ("3,771" → 3771)
    if "MAX so_amount" in df.columns:
        df["MAX so_amount"] = (
            df["MAX so_amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

    # ── SLA hours:  reached_bo_date − created_date
    df["sla_hours"] = (
        (df["reached_bo_date"] - df["created_date"])
        .dt.total_seconds()
        / 3600
    )

    # ── Date-only column for daily aggregations
    df["created_day"] = df["created_date"].dt.normalize()

    # ── Boolean flags
    for col in ["IsUnder", "IsAfter"]:
        if col in df.columns:
            df[col] = df[col].map({"T": True, "F": False}).fillna(False)

    return df


df = load_data()

# ─────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Filters")

    # Date range
    min_date = df["created_day"].min()
    max_date = df["created_day"].max()
    date_range = st.date_input(
        "Created Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Manufacturer multi-select
    all_mfrs = sorted(df["item_manufacturer"].dropna().unique())
    sel_mfrs = st.multiselect("Manufacturer(s)", all_mfrs, default=all_mfrs)

    # BO Status
    all_statuses = sorted(df["bo_status"].dropna().unique())
    sel_statuses = st.multiselect("BO Status", all_statuses, default=all_statuses)

    # Field
    all_fields = sorted(df["field"].dropna().unique())
    sel_fields = st.multiselect("Field", all_fields, default=all_fields)

    st.markdown("---")
    st.caption("JEM Backorders SLA · EDA Dashboard")

# ─────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────
if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start, end = min_date, max_date

mask = (
    (df["created_day"] >= start)
    & (df["created_day"] <= end)
    & (df["item_manufacturer"].isin(sel_mfrs))
    & (df["bo_status"].isin(sel_statuses))
    & (df["field"].isin(sel_fields))
)
fdf = df[mask].copy()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<p class="main-header">📦 JEM Backorders SLA Dashboard</p>', unsafe_allow_html=True)
st.markdown(
    f"<p style='color:rgba(255,255,255,0.5); font-size:0.9rem; margin-top:-0.5rem;'>"
    f"Period: {start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')} &nbsp;|&nbsp; "
    f"{len(fdf):,} records &nbsp;|&nbsp; {fdf['tran_id'].nunique():,} unique SOs</p>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# ── SECTION 1 · KPIs
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">Key Metrics</p>', unsafe_allow_html=True)

n_so   = fdf["tran_id"].nunique()
n_mfr  = fdf["item_manufacturer"].nunique()
avg_sla = fdf["sla_hours"].median()
pct_under48 = (fdf["IsUnder"] == True).mean() * 100 if "IsUnder" in fdf.columns else 0
total_bo_qty = fdf["bo_quantity"].sum()
pct_after48  = (fdf["IsAfter"] == True).mean() * 100 if "IsAfter" in fdf.columns else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)
kpis = [
    (col1, f"{n_so:,}",          "Sales Orders"),
    (col2, f"{n_mfr}",           "Manufacturers"),
    (col3, f"{avg_sla:.1f}h",    "Median SLA"),
    (col4, f"{pct_under48:.0f}%","Under 48h"),
    (col5, f"{pct_after48:.0f}%","After 48h"),
    (col6, f"{int(total_bo_qty):,}", "Total BO Qty"),
]
for col, val, lbl in kpis:
    with col:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-value">{val}</div>'
            f'<div class="kpi-label">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA QUALITY EXPANDER
# ─────────────────────────────────────────────
with st.expander("🔍 Data Quality Report", expanded=False):
    st.markdown("#### Missing Values (full dataset)")
    missing = df.isnull().sum()
    missing_pct = (df.isnull().mean() * 100).round(2)
    qual_df = pd.DataFrame({"Missing Count": missing, "Missing %": missing_pct})
    qual_df = qual_df[qual_df["Missing Count"] > 0].sort_values("Missing %", ascending=False)
    if qual_df.empty:
        st.success("No missing values detected ✅")
    else:
        st.dataframe(qual_df, use_container_width=True)

    st.markdown("#### Column Data Types")
    dtype_df = pd.DataFrame({"dtype": df.dtypes.astype(str)})
    st.dataframe(dtype_df, use_container_width=True)

    st.markdown("#### SLA Hours Distribution (descriptive stats)")
    st.dataframe(
        fdf["sla_hours"].describe().rename("sla_hours").to_frame().T.round(2),
        use_container_width=True,
    )

# ─────────────────────────────────────────────
# ── SECTION 2 · TEMPORAL EVOLUTION
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">📅 Temporal Evolution of Backorders</p>', unsafe_allow_html=True)

# Daily backorder volume
daily = (
    fdf.groupby("created_day")
    .agg(
        records=("tran_id", "count"),
        unique_sos=("tran_id", "nunique"),
        bo_qty=("bo_quantity", "sum"),
        avg_sla=("sla_hours", "mean"),
    )
    .reset_index()
)

tab1, tab2, tab3 = st.tabs(["📈 Volume Over Time", "⏱️ SLA Over Time", "🗂️ Status Mix"])

with tab1:
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(
        x=daily["created_day"],
        y=daily["records"],
        name="Records",
        marker=dict(
            color=daily["records"],
            colorscale="Viridis",
            showscale=False,
        ),
        opacity=0.85,
    ))
    fig_vol.add_trace(go.Scatter(
        x=daily["created_day"],
        y=daily["unique_sos"],
        name="Unique SOs",
        mode="lines+markers",
        line=dict(color="#ec4899", width=2.5),
        marker=dict(size=6),
        yaxis="y2",
    ))
    fig_vol.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Date",
        yaxis_title="Record Count",
        yaxis2=dict(title="Unique Sales Orders", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=380,
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig_vol, use_container_width=True)

with tab2:
    daily_sla = (
        fdf.groupby("created_day")["sla_hours"]
        .agg(["mean", "median", "max"])
        .reset_index()
    )
    fig_sla = go.Figure()
    fig_sla.add_trace(go.Scatter(
        x=daily_sla["created_day"], y=daily_sla["median"],
        name="Median SLA (h)", mode="lines+markers",
        line=dict(color="#818cf8", width=2.5),
    ))
    fig_sla.add_trace(go.Scatter(
        x=daily_sla["created_day"], y=daily_sla["mean"],
        name="Mean SLA (h)", mode="lines",
        line=dict(color="#c084fc", width=1.5, dash="dash"),
    ))
    fig_sla.add_trace(go.Scatter(
        x=daily_sla["created_day"], y=daily_sla["max"],
        name="Max SLA (h)", mode="lines",
        line=dict(color="#f43f5e", width=1, dash="dot"),
    ))
    # 48h reference line
    fig_sla.add_hline(
        y=48, line_dash="dash", line_color="#facc15",
        annotation_text="48h SLA target", annotation_position="bottom right",
    )
    fig_sla.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Date",
        yaxis_title="Hours",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=380,
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig_sla, use_container_width=True)

with tab3:
    # Stacked bar by field (Allocated Supply / Committed / Fulfilled)
    status_daily = (
        fdf.groupby(["created_day", "field"])
        .size()
        .reset_index(name="count")
    )
    fig_status = px.bar(
        status_daily, x="created_day", y="count", color="field",
        title="Daily Records by Field Type",
        color_discrete_sequence=px.colors.qualitative.Vivid,
        labels={"created_day": "Date", "count": "Records", "field": "Field"},
    )
    fig_status.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        font=dict(family="Inter"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_status, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 3 · TOP 5 MANUFACTURERS
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">🏭 Top 5 Manufacturers by Backorder Volume</p>', unsafe_allow_html=True)

top5 = (
    fdf.groupby("item_manufacturer")
    .agg(
        records=("tran_id", "count"),
        unique_sos=("tran_id", "nunique"),
        bo_qty=("bo_quantity", "sum"),
        avg_sla=("sla_hours", "mean"),
        median_sla=("sla_hours", "median"),
    )
    .reset_index()
    .sort_values("records", ascending=False)
    .head(5)
)

col_left, col_right = st.columns([1.3, 1])

with col_left:
    fig_top5 = go.Figure()
    colors = ["#818cf8", "#a78bfa", "#c084fc", "#e879f9", "#f43f5e"]
    fig_top5.add_trace(go.Bar(
        x=top5["item_manufacturer"],
        y=top5["records"],
        name="Records",
        marker=dict(color=colors),
        text=top5["records"],
        textposition="outside",
        textfont=dict(color="white"),
    ))
    fig_top5.add_trace(go.Scatter(
        x=top5["item_manufacturer"],
        y=top5["median_sla"],
        name="Median SLA (h)",
        mode="lines+markers",
        line=dict(color="#facc15", width=2.5),
        marker=dict(size=10, symbol="diamond"),
        yaxis="y2",
    ))
    fig_top5.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Manufacturer",
        yaxis_title="Record Count",
        yaxis2=dict(title="Median SLA (hours)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400,
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig_top5, use_container_width=True)

with col_right:
    # Treemap of record share
    fig_tree = px.treemap(
        top5,
        path=["item_manufacturer"],
        values="records",
        color="median_sla",
        color_continuous_scale="RdYlGn_r",
        title="Record Share & Median SLA (color)",
    )
    fig_tree.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="white"),
        height=400,
        margin=dict(t=40, l=0, r=0, b=0),
        coloraxis_colorbar=dict(title="Med. SLA (h)"),
    )
    fig_tree.update_traces(textinfo="label+value+percent root")
    st.plotly_chart(fig_tree, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 4 · SLA BUCKET ANALYSIS
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">⏱️ SLA Bucket Distribution</p>', unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    bucket_counts = (
        fdf["Buckets"].value_counts().reset_index()
        if "Buckets" in fdf.columns
        else pd.DataFrame(columns=["Buckets", "count"])
    )
    bucket_counts.columns = ["Bucket", "Count"]
    # Sort buckets alphabetically (they start with A., B., C. …)
    bucket_counts = bucket_counts.sort_values("Bucket")

    fig_bucket = px.bar(
        bucket_counts, x="Bucket", y="Count",
        color="Count",
        color_continuous_scale="Plasma",
        title="Records per SLA Bucket",
        labels={"Count": "Records"},
        text="Count",
    )
    fig_bucket.update_traces(textposition="outside")
    fig_bucket.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"),
        height=380,
        coloraxis_showscale=False,
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig_bucket, use_container_width=True)

with c2:
    fig_hist = px.histogram(
        fdf[fdf["sla_hours"] <= 200],
        x="sla_hours",
        nbins=30,
        color_discrete_sequence=["#818cf8"],
        title="SLA Hours Distribution (≤ 200h)",
        labels={"sla_hours": "SLA Hours"},
    )
    fig_hist.add_vline(
        x=48, line_dash="dash", line_color="#facc15",
        annotation_text="48h target",
    )
    fig_hist.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"),
        height=380,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 5 · MANUFACTURER × SLA DEEP DIVE
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">🔬 Manufacturer × SLA Deep Dive</p>', unsafe_allow_html=True)

mfr_sla = (
    fdf.groupby("item_manufacturer")["sla_hours"]
    .agg(["mean", "median", "count", "std"])
    .reset_index()
    .rename(columns={"mean":"Avg SLA", "median":"Med SLA", "count":"Records", "std":"Std Dev"})
    .sort_values("Records", ascending=False)
    .head(15)
)

fig_box = px.box(
    fdf[fdf["item_manufacturer"].isin(mfr_sla["item_manufacturer"])],
    x="item_manufacturer",
    y="sla_hours",
    color="item_manufacturer",
    color_discrete_sequence=px.colors.qualitative.Vivid,
    title="SLA Hours Box Plot — Top 15 Manufacturers",
    labels={"item_manufacturer": "Manufacturer", "sla_hours": "SLA (hours)"},
    category_orders={"item_manufacturer": mfr_sla["item_manufacturer"].tolist()},
)
fig_box.add_hline(
    y=48, line_dash="dash", line_color="#facc15",
    annotation_text="48h Target",
)
fig_box.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter"),
    height=420,
    showlegend=False,
    xaxis_tickangle=-35,
)
st.plotly_chart(fig_box, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 6 · BUYER PERFORMANCE
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">👤 Buyer Performance</p>', unsafe_allow_html=True)

buyer_perf = (
    fdf.groupby("item_buyer")
    .agg(
        records=("tran_id", "count"),
        avg_sla=("sla_hours", "mean"),
        under48=("IsUnder", "sum"),
        after48=("IsAfter", "sum"),
    )
    .reset_index()
    .sort_values("records", ascending=False)
    .dropna(subset=["item_buyer"])
)
buyer_perf["item_buyer"] = buyer_perf["item_buyer"].replace("", "Unknown")
buyer_perf = buyer_perf[buyer_perf["item_buyer"] != ""]

fig_buyer = px.scatter(
    buyer_perf,
    x="records",
    y="avg_sla",
    size="records",
    color="item_buyer",
    text="item_buyer",
    title="Buyer: Volume vs Average SLA",
    labels={"records": "Record Count", "avg_sla": "Avg SLA (h)", "item_buyer": "Buyer"},
    color_discrete_sequence=px.colors.qualitative.Bold,
)
fig_buyer.update_traces(textposition="top center")
fig_buyer.add_hline(y=48, line_dash="dash", line_color="#facc15", annotation_text="48h Target")
fig_buyer.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter"),
    height=380,
    showlegend=False,
)
st.plotly_chart(fig_buyer, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 7 · BO STATUS BREAKDOWN
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">📋 Backorder Status Breakdown</p>', unsafe_allow_html=True)

c3, c4 = st.columns(2)

with c3:
    status_counts = fdf["bo_status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig_donut = px.pie(
        status_counts, names="Status", values="Count",
        hole=0.55,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title="BO Status Distribution",
    )
    fig_donut.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"),
        height=360,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with c4:
    field_counts = fdf["field"].value_counts().reset_index()
    field_counts.columns = ["Field", "Count"]
    fig_field = px.pie(
        field_counts, names="Field", values="Count",
        hole=0.55,
        color_discrete_sequence=px.colors.qualitative.Set3,
        title="Field Distribution",
    )
    fig_field.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"),
        height=360,
    )
    st.plotly_chart(fig_field, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 8 · TOP MANUFACTURERS OVER TIME
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">📊 Top 5 Manufacturers — Daily Evolution</p>', unsafe_allow_html=True)

top5_names = top5["item_manufacturer"].tolist()
mfr_daily = (
    fdf[fdf["item_manufacturer"].isin(top5_names)]
    .groupby(["created_day", "item_manufacturer"])
    .size()
    .reset_index(name="records")
)

fig_mfr_time = px.line(
    mfr_daily, x="created_day", y="records",
    color="item_manufacturer",
    markers=True,
    title="Daily Backorder Volume — Top 5 Manufacturers",
    labels={"created_day": "Date", "records": "Records", "item_manufacturer": "Manufacturer"},
    color_discrete_sequence=px.colors.qualitative.Vivid,
)
fig_mfr_time.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter"),
    height=400,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig_mfr_time, use_container_width=True)

# ─────────────────────────────────────────────
# ── SECTION 9 · RAW DATA TABLE
# ─────────────────────────────────────────────
with st.expander("📄 Raw Filtered Data", expanded=False):
    display_cols = [
        "tran_id", "created_date", "reached_bo_date",
        "item_manufacturer", "item_name", "item_buyer",
        "field", "bo_status", "bo_quantity",
        "sla_hours", "Buckets",
    ]
    existing = [c for c in display_cols if c in fdf.columns]
    st.dataframe(
        fdf[existing].sort_values("created_date", ascending=False),
        use_container_width=True,
        height=350,
    )

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:rgba(255,255,255,0.08); margin-top:2rem;'>"
    "<p style='text-align:center; color:rgba(255,255,255,0.3); font-size:0.75rem;'>"
    "JEM Backorders SLA Dashboard &nbsp;·&nbsp; Built with Streamlit & Plotly</p>",
    unsafe_allow_html=True,
)
