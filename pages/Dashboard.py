import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
from data_loader import load_data, reshape_data

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #003459 0%, #007ea7 100%);
        padding: 1.2rem;
        border-radius: 0.8rem;
        color: #ffffff;
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 0.9rem; opacity: 0.85; }
    .metric-card h1 { margin: 0.3rem 0 0 0; font-size: 2rem; }
    .stApp > header { background-color: transparent; }
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #f0f4f8; }
    [data-testid="stSidebar"] * { color: #00171f; }
    [data-testid="stMetric"] {
        background-color: #003459;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #00a8e8;
    }
    [data-testid="stMetric"] * { color: #ffffff !important; }
    [data-testid="stMetricLabel"] { color: #00a8e8 !important; }
    h1, h2, h3 { color: #003459 !important; }
    p, span, label, div { color: #00171f; }
    .stButton > button {
        background-color: #003459;
        color: #ffffff;
        border: none;
        border-radius: 0.4rem;
    }
    .stButton > button:hover {
        background-color: #007ea7;
        color: #ffffff;
    }
    hr { border-color: #00a8e8; }
    .stRadio > label { color: #00171f !important; }
    .stCheckbox > label { color: #00171f !important; }
    [data-testid="stExpander"] { border-color: #007ea7; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")

auto_refresh = st.sidebar.checkbox("Auto-refresh every 5 minutes", value=True)
if auto_refresh:
    st.sidebar.caption("Data reloads automatically from Google Sheets.")

if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# ─── Load Data ───────────────────────────────────────────────────────────────
try:
    with st.spinner("Loading data from Google Sheets..."):
        raw_df = load_data()
        long_df = reshape_data(raw_df)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# ─── Sidebar Filters ────────────────────────────────────────────────────────
all_gates = sorted(raw_df["Gate"].unique().tolist())
selected_gates = st.sidebar.multiselect(
    "Filter Gates", all_gates, default=all_gates,
    help="Select which gates/sections to include in the analysis."
)

if not selected_gates:
    st.warning("Select at least one gate to display data.")
    st.stop()

# Filter data
filtered_long = long_df[long_df["Gate"].isin(selected_gates)]
filtered_wide = raw_df[raw_df["Gate"].isin(selected_gates)]

# Date range filter
if not filtered_long.empty:
    min_date = filtered_long["Date"].min().date()
    max_date = filtered_long["Date"].max().date()
    date_range = st.sidebar.date_input(
        "Date Range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        filtered_long = filtered_long[
            (filtered_long["Date"].dt.date >= date_range[0]) &
            (filtered_long["Date"].dt.date <= date_range[1])
        ]

st.sidebar.markdown("---")
st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")

# ─── KPI Metrics ─────────────────────────────────────────────────────────────
st.title("Ticket Sales Dashboard")

# Latest cumulative totals (last recorded date)
if not filtered_long.empty:
    latest_date = filtered_long["Date"].max()
    latest_data = filtered_long[filtered_long["Date"] == latest_date]
    current_total = latest_data["Cumulative"].sum()

    # New tickets sold on latest date
    latest_daily = latest_data["Daily"].sum()

    # Total new tickets across all dates
    total_daily_sold = filtered_long["Daily"].sum()
    num_dates = filtered_long["Date"].nunique()
    avg_daily = total_daily_sold / num_dates if num_dates > 0 else 0

    # Best gate by current cumulative
    best_gate = latest_data.groupby("Gate")["Cumulative"].sum().idxmax()
    best_gate_total = latest_data.groupby("Gate")["Cumulative"].sum().max()

    # Previous date for comparison
    dates_sorted = sorted(filtered_long["Date"].unique())
    if len(dates_sorted) >= 2:
        prev_date = dates_sorted[-2]
        prev_total = filtered_long[filtered_long["Date"] == prev_date]["Cumulative"].sum()
        delta = current_total - prev_total
        delta_pct = (delta / prev_total * 100) if prev_total > 0 else 0
    else:
        delta = 0
        delta_pct = 0
else:
    current_total = latest_daily = 0
    num_dates = avg_daily = 0
    best_gate = "N/A"
    best_gate_total = delta = delta_pct = 0

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Current Total Sold", f"{current_total:,}")
with col2:
    st.metric("Recording Days", num_dates)
with col3:
    st.metric("Avg New/Day", f"{avg_daily:,.0f}")
with col4:
    st.metric("Latest Day New", f"{latest_daily:,}",
              delta=f"{delta:+,} ({delta_pct:+.1f}%)" if delta != 0 else None)
with col5:
    st.metric("Top Gate", f"{best_gate}", delta=f"{best_gate_total:,} total")

st.markdown("---")

# ─── Charts ──────────────────────────────────────────────────────────────────

# 1. Cumulative Total Over Time + Daily New Sales
st.subheader("Cumulative Tickets Sold & Daily New Sales")
daily_agg = filtered_long.groupby("Date").agg(
    Cumulative=("Cumulative", "sum"),
    Daily=("Daily", "sum"),
).reset_index()

fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
fig_trend.add_trace(
    go.Bar(x=daily_agg["Date"], y=daily_agg["Daily"],
           name="New Tickets", marker_color="#667eea", opacity=0.7),
    secondary_y=False,
)
fig_trend.add_trace(
    go.Scatter(x=daily_agg["Date"], y=daily_agg["Cumulative"],
               name="Cumulative Total", line=dict(color="#e63946", width=3)),
    secondary_y=True,
)
fig_trend.update_layout(
    height=450, hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig_trend.update_yaxes(title_text="New Tickets", secondary_y=False)
fig_trend.update_yaxes(title_text="Cumulative Total", secondary_y=True)
st.plotly_chart(fig_trend, use_container_width=True)

# 2. Sales by Gate - two columns
col_left, col_right = st.columns(2)

# Gate totals = latest cumulative per gate
latest = filtered_long[filtered_long["Date"] == filtered_long["Date"].max()]
gate_totals = latest.groupby("Gate")["Cumulative"].sum().reset_index()
gate_totals.columns = ["Gate", "Tickets"]
gate_totals = gate_totals.sort_values("Tickets", ascending=True)
gate_totals["Gate"] = gate_totals["Gate"].astype(str)

with col_left:
    st.subheader("Current Tickets by Gate")
    fig_gates = px.bar(gate_totals, x="Tickets", y="Gate", orientation="h",
                       color="Tickets", color_continuous_scale="Viridis",
                       text="Tickets")
    fig_gates.update_traces(textposition="outside")
    fig_gates.update_yaxes(type="category")
    fig_gates.update_layout(height=400, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_gates, use_container_width=True)

with col_right:
    st.subheader("Gate Distribution")
    fig_pie = px.pie(gate_totals, values="Tickets", names="Gate",
                     color_discrete_sequence=px.colors.qualitative.Set3,
                     hole=0.4)
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

# 3. Cumulative Over Time by Gate
st.subheader("Cumulative Sales by Gate Over Time")
view_mode = st.radio("View", ["Cumulative", "Daily New"], horizontal=True,
                     label_visibility="collapsed")
y_col = "Cumulative" if view_mode == "Cumulative" else "Daily"

chart_type = st.radio("Chart type", ["Stacked Area", "Line", "Stacked Bar"],
                      horizontal=True, label_visibility="collapsed",
                      key="chart_type_gate")

if chart_type == "Stacked Area":
    fig_area = px.area(filtered_long, x="Date", y=y_col, color="Gate",
                       color_discrete_sequence=px.colors.qualitative.Set2)
elif chart_type == "Line":
    fig_area = px.line(filtered_long, x="Date", y=y_col, color="Gate",
                       markers=True, color_discrete_sequence=px.colors.qualitative.Set2)
else:
    fig_area = px.bar(filtered_long, x="Date", y=y_col, color="Gate",
                      color_discrete_sequence=px.colors.qualitative.Set2)

fig_area.update_layout(height=450, hovermode="x unified",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                   xanchor="right", x=1))
st.plotly_chart(fig_area, use_container_width=True)

# 4. Day-over-Day Change (new tickets per day)
st.subheader("Day-over-Day New Tickets")
daily_change = daily_agg.copy()
daily_change["Change"] = daily_change["Daily"].diff()
daily_change["Change %"] = daily_change["Daily"].pct_change() * 100
daily_change = daily_change.iloc[1:]  # skip first row (no previous)

if not daily_change.empty:
    fig_change = go.Figure()
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in daily_change["Change"]]
    fig_change.add_trace(go.Bar(
        x=daily_change["Date"], y=daily_change["Change"],
        marker_color=colors, name="Change",
        text=[f"{v:+,.0f}" for v in daily_change["Change"]],
        textposition="outside"
    ))
    fig_change.update_layout(height=350, hovermode="x unified")
    st.plotly_chart(fig_change, use_container_width=True)
else:
    st.info("Need at least 2 dates to show day-over-day changes.")

# 6. Gate Performance Summary
st.subheader("Gate Performance Summary")
latest_cum = filtered_long[filtered_long["Date"] == filtered_long["Date"].max()]
summary = latest_cum[["Gate", "Cumulative"]].copy()
summary.columns = ["Gate", "Current Total"]
daily_stats = filtered_long.groupby("Gate")["Daily"].agg(
    ["mean", "min", "max", "std"]
).reset_index()
daily_stats.columns = ["Gate", "Avg New/Day", "Min New/Day", "Max New/Day", "Std Dev"]
summary = summary.merge(daily_stats, on="Gate")
summary["% of Total"] = (summary["Current Total"] / summary["Current Total"].sum() * 100).round(1)
summary = summary.sort_values("Current Total", ascending=False)

# Format numbers
for col in ["Avg New/Day", "Std Dev"]:
    summary[col] = summary[col].round(1)

st.dataframe(
    summary.style.format({
        "Current Total": "{:,.0f}",
        "Avg New/Day": "{:,.1f}",
        "Min New/Day": "{:,.0f}",
        "Max New/Day": "{:,.0f}",
        "Std Dev": "{:,.1f}",
        "% of Total": "{:.1f}%",
    }).background_gradient(subset=["Current Total"], cmap="YlOrRd"),
    use_container_width=True, hide_index=True
)

# 7. Raw Data (expandable)
with st.expander("Raw Data"):
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

# ─── Auto-refresh ────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(300)  # 5 minutes
    st.cache_data.clear()
    st.rerun()
