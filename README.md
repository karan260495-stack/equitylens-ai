# EquityLens One V8 — Kotak Neo Connected Edition

## What this build adds

- Secure Kotak Neo TOTP login from inside the app
- Kotak live quote as the primary current-price layer
- NSE and BSE symbol discovery through Kotak scrip search
- Kotak 52-week/quote fields when returned by the API
- Read-only Kotak holdings, positions and limits dashboard
- No place-order, modify-order or cancel-order functions
- Existing five-year research, news, valuation, risk and PDF sections
- Mainboard and SME IPO discovery using IPOWatch and IPO Ji reference tables
- Responsive mobile layout

## Required Streamlit Secrets

Add these in **Streamlit Community Cloud → Manage app → Settings → Secrets**:

```toml
KOTAK_CONSUMER_KEY = "your_new_consumer_key"
KOTAK_UCC = "your_unique_client_code"
KOTAK_MOBILE = "+91xxxxxxxxxx"
KOTAK_MPIN = "your_6_digit_mpin"
```

Do not store the changing TOTP in Secrets. Enter it in the app whenever a fresh Kotak session is needed.

## Critical security step

If a Consumer Key appeared in a screenshot or chat, regenerate it in Kotak Neo and update Streamlit Secrets before using this build.

## Streamlit Python version

Kotak's official SDK documents Python 3.10–3.13. In Streamlit Community Cloud, set the app to **Python 3.13** in Advanced settings, then reboot.

## GitHub files

Upload these into the root of the existing repository:

- `app.py`
- `requirements.txt`
- `README.md`
- `.streamlit/config.toml`

Commit and allow Streamlit to redeploy.

## First connection test

1. Open the app.
2. Enter the current six-digit Kotak TOTP.
3. Tap **Connect securely**.
4. Search `RELIANCE` or another NSE symbol.
5. Confirm the source badge says **Kotak Neo live quote + verified public research layers**.
6. Open **My Kotak Portfolio** and confirm holdings/positions load.

## Data design

Kotak Neo is used for market and account data. Public/exchange research layers are still needed for multi-year financial statements, corporate filings, news, RHP/DRHP analysis and unofficial GMP. The app never enables trading.
