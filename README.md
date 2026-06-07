# Ticket Sales Dashboard

Interactive ticket sales analytics dashboard built with Streamlit.

## Setup

```bash
pip install -r requirements.txt
```

## Run Locally

```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud (Free)

1. Push this folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub and click "New app"
4. Select your repo, branch, and `app.py` as the main file
5. Click "Deploy"

## How to Use

1. Open your Excel file in Google Drive
2. Right-click the file → **Share** → **Copy link**
3. Make sure sharing is set to **"Anyone with the link"**
4. Paste the link into the sidebar of the dashboard
5. The dashboard auto-refreshes every 5 minutes to pick up new data

## Expected Excel Format

| Gate   | 2026-01-01 | 2026-01-02 | 2026-01-03 | ... |
|--------|-----------|-----------|-----------|-----|
| VIP    | 50        | 65        | 70        | ... |
| 11-15  | 120       | 135       | 110       | ... |
| 10     | 80        | 90        | 85        | ... |
| ...    | ...       | ...       | ...       | ... |

- First column: Gate/section names
- Remaining columns: Dates with total ticket counts
