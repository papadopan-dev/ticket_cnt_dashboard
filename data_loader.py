import streamlit as st
import pandas as pd

DATA_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQyxzD7vj277wCRmAEowmOXQ-65fYyZX3U2gS0cat7lsJC1aymnYEd9glYgAMpp9tqSHXREMStvjdy1"
    "/pub?output=csv"
)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Download and parse the published Google Sheet as CSV."""
    df = pd.read_csv(DATA_URL)

    gate_col = df.columns[0]
    df = df.rename(columns={gate_col: "Gate"})
    df["Gate"] = df["Gate"].astype(str).str.strip()

    df = df.dropna(subset=["Gate"])
    df = df[df["Gate"] != "nan"]

    date_cols = [c for c in df.columns if c != "Gate"]

    parsed_dates = {}
    for c in date_cols:
        try:
            parsed_dates[c] = pd.to_datetime(c)
        except Exception:
            try:
                parsed_dates[c] = pd.to_datetime(str(c))
            except Exception:
                parsed_dates[c] = str(c)

    rename_map = {c: parsed_dates[c] for c in date_cols}
    df = df.rename(columns=rename_map)

    for c in df.columns:
        if c != "Gate":
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    return df


def reshape_data(df: pd.DataFrame) -> pd.DataFrame:
    """Melt the wide dataframe into long format. Data is cumulative totals."""
    date_cols = [c for c in df.columns if c != "Gate"]
    melted = df.melt(id_vars="Gate", value_vars=date_cols,
                     var_name="Date", value_name="Cumulative")
    melted["Date"] = pd.to_datetime(melted["Date"], errors="coerce")
    melted = melted.dropna(subset=["Date"])
    melted = melted.sort_values(["Gate", "Date"])

    melted["Daily"] = melted.groupby("Gate")["Cumulative"].diff().fillna(0).astype(int)
    first_dates = melted.groupby("Gate")["Date"].transform("min")
    melted.loc[melted["Date"] == first_dates, "Daily"] = melted.loc[
        melted["Date"] == first_dates, "Cumulative"
    ]

    return melted
