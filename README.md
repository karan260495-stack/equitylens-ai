# EquityLens AI — Full Mobile Web App

A mobile-first Streamlit research application for Indian listed shares plus Mainboard/SME IPOs.

## Included
- 5-minute summary dashboard
- Listed-stock live prototype feed through yfinance
- NSE IPO discovery attempt with demo fallback
- Growth, profitability, leverage, cash quality and valuation scoring
- Price, financial and subscription charts
- Business dependency, bull case, bear case and “what can go wrong” sections
- Mainboard vs SME liquidity warnings
- Downloadable PDF reports
- Railway deployment configuration

## Important data note
The app is feature-complete as a working prototype, but no free public feed reliably supplies every Indian IPO and listed-company field. For real capital decisions, replace/verify prototype feeds with authorised or licensed sources and parse NSE/BSE/SEBI/company filings. Do not scrape private app endpoints.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Railway
The included `Procfile` and `railway.toml` use Railway's `$PORT`. Deploy the repository, generate a Railway domain, then add `ipo.demoda.in` as a custom domain in Railway. Railway will show the exact DNS target to enter in Hostinger.
