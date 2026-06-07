import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import curve_fit
from datetime import timedelta
from data_loader import load_data, reshape_data

st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)


# ─── Model Definitions ──────────────────────────────────────────────────────
def linear_model(x, a, b):
    return a * x + b


def exponential_model(x, a, b, c):
    return a * np.exp(b * x) + c


def logarithmic_model(x, a, b):
    return a * np.log(x + 1) + b


def logistic_model(x, L, k, x0, b):
    return L / (1 + np.exp(-k * (x - x0))) + b


def polynomial_model(x, a, b, c):
    return a * x**2 + b * x + c


MODEL_CONFIGS = {
    "Linear": {
        "fn": linear_model,
        "p0": None,
        "desc": "Constant daily growth rate",
        "color": "#e63946",
    },
    "Exponential": {
        "fn": exponential_model,
        "p0": [1, 0.01, 0],
        "desc": "Accelerating growth",
        "color": "#f4a261",
    },
    "Logarithmic": {
        "fn": logarithmic_model,
        "p0": None,
        "desc": "Decelerating growth (slowing down)",
        "color": "#2a9d8f",
    },
    "Logistic (S-curve)": {
        "fn": logistic_model,
        "p0": None,  # set dynamically
        "desc": "Growth with saturation limit",
        "color": "#9b5de5",
    },
    "Polynomial (quadratic)": {
        "fn": polynomial_model,
        "p0": None,
        "desc": "Curved growth trend",
        "color": "#00b4d8",
    },
}


def fit_and_predict(x_data, y_data, model_name, target, max_days=365):
    """Fit a model and predict when the target will be reached."""
    cfg = MODEL_CONFIGS[model_name]
    fn = cfg["fn"]

    p0 = cfg["p0"]
    if model_name == "Logistic (S-curve)":
        p0 = [max(y_data) * 2, 0.05, len(x_data) / 2, min(y_data)]

    try:
        bounds = (-np.inf, np.inf)
        if model_name == "Logistic (S-curve)":
            bounds = ([target * 0.5, 0.001, -len(x_data) * 5, -np.inf],
                      [target * 5, 1.0, len(x_data) * 10, np.inf])

        popt, _ = curve_fit(fn, x_data, y_data, p0=p0, maxfev=10000,
                            bounds=bounds)

        # Generate future predictions
        x_future = np.arange(0, len(x_data) + max_days)
        y_pred = fn(x_future, *popt)

        # Find when target is reached
        target_idx = np.where(y_pred >= target)[0]
        days_to_target = int(target_idx[0]) if len(target_idx) > 0 else None

        # R² score on training data
        y_fit = fn(x_data, *popt)
        ss_res = np.sum((y_data - y_fit) ** 2)
        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            "x_future": x_future,
            "y_pred": y_pred,
            "days_to_target": days_to_target,
            "r_squared": r_squared,
            "params": popt,
        }
    except Exception:
        return None


# ─── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("Sales Predictor")
st.sidebar.markdown("---")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Load data
try:
    raw_df = load_data()
    long_df = reshape_data(raw_df)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# Gate selection
all_gates = sorted(raw_df["Gate"].unique().tolist())
scope = st.sidebar.radio("Prediction scope", ["All Gates Combined"] + all_gates)

# Get the time series
if scope == "All Gates Combined":
    ts = long_df.groupby("Date")["Cumulative"].sum().reset_index()
else:
    ts = long_df[long_df["Gate"] == scope].groupby("Date")["Cumulative"].sum().reset_index()

ts = ts.sort_values("Date")
current_total = int(ts["Cumulative"].iloc[-1])
latest_date = ts["Date"].iloc[-1]

st.sidebar.markdown("---")
st.sidebar.metric("Current Total", f"{current_total:,}")
st.sidebar.metric("Latest Date", latest_date.strftime("%b %d, %Y"))

# Target setting
st.sidebar.markdown("---")
st.sidebar.subheader("Set Target")
target = st.sidebar.number_input(
    "Target tickets to sell",
    min_value=current_total + 1,
    max_value=current_total * 20,
    value=int(current_total * 1.5),
    step=100,
)

# Model selection
st.sidebar.markdown("---")
st.sidebar.subheader("Models")
selected_models = []
for name, cfg in MODEL_CONFIGS.items():
    if st.sidebar.checkbox(name, value=True, help=cfg["desc"]):
        selected_models.append(name)

from datetime import date as date_type
end_of_sales = st.sidebar.date_input(
    "End of sales date",
    value=date_type(2026, 8, 22),
    min_value=latest_date + timedelta(days=1),
    help="Set the date when ticket sales end"
)
max_forecast_days = (end_of_sales - latest_date.date()).days if isinstance(end_of_sales, date_type) else 365

# ─── Main Content ────────────────────────────────────────────────────────────
st.title("🔮 Sales Prediction & Target Planner")
st.markdown(f"**Scope:** {scope} · **Current total:** {current_total:,} · "
            f"**Target:** {target:,} · **Remaining:** {target - current_total:,} · "
            f"**Sales end:** {end_of_sales.strftime('%b %d, %Y') if isinstance(end_of_sales, date_type) else 'N/A'}")
st.markdown("---")

if not selected_models:
    st.warning("Select at least one model from the sidebar.")
    st.stop()

# Prepare data for fitting
x_data = np.arange(len(ts))
y_data = ts["Cumulative"].values.astype(float)
start_date = ts["Date"].iloc[0]

# Fit models
results = {}
for model_name in selected_models:
    result = fit_and_predict(x_data, y_data, model_name, target, max_forecast_days)
    if result is not None:
        results[model_name] = result

if not results:
    st.error("No models could be fitted to the data. Try different model selections.")
    st.stop()

# ─── Prediction Chart ────────────────────────────────────────────────────────
st.subheader("Growth Curve & Predictions")

fig = go.Figure()

# Actual data
fig.add_trace(go.Scatter(
    x=ts["Date"], y=ts["Cumulative"],
    mode="markers+lines", name="Actual Data",
    line=dict(color="white", width=2),
    marker=dict(size=8, color="#667eea"),
))

# Target line
fig.add_hline(y=target, line_dash="dash", line_color="#ffd166",
              annotation_text=f"Target: {target:,}",
              annotation_position="top left",
              annotation_font_color="#ffd166")

# Model predictions
for model_name, result in results.items():
    cfg = MODEL_CONFIGS[model_name]
    future_dates = [start_date + timedelta(days=int(d)) for d in result["x_future"]]

    # Only plot up to a reasonable range past the target
    max_plot = len(x_data) + max_forecast_days
    plot_mask = result["x_future"] <= max_plot

    fig.add_trace(go.Scatter(
        x=[future_dates[i] for i in range(len(future_dates)) if plot_mask[i]],
        y=result["y_pred"][plot_mask],
        mode="lines", name=f"{model_name} (R²={result['r_squared']:.3f})",
        line=dict(color=cfg["color"], width=2, dash="dot"),
    ))

    # Mark target point
    if result["days_to_target"] is not None:
        target_date = start_date + timedelta(days=result["days_to_target"])
        fig.add_trace(go.Scatter(
            x=[target_date],
            y=[target],
            mode="markers", name=f"{model_name} target",
            marker=dict(size=14, color=cfg["color"], symbol="star"),
            showlegend=False,
            hovertemplate=f"{model_name}<br>Date: {target_date.strftime('%b %d, %Y')}<br>Tickets: {target:,}<extra></extra>",
        ))

fig.update_layout(
    height=550, hovermode="x unified",
    xaxis_title="Date", yaxis_title="Total Tickets",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(rangemode="tozero"),
)
st.plotly_chart(fig, use_container_width=True)

# ─── Model Comparison Table ─────────────────────────────────────────────────
st.subheader("When Will You Hit Your Target?")

comparison = []
for model_name, result in results.items():
    if result["days_to_target"] is not None:
        target_date = start_date + timedelta(days=result["days_to_target"])
        days_from_now = (target_date - latest_date).days
        comparison.append({
            "Model": model_name,
            "Estimated Date": target_date.strftime("%b %d, %Y"),
            "Days From Now": max(0, days_from_now),
            "R² Fit": result["r_squared"],
            "Description": MODEL_CONFIGS[model_name]["desc"],
        })
    else:
        comparison.append({
            "Model": model_name,
            "Estimated Date": f"Not within {max_forecast_days} days",
            "Days From Now": None,
            "R² Fit": result["r_squared"],
            "Description": MODEL_CONFIGS[model_name]["desc"],
        })

comp_df = pd.DataFrame(comparison)

st.dataframe(
    comp_df.style.format({
        "R² Fit": "{:.4f}",
        "Days From Now": lambda x: f"{x:,.0f}" if pd.notna(x) else "—",
    }),
    use_container_width=True, hide_index=True,
)

# Best model recommendation
valid = [r for r in comparison if r["Days From Now"] is not None]
if valid:
    best = max(valid, key=lambda r: r["R² Fit"])
    st.success(
        f"**Best fit model: {best['Model']}** (R² = {best['R² Fit']:.4f}) — "
        f"Estimated to reach **{target:,}** tickets by **{best['Estimated Date']}** "
        f"({best['Days From Now']} days from now)"
    )

# ─── Interactive Growth Simulator ────────────────────────────────────────────
st.markdown("---")
st.subheader("Growth Simulator")
st.markdown("Manually set a daily growth rate to see how fast you'd reach your target.")

col1, col2 = st.columns(2)
with col1:
    # Calculate current average daily growth
    if len(ts) >= 2:
        total_days = (ts["Date"].iloc[-1] - ts["Date"].iloc[0]).days
        actual_daily_avg = (ts["Cumulative"].iloc[-1] - ts["Cumulative"].iloc[0]) / total_days if total_days > 0 else 0
    else:
        actual_daily_avg = 0

    sim_daily = st.slider(
        "Simulated tickets/day",
        min_value=1, max_value=int(max(actual_daily_avg * 5, 100)),
        value=int(max(actual_daily_avg, 1)),
        step=1,
    )
with col2:
    remaining = target - current_total
    if sim_daily > 0:
        days_needed = remaining / sim_daily
        est_date = latest_date + timedelta(days=int(days_needed))
        st.metric("Days to Target", f"{int(days_needed):,}")
        st.metric("Estimated Date", est_date.strftime("%b %d, %Y"))
    else:
        st.metric("Days to Target", "∞")

# Simulation chart
if sim_daily > 0:
    sim_days = int(days_needed) + 30
    sim_dates = [latest_date + timedelta(days=i) for i in range(sim_days + 1)]
    sim_values = [current_total + sim_daily * i for i in range(sim_days + 1)]

    fig_sim = go.Figure()
    fig_sim.add_trace(go.Scatter(
        x=ts["Date"], y=ts["Cumulative"],
        mode="lines+markers", name="Actual",
        line=dict(color="#667eea", width=2),
    ))
    fig_sim.add_trace(go.Scatter(
        x=sim_dates, y=sim_values,
        mode="lines", name=f"Simulated ({sim_daily}/day)",
        line=dict(color="#2ecc71", width=2, dash="dash"),
    ))
    fig_sim.add_hline(y=target, line_dash="dash", line_color="#ffd166",
                      annotation_text=f"Target: {target:,}")

    fig_sim.update_layout(
        height=400, hovermode="x unified",
        xaxis_title="Date", yaxis_title="Total Tickets",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_sim, use_container_width=True)

# ─── Per-Gate Projections ────────────────────────────────────────────────────
if scope == "All Gates Combined":
    st.markdown("---")
    st.subheader("Per-Gate Current Status vs Proportional Target")

    latest_by_gate = long_df[long_df["Date"] == long_df["Date"].max()]
    gate_summary = latest_by_gate.groupby("Gate")["Cumulative"].sum().reset_index()
    gate_summary.columns = ["Gate", "Current"]
    gate_summary["% of Total"] = (gate_summary["Current"] / gate_summary["Current"].sum() * 100)
    gate_summary["Proportional Target"] = (gate_summary["% of Total"] / 100 * target).astype(int)
    gate_summary["Remaining"] = gate_summary["Proportional Target"] - gate_summary["Current"]
    gate_summary["Progress %"] = (gate_summary["Current"] / gate_summary["Proportional Target"] * 100).round(1)
    gate_summary = gate_summary.sort_values("Current", ascending=False)

    fig_progress = go.Figure()
    fig_progress.add_trace(go.Bar(
        y=gate_summary["Gate"], x=gate_summary["Current"],
        name="Current", orientation="h", marker_color="#667eea",
        text=[f"{v:,}" for v in gate_summary["Current"]], textposition="inside",
    ))
    fig_progress.add_trace(go.Bar(
        y=gate_summary["Gate"], x=gate_summary["Remaining"].clip(lower=0),
        name="Remaining", orientation="h", marker_color="#e0e0e0", opacity=0.5,
        text=[f"{v:,}" for v in gate_summary["Remaining"].clip(lower=0)],
        textposition="inside",
    ))
    fig_progress.update_layout(
        barmode="stack", height=350, hovermode="y unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_progress, use_container_width=True)

    st.dataframe(
        gate_summary.style.format({
            "Current": "{:,.0f}",
            "% of Total": "{:.1f}%",
            "Proportional Target": "{:,.0f}",
            "Remaining": "{:,.0f}",
            "Progress %": "{:.1f}%",
        }),
        use_container_width=True, hide_index=True,
    )
