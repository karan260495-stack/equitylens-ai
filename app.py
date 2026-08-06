from __future__ import annotations

import io
import math
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

st.set_page_config(page_title="EquityLens AI", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

CSS = r"""
<style>
:root{--blue:#387ed1;--ink:#202124;--muted:#667085;--line:#e4e7ec;--card:#fff;--bg:#f6f7f9;--green:#087a45;--red:#c53b3b;--amber:#9a6500}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{max-width:1180px;padding-top:.8rem;padding-bottom:3rem}
[data-testid="stHeader"]{background:rgba(246,247,249,.94)}
.hero{background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px 24px;margin:4px 0 16px}
.hero h1{font-size:1.7rem;margin:0 0 6px}.sub{color:var(--muted);font-size:.96rem;margin:0}
.toolbar{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 14px}
.verdict{background:#fff;border:1px solid var(--line);border-left:6px solid var(--blue);border-radius:12px;padding:18px 20px;margin:12px 0 15px}
.verdict.buy{border-left-color:var(--green)}.verdict.wait{border-left-color:var(--amber)}.verdict.avoid{border-left-color:var(--red)}
.eyebrow{font-size:.72rem;color:var(--muted);font-weight:700;letter-spacing:.08em}.vtitle{font-size:1.45rem;font-weight:760;margin:5px 0 7px}
.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 16px}
.metric{background:#fff;border:1px solid var(--line);border-radius:10px;padding:13px 14px;min-width:0}
.mlabel{color:var(--muted);font-size:.76rem}.mvalue{font-size:1.22rem;font-weight:730;margin:4px 0;white-space:normal;overflow-wrap:anywhere}.mnote{color:var(--muted);font-size:.70rem}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:17px 18px;margin:10px 0 15px}
.card h3{font-size:1.05rem;margin:0 0 10px}.good{color:var(--green);font-weight:650}.bad{color:var(--red);font-weight:650}.warn{color:var(--amber);font-weight:650}
.pill{display:inline-block;border-radius:99px;padding:3px 9px;font-size:.72rem;font-weight:700}.pos{background:#e8f6ee;color:#087a45}.neg{background:#fdecec;color:#b22f2f}.neu{background:#eef2f6;color:#596273}
.news{background:#fff;border:1px solid var(--line);border-radius:10px;padding:13px 15px;margin:8px 0}.ntitle{font-weight:720;margin:5px 0}.nmeta{font-size:.74rem;color:var(--muted)}
.source{font-size:.75rem;color:var(--muted);padding:7px 0}.section-title{font-size:1.18rem;font-weight:750;margin:18px 0 8px}
.stButton>button{background:var(--blue);color:white;border:0;border-radius:7px;min-height:42px;font-weight:680}.stButton>button:hover{background:#2f6fba;color:white}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"] div[data-baseweb="select"]>div{background:#fff;color:var(--ink)}
.stTabs [data-baseweb="tab-list"]{gap:20px;border-bottom:1px solid var(--line)}.stTabs [data-baseweb="tab"]{height:44px;padding-left:0;padding-right:0}.stTabs [aria-selected="true"]{color:var(--blue)}
[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
@media(max-width:780px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.block-container{padding-left:.7rem;padding-right:.7rem}.hero{padding:17px}.vtitle{font-size:1.2rem}.mvalue{font-size:1.07rem}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

UPSTOX_V2 = "https://api.upstox.com/v2"
UPSTOX_V3 = "https://api.upstox.com/v3"
POS_WORDS = {"profit", "growth", "order", "contract", "approval", "record", "upgrade", "dividend", "buyback", "expansion", "strong", "beats", "award", "launch", "investment", "outperform", "rally"}
NEG_WORDS = {"loss", "fraud", "probe", "penalty", "downgrade", "default", "delay", "lawsuit", "weak", "misses", "shutdown", "ban", "fall", "decline", "slump", "investigation"}


def secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "") or "")
    except Exception:
        return os.getenv(name, "")


def n(v: Any) -> float | None:
    try:
        if v is None or v == "" or (isinstance(v, float) and math.isnan(v)):
            return None
        if isinstance(v, str):
            v = v.replace(",", "").replace("%", "").strip()
        return float(v)
    except Exception:
        return None


def pct(v: float | None, input_decimal: bool = False) -> str:
    if v is None: return "N/A"
    if input_decimal: v *= 100
    return f"{v:,.1f}%"


def ratio(v: float | None) -> str:
    return "N/A" if v is None else f"{v:,.2f}x"


def price(v: float | None) -> str:
    return "N/A" if v is None else f"₹{v:,.2f}"


def money(v: float | None) -> str:
    if v is None: return "N/A"
    if abs(v) >= 1e7: return f"₹{v/1e7:,.2f} Cr"
    if abs(v) >= 1e5: return f"₹{v/1e5:,.2f} L"
    return f"₹{v:,.0f}"


def metric(label: str, value: str, note: str = "") -> str:
    return f"<div class='metric'><div class='mlabel'>{label}</div><div class='mvalue'>{value}</div><div class='mnote'>{note}</div></div>"


def api_get(url: str, token: str, params: dict | None = None) -> Any:
    r = requests.get(url, headers={"Accept":"application/json", "Authorization":f"Bearer {token}"}, params=params, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"Upstox returned {r.status_code}")
    body = r.json()
    return body.get("data", body)


def google_news(query: str, limit: int = 12) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query + ' stock NSE when:7d')}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = []
        for item in root.findall(".//item")[:limit]:
            out.append({
                "heading": item.findtext("title", ""),
                "summary": re.sub("<[^>]+>", "", item.findtext("description", "")),
                "url": item.findtext("link", ""),
                "published": item.findtext("pubDate", ""),
                "source": "Google News RSS",
            })
        return out
    except Exception:
        return []


def sentiment(item: dict) -> tuple[str, int]:
    text = f"{item.get('heading','')} {item.get('summary','')}".lower()
    p = sum(w in text for w in POS_WORDS)
    m = sum(w in text for w in NEG_WORDS)
    return ("Positive", 1) if p > m else ("Negative", -1) if m > p else ("Neutral", 0)


def news_stats(items: list[dict]) -> dict:
    vals = [sentiment(x)[1] for x in items]
    net = sum(vals)
    return {
        "count": len(items), "pos": sum(v > 0 for v in vals), "neg": sum(v < 0 for v in vals),
        "label": "Positive" if net >= 2 else "Negative" if net <= -2 else "Mixed/Neutral",
        "impact": max(-7, min(7, net * 2)),
    }


@dataclass
class StockData:
    symbol: str
    name: str = ""
    source: str = "Free fallback"
    price: float | None = None
    previous_close: float | None = None
    market_cap: float | None = None
    pe: float | None = None
    sector_pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    roce: float | None = None
    debt_equity: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    free_cash_flow: float | None = None
    operating_cash_flow: float | None = None
    total_debt: float | None = None
    cash: float | None = None
    business: str = ""
    sector: str = ""
    industry: str = ""
    history: pd.DataFrame = field(default_factory=pd.DataFrame)
    annuals: pd.DataFrame = field(default_factory=pd.DataFrame)
    news: list[dict] = field(default_factory=list)
    competitors: list[dict] = field(default_factory=list)
    ownership: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: list[str] = field(default_factory=list)


def yf_fallback(symbol: str) -> StockData:
    s = symbol.upper().strip().replace(".NS", "")
    ticker = yf.Ticker(f"{s}.NS")
    d = StockData(symbol=s, source="Yahoo Finance fallback + Google News")
    try:
        hist = ticker.history(period="5y", auto_adjust=False)
        if not hist.empty:
            hist = hist.reset_index()
            d.history = hist.rename(columns={"Date":"Date", "Close":"Close"})
            d.price = n(hist.iloc[-1]["Close"])
            d.previous_close = n(hist.iloc[-2]["Close"]) if len(hist) > 1 else None
    except Exception as e:
        d.warnings.append(f"Price history unavailable: {e}")
    info = {}
    for getter in (lambda: ticker.get_info(), lambda: ticker.info):
        try:
            info = getter() or {}
            if info: break
        except Exception:
            pass
    d.name = info.get("longName") or info.get("shortName") or s
    d.price = n(info.get("currentPrice") or info.get("regularMarketPrice")) or d.price
    d.previous_close = n(info.get("previousClose")) or d.previous_close
    d.market_cap = n(info.get("marketCap"))
    d.pe = n(info.get("trailingPE"))
    d.pb = n(info.get("priceToBook"))
    d.roe = (n(info.get("returnOnEquity")) or 0) * 100 if info.get("returnOnEquity") is not None else None
    d.debt_equity = n(info.get("debtToEquity")); d.debt_equity = d.debt_equity / 100 if d.debt_equity and d.debt_equity > 10 else d.debt_equity
    d.revenue_growth = (n(info.get("revenueGrowth")) or 0) * 100 if info.get("revenueGrowth") is not None else None
    d.profit_growth = (n(info.get("earningsGrowth")) or 0) * 100 if info.get("earningsGrowth") is not None else None
    d.profit_margin = (n(info.get("profitMargins")) or 0) * 100 if info.get("profitMargins") is not None else None
    d.operating_margin = (n(info.get("operatingMargins")) or 0) * 100 if info.get("operatingMargins") is not None else None
    d.free_cash_flow = n(info.get("freeCashflow")); d.operating_cash_flow = n(info.get("operatingCashflow"))
    d.total_debt = n(info.get("totalDebt")); d.cash = n(info.get("totalCash"))
    d.business = info.get("longBusinessSummary") or "Business description was not available from the free feed."
    d.sector = info.get("sector") or "N/A"; d.industry = info.get("industry") or "N/A"
    d.news = google_news(f"{d.name} {s}")
    if not info:
        d.warnings.append("Free fundamentals feed returned limited data. Verify ratios from exchange filings or connect Upstox.")
    return d


def upstox_search(symbol: str, token: str) -> dict | None:
    data = api_get(f"{UPSTOX_V2}/instruments/search", token, {"query":symbol, "exchange":"NSE", "segment":"EQ", "page_number":1, "records":20})
    items = data.get("instruments", data if isinstance(data, list) else []) if data else []
    candidates = [x for x in items if x.get("segment") == "NSE_EQ"]
    exact = [x for x in candidates if str(x.get("trading_symbol", "")).upper() == symbol.upper()]
    return (exact or candidates or [None])[0]


def upstox_data(symbol: str, token: str) -> StockData:
    inst = upstox_search(symbol, token)
    if not inst: raise RuntimeError("Symbol not found on Upstox")
    d = StockData(symbol=inst.get("trading_symbol", symbol), name=inst.get("short_name") or inst.get("name") or symbol, source="Upstox official APIs")
    isin, key = inst.get("isin"), inst.get("instrument_key")
    endpoints = {
        "profile": f"{UPSTOX_V2}/fundamentals/{isin}/profile",
        "ratios": f"{UPSTOX_V2}/fundamentals/{isin}/key-ratios",
        "income": f"{UPSTOX_V2}/fundamentals/{isin}/income-statement",
        "cash": f"{UPSTOX_V2}/fundamentals/{isin}/cash-flow",
        "balance": f"{UPSTOX_V2}/fundamentals/{isin}/balance-sheet",
        "holding": f"{UPSTOX_V2}/fundamentals/{isin}/share-holdings",
        "competitors": f"{UPSTOX_V2}/fundamentals/{isin}/competitors",
    }
    bundle = {}
    for k, url in endpoints.items():
        try:
            params = {"type":"consolidated", "time_period":"yearly"} if k == "income" else ({"type":"consolidated"} if k in {"cash", "balance"} else None)
            bundle[k] = api_get(url, token, params)
        except Exception as e:
            bundle[k] = None; d.warnings.append(f"{k.title()} unavailable")
    profile = bundle.get("profile") or {}
    if isinstance(profile, dict):
        d.business = profile.get("company_profile") or profile.get("business_description") or ""
        d.sector = profile.get("sector") or "N/A"
    ratios_data = bundle.get("ratios") or []
    rmap = {}
    if isinstance(ratios_data, list):
        for x in ratios_data:
            rmap[str(x.get("name", "")).upper()] = (n(x.get("company_value")), n(x.get("sector_value")))
    d.pe, d.sector_pe = rmap.get("P/E", (None, None)); d.pb = rmap.get("P/B", (None, None))[0]
    d.roe = rmap.get("ROE", (None, None))[0]; d.roce = rmap.get("ROCE", (None, None))[0]
    try:
        q = api_get(f"{UPSTOX_V3}/market-quote/ltp", token, {"instrument_key":key})
        qv = next(iter(q.values())) if isinstance(q, dict) and q else {}
        d.price = n(qv.get("last_price")); d.previous_close = n(qv.get("cp"))
    except Exception:
        d.warnings.append("Live quote unavailable")
    try:
        news_data = api_get(f"{UPSTOX_V2}/news", token, {"category":"instrument_keys", "instrument_keys":key, "page_number":1, "page_size":25})
        if isinstance(news_data, dict): d.news = news_data.get(key) or (next(iter(news_data.values())) if news_data else [])
        elif isinstance(news_data, list): d.news = news_data
    except Exception:
        d.news = google_news(f"{d.name} {d.symbol}")
        d.warnings.append("Upstox news unavailable; Google News fallback used")
    if not d.news: d.news = google_news(f"{d.name} {d.symbol}")
    try:
        end, start = date.today(), date.today() - timedelta(days=365*5)
        key_encoded = requests.utils.quote(key, safe="")
        hist = api_get(f"{UPSTOX_V3}/historical-candle/{key_encoded}/days/1/{end.isoformat()}/{start.isoformat()}", token)
        candles = (hist or {}).get("candles", [])
        if candles:
            d.history = pd.DataFrame(candles, columns=["Date","Open","High","Low","Close","Volume","OI"])
            d.history["Date"] = pd.to_datetime(d.history["Date"])
    except Exception:
        pass
    if isinstance(bundle.get("competitors"), list): d.competitors = bundle["competitors"]
    return d


def score_stock(d: StockData) -> dict:
    score = 50; reasons, risks = [], []
    def add(cond, points, pos, neg=None):
        nonlocal score
        if cond is True: score += points; reasons.append(pos)
        elif cond is False and neg: score -= abs(points); risks.append(neg)
    if d.roe is not None: add(d.roe >= 15, 10, "ROE indicates good use of shareholders’ capital", "ROE is below a healthy level")
    if d.roce is not None: add(d.roce >= 15, 8, "ROCE indicates efficient capital deployment", "ROCE is weak")
    if d.debt_equity is not None:
        if d.debt_equity <= .5: score += 8; reasons.append("Debt is manageable")
        elif d.debt_equity >= 1.5: score -= 10; risks.append("Debt/equity is high")
    if d.revenue_growth is not None:
        if d.revenue_growth >= 12: score += 8; reasons.append("Revenue growth is healthy")
        elif d.revenue_growth < 0: score -= 10; risks.append("Revenue is declining")
    if d.profit_growth is not None:
        if d.profit_growth >= 12: score += 9; reasons.append("Profit growth is healthy")
        elif d.profit_growth < 0: score -= 12; risks.append("Profit is declining")
    if d.pe is not None:
        if d.sector_pe:
            premium = (d.pe / d.sector_pe - 1) * 100
            if premium <= -15: score += 9; reasons.append("P/E is below the sector benchmark")
            elif premium >= 35: score -= 12; risks.append("Valuation is substantially above the sector")
            elif premium >= 15: score -= 5; risks.append("Valuation is above the sector benchmark")
        elif d.pe > 50: score -= 7; risks.append("P/E is demanding and requires strong growth")
        elif 0 < d.pe <= 25: score += 4; reasons.append("P/E is not excessive on an absolute basis")
    if d.operating_cash_flow is not None:
        if d.operating_cash_flow > 0: score += 5; reasons.append("Operating cash flow is positive")
        else: score -= 8; risks.append("Operating cash flow is negative")
    ns = news_stats(d.news); score += ns["impact"]
    if ns["impact"] >= 4: reasons.append("Recent company news is broadly positive")
    if ns["impact"] <= -4: risks.append("Recent company news is broadly negative")
    score = int(max(0, min(100, round(score))))
    if score >= 72: verdict = ("CONSIDER BUYING GRADUALLY", "buy", "Fundamentals and current developments are supportive. Use staggered buying and verify the latest exchange filing before investing.")
    elif score >= 52: verdict = ("WATCH / WAIT FOR A BETTER ENTRY", "wait", "The case is mixed. Wait for a better valuation, stronger results or clearer positive triggers.")
    else: verdict = ("AVOID FOR NOW", "avoid", "The available evidence does not offer a sufficiently attractive risk–reward at present.")
    return {"score":score, "verdict":verdict, "reasons":reasons[:6], "risks":risks[:6], "news":ns}


def pdf_report(d: StockData, result: dict) -> bytes:
    buf = io.BytesIO(); styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = [Paragraph(f"EquityLens AI — {d.name}", styles["Title"]), Spacer(1, 5*mm), Paragraph(result["verdict"][0], styles["Heading2"]), Paragraph(result["verdict"][2], styles["BodyText"]), Spacer(1, 4*mm)]
    rows = [["Metric","Value"],["Price",price(d.price)],["Overall score",f"{result['score']}/100"],["P/E",ratio(d.pe)],["Sector P/E",ratio(d.sector_pe)],["ROE",pct(d.roe)],["ROCE",pct(d.roce)],["Debt/Equity",ratio(d.debt_equity)],["Revenue growth",pct(d.revenue_growth)],["Profit growth",pct(d.profit_growth)],["News flow",result["news"]["label"]]]
    t = Table(rows, colWidths=[65*mm, 85*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#387ed1")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.lightgrey),("PADDING",(0,0),(-1,-1),6)])); story += [t, Spacer(1,5*mm), Paragraph("Why it may work",styles["Heading2"])]
    for x in result["reasons"] or ["No strong positive signal was available."]: story.append(Paragraph(f"• {x}",styles["BodyText"]))
    story.append(Paragraph("Risks and disadvantages",styles["Heading2"]))
    for x in result["risks"] or ["No major risk was identified from the available feed; this is not proof of absence."]: story.append(Paragraph(f"• {x}",styles["BodyText"]))
    story += [Paragraph("Business",styles["Heading2"]), Paragraph(d.business or "Not available",styles["BodyText"]), Spacer(1,4*mm), Paragraph("Important: this report is decision support, not a guarantee. Verify exchange filings and current prices.",styles["Italic"])]
    doc.build(story); return buf.getvalue()


def render_news(items: list[dict], ns: dict):
    st.markdown(f"<div class='card'><h3>Current news & event check</h3><p><b>{ns['label']}</b> · {ns['count']} articles · {ns['pos']} positive · {ns['neg']} negative</p><p class='sub'>News changes the score by at most ±7 points. Financial quality and valuation remain the main drivers.</p></div>", unsafe_allow_html=True)
    if not items: st.info("No company-specific news was returned for the past seven days.")
    for item in items[:12]:
        label, _ = sentiment(item); cls = {"Positive":"pos","Negative":"neg","Neutral":"neu"}[label]
        heading = item.get("heading") or item.get("title") or "Untitled"
        summary = item.get("summary") or ""
        link = item.get("url") or item.get("article_link") or item.get("link") or "#"
        published = item.get("published") or item.get("published_at") or ""
        st.markdown(f"<div class='news'><span class='pill {cls}'>{label}</span><div class='ntitle'>{heading}</div><div>{summary[:500]}</div><div class='nmeta'>{published} · <a href='{link}' target='_blank'>Open article</a></div></div>", unsafe_allow_html=True)


def render_stock(d: StockData):
    r = score_stock(d); title, cls, explanation = r["verdict"]
    st.markdown(f"<div class='hero'><h1>{d.name or d.symbol}</h1><p class='sub'>{d.symbol} · {d.sector} · Source: {d.source}</p></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='verdict {cls}'><div class='eyebrow'>CURRENT DECISION SUPPORT VERDICT</div><div class='vtitle'>{title}</div><p>{explanation}</p><b>Score: {r['score']}/100</b> &nbsp;·&nbsp; News: {r['news']['label']}</div>", unsafe_allow_html=True)
    change = ((d.price / d.previous_close - 1) * 100) if d.price and d.previous_close else None
    st.markdown("<div class='metric-grid'>" + "".join([
        metric("Current price", price(d.price), f"Day change {pct(change)}"), metric("Overall score", f"{r['score']}/100", title.title()),
        metric("Market cap", money(d.market_cap)), metric("P/E", ratio(d.pe), f"Sector {ratio(d.sector_pe)}"), metric("P/B", ratio(d.pb)),
        metric("ROE", pct(d.roe)), metric("ROCE", pct(d.roce)), metric("Debt/Equity", ratio(d.debt_equity)),
    ]) + "</div>", unsafe_allow_html=True)
    tabs = st.tabs(["5-minute view","Financials & chart","Business & dependencies","News & events","Risks & PDF"])
    with tabs[0]:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("<div class='card'><h3>Why this may work</h3>" + "".join(f"<p class='good'>✓ {x}</p>" for x in (r['reasons'] or ["No strong positive signal from available data."])) + "</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='card'><h3>Disadvantages and risks</h3>" + "".join(f"<p class='bad'>! {x}</p>" for x in (r['risks'] or ["No major risk was identified from the available feed; verify filings."])) + "</div>", unsafe_allow_html=True)
        rows = pd.DataFrame([
            ["Should I invest?", title],["Business quality", "Strong" if (d.roe or 0)>=15 else "Needs review"],["Growth", "Strong" if (d.revenue_growth or 0)>=12 else "Moderate/unknown"],
            ["Valuation", "Expensive" if d.pe and d.sector_pe and d.pe>d.sector_pe*1.25 else "Reasonable/unknown"],["Debt", "Low" if d.debt_equity is not None and d.debt_equity<=.5 else "Review"],
            ["News flow",r['news']['label']],["Data confidence","Higher" if "Upstox" in d.source else "Medium / verify"],
        ], columns=["Question","Answer"])
        st.dataframe(rows, hide_index=True, width="stretch")
    with tabs[1]:
        if not d.history.empty and "Close" in d.history.columns:
            fig = px.line(d.history.sort_values("Date"), x="Date", y="Close", title="Five-year share-price history")
            fig.update_layout(height=420, margin=dict(l=10,r=10,t=55,b=10), paper_bgcolor="#fff", plot_bgcolor="#fff")
            st.plotly_chart(fig, width="stretch")
        metrics = pd.DataFrame([
            ["Revenue growth",pct(d.revenue_growth)],["Profit growth",pct(d.profit_growth)],["Operating margin",pct(d.operating_margin)],
            ["Profit margin",pct(d.profit_margin)],["Operating cash flow",money(d.operating_cash_flow)],["Free cash flow",money(d.free_cash_flow)],
            ["Total debt",money(d.total_debt)],["Cash",money(d.cash)]
        ],columns=["Financial check","Result"])
        st.dataframe(metrics, hide_index=True, width="stretch")
    with tabs[2]:
        st.markdown(f"<div class='card'><h3>What the company does</h3><p>{d.business or 'Business description unavailable.'}</p><p><b>Sector:</b> {d.sector} &nbsp; <b>Industry:</b> {d.industry}</p></div>", unsafe_allow_html=True)
        deps = ["Demand in its main industry", "Raw-material and input costs", "Interest rates and access to capital", "Government/regulatory policy", "Execution by management"]
        st.markdown("<div class='card'><h3>Major business dependencies to verify</h3>" + "".join(f"<p>• {x}</p>" for x in deps) + "<p class='sub'>Company-specific concentration requires annual-report/RHP extraction; it is not inferred when the source does not provide it.</p></div>", unsafe_allow_html=True)
        if d.competitors:
            st.dataframe(pd.DataFrame(d.competitors), hide_index=True, width="stretch")
    with tabs[3]: render_news(d.news, r["news"])
    with tabs[4]:
        if d.warnings:
            st.warning(" · ".join(d.warnings))
        st.markdown("<div class='card'><h3>What can go wrong?</h3><p>Results can weaken because of competition, regulation, commodity/input costs, customer concentration, capital-allocation mistakes, leverage, or an expensive starting valuation. Check the latest quarterly filing and exchange announcements before acting.</p></div>", unsafe_allow_html=True)
        st.download_button("Download PDF research report", pdf_report(d,r), file_name=f"{d.symbol}_EquityLens_Report.pdf", mime="application/pdf", width="stretch")


def ipo_screen(token: str):
    st.markdown("<div class='hero'><h1>IPO Research</h1><p class='sub'>Mainboard and SME IPO discovery, issue structure, subscription and decision checklist.</p></div>", unsafe_allow_html=True)
    if not token:
        st.info("Live automatic IPO discovery requires an Upstox Analytics/Access Token. The listed-share research section still works in free fallback mode.")
        st.markdown("<div class='card'><h3>Manual IPO checklist</h3><p>Until the token is connected, verify: RHP financials, peer P/E, fresh issue vs OFS, use of proceeds, QIB/NII/retail subscription, promoter litigation, customer concentration, cash-flow quality and SME liquidity.</p></div>", unsafe_allow_html=True)
        return
    status = st.selectbox("IPO stage", ["open","upcoming","closed","listed"])
    issue_type = st.radio("Issue type", ["regular","sme"], horizontal=True, format_func=lambda x: "Mainboard" if x=="regular" else "SME")
    try:
        data = api_get(f"{UPSTOX_V2}/ipos", token, {"status":status,"issue_type":issue_type,"page_number":1,"records":30})
        items = data.get("ipos", data if isinstance(data,list) else []) if data else []
        if not items: st.info("No IPOs returned for this filter."); return
        names = [x.get("name") or x.get("company_name") or x.get("id") for x in items]
        idx = st.selectbox("Select IPO", range(len(items)), format_func=lambda i:names[i])
        item = items[idx]
        detail = api_get(f"{UPSTOX_V2}/ipos/{item.get('id')}", token)
        st.json(detail, expanded=False)
        st.warning("IPO recommendation logic will only be produced when the API returns verified financial and subscription fields. The app will not score missing values as positive.")
    except Exception as e: st.error(f"IPO data could not be loaded: {e}")


st.markdown("<div class='hero'><h1>EquityLens AI</h1><p class='sub'>Stocks, IPOs, fundamentals, valuation and current news — in one five-minute dashboard.</p></div>", unsafe_allow_html=True)

token = secret("UPSTOX_ACCESS_TOKEN")
mode = st.radio("Research mode", ["Listed Share","IPO — Mainboard / SME"], horizontal=True)
if mode.startswith("Listed"):
    c1,c2 = st.columns([3,1])
    with c1: symbol = st.text_input("NSE symbol", value="RELIANCE", placeholder="Example: MAZDOCK")
    with c2: run = st.button("Analyse share", width="stretch")
    if not token:
        with st.expander("Optional: connect Upstox for higher-quality data"):
            st.markdown("The app is running in free fallback mode. To unlock official fundamentals, competitors, IPOs and instrument news, add this in **Manage app → Settings → Secrets**:")
            st.code('UPSTOX_ACCESS_TOKEN = "your_token_here"', language="toml")
    if run:
        with st.spinner("Checking financials, valuation, price history and current news…"):
            try:
                d = upstox_data(symbol.strip(), token) if token else yf_fallback(symbol.strip())
                if d.price is None and d.pe is None and d.history.empty:
                    st.error("No usable data was returned. Check the exact NSE symbol or try again later.")
                else: render_stock(d)
            except Exception as e:
                st.warning(f"Official feed could not be used ({e}). Trying the free fallback…")
                try:
                    d = yf_fallback(symbol.strip()); render_stock(d)
                except Exception as e2: st.error(f"The stock could not be analysed: {e2}")
else:
    ipo_screen(token)

st.markdown("<div class='source'>EquityLens provides structured decision support, not guaranteed returns or personalised investment advice. Live prices, filings and corporate announcements should be verified before investing.</div>", unsafe_allow_html=True)
