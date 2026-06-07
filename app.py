import streamlit as st

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ira Tickets Dashboard",
    page_icon="🎟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Navigation ──────────────────────────────────────────────────────────────
dashboard_page = st.Page("pages/Dashboard.py", title="Dashboard", icon="🎟️", default=True)
predictor_page = st.Page("pages/Predictor.py", title="Predictor", icon="🔮")

nav = st.navigation([dashboard_page, predictor_page])
nav.run()
