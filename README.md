# EquityLens AI V5 — Hybrid Professional Edition

This version works immediately on Streamlit Community Cloud without an API token.

## Data modes
- Free fallback: Yahoo Finance for market/fundamental fields + Google News RSS.
- Connected mode: Upstox official market, fundamentals, news and IPO APIs when `UPSTOX_ACCESS_TOKEN` is configured.

## Streamlit update
Upload `app.py`, `requirements.txt`, and the `.streamlit` folder to the repository root. Commit the changes. Streamlit redeploys automatically.

## Optional Upstox secret
Manage app → Settings → Secrets:

```toml
UPSTOX_ACCESS_TOKEN = "your_token_here"
```

The app does not stop when the token is absent.
