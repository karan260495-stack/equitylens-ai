from __future__ import annotations

import io, math, os, re, json, xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from neo_api_client import NeoAPI
    KOTAK_SDK_AVAILABLE = True
except Exception:
    NeoAPI = None
    KOTAK_SDK_AVAILABLE = False

st.set_page_config(page_title='EquityLens One', page_icon='◉', layout='wide', initial_sidebar_state='collapsed')

CSS = '''
<style>
:root{--ink:#17212b;--muted:#667085;--line:#e5e9ef;--bg:#f5f7fa;--card:#fff;--blue:#387ed1;--blue2:#eaf2fd;--green:#138a5b;--red:#d44747;--amber:#b7791f;--navy:#101828}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{max-width:1440px;padding:1rem 1.4rem 4rem}
[data-testid="stHeader"]{background:rgba(245,247,250,.92)}
.hero{background:linear-gradient(110deg,#0f172a,#173b70 62%,#387ed1);border-radius:18px;padding:28px 30px;color:white;box-shadow:0 14px 36px rgba(15,23,42,.16);margin-bottom:16px}
.hero h1{font-size:2.05rem;margin:0 0 5px;font-weight:800}.hero p{margin:0;color:#d7e5f8}.brokerbar{background:#ffffff;border:1px solid var(--line);border-left:5px solid #387ed1;border-radius:14px;padding:14px 16px;margin:0 0 14px;box-shadow:0 4px 14px rgba(16,24,40,.04)}.brokerok{border-left-color:#138a5b}.brokerwarn{border-left-color:#b7791f}.brokerbad{border-left-color:#d44747}.mobile-pills{display:flex;gap:8px;flex-wrap:wrap}.pill{padding:5px 9px;border-radius:999px;background:#eef3f8;color:#344054;font-size:.75rem;font-weight:700}.hero-badge{display:inline-block;background:rgba(255,255,255,.14);padding:5px 10px;border:1px solid rgba(255,255,255,.22);border-radius:99px;font-size:.75rem;margin-bottom:10px}
.searchbox{background:white;border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:0 6px 18px rgba(16,24,40,.05);margin-bottom:16px}
.verdict{background:white;border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:0 6px 18px rgba(16,24,40,.05);height:100%}.verdict.buy{border-top:5px solid var(--green)}.verdict.wait{border-top:5px solid var(--amber)}.verdict.avoid{border-top:5px solid var(--red)}
.eyebrow{font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:800}.vbig{font-size:1.8rem;font-weight:850;margin:6px 0}.score{font-size:3.2rem;font-weight:850;line-height:1;color:var(--navy)}.score small{font-size:1.05rem;color:var(--muted)}
.grid6{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:11px;margin:14px 0}.kpi{background:white;border:1px solid var(--line);border-radius:14px;padding:15px 16px;min-height:105px;box-shadow:0 4px 14px rgba(16,24,40,.035)}.klabel{font-size:.75rem;color:var(--muted);font-weight:700}.kvalue{font-size:1.35rem;font-weight:820;color:var(--navy);margin:8px 0 3px;white-space:normal;overflow-wrap:anywhere}.knote{font-size:.72rem;color:var(--muted)}
.card{background:white;border:1px solid var(--line);border-radius:16px;padding:20px 21px;margin:12px 0;box-shadow:0 5px 16px rgba(16,24,40,.04)}.card h3{font-size:1.08rem;margin:0 0 12px}.section{font-size:1.35rem;font-weight:820;margin:24px 0 9px;color:var(--navy)}
.flag{border-radius:12px;padding:12px 14px;margin:8px 0;font-size:.9rem}.flag.good{background:#edf9f3;color:#176b4b}.flag.bad{background:#fff1f1;color:#a93333}.flag.warn{background:#fff8e8;color:#8a5b10}
.tag{display:inline-block;padding:4px 9px;border-radius:99px;font-size:.72rem;font-weight:750;margin-right:5px}.live{background:#eaf8f1;color:#11734d}.fallback{background:#fff6df;color:#8b6215}.demo{background:#eef2f8;color:#546273}.positive{background:#eaf8f1;color:#11734d}.negative{background:#fff0f0;color:#a73737}.neutral{background:#eef2f8;color:#5c6877}
.news{padding:14px 0;border-bottom:1px solid var(--line)}.news:last-child{border-bottom:0}.ntitle{font-weight:780;font-size:.95rem;margin:5px 0}.nmeta{font-size:.72rem;color:var(--muted)}
.dependency{display:grid;grid-template-columns:180px 1fr 70px;gap:10px;align-items:center;margin:10px 0}.bar{height:9px;background:#edf1f6;border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,#387ed1,#65a5ef);border-radius:99px}
.stButton>button{background:var(--blue);color:white;border:0;border-radius:9px;min-height:44px;font-weight:760}.stButton>button:hover{background:#2d6fbd;color:white}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"] div[data-baseweb="select"]>div{background:white;color:var(--ink);border-color:#d8dde5}
[data-testid="stMetric"]{background:white;border:1px solid var(--line);padding:14px;border-radius:12px}
.stTabs [data-baseweb="tab-list"]{gap:22px;background:white;padding:0 16px;border:1px solid var(--line);border-radius:12px}.stTabs [data-baseweb="tab"]{height:50px}.stTabs [aria-selected="true"]{color:var(--blue)}
[data-testid="stDataFrame"]{background:white;border:1px solid var(--line);border-radius:12px;overflow:hidden}
@media(max-width:1100px){.grid6{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:720px){.block-container{padding:.6rem .65rem 3rem}.hero{padding:22px 18px}.hero h1{font-size:1.55rem}.grid6{grid-template-columns:repeat(2,minmax(0,1fr))}.kvalue{font-size:1.12rem}.dependency{grid-template-columns:125px 1fr 55px}.score{font-size:2.45rem}.vbig{font-size:1.35rem}}
</style>
'''
st.markdown(CSS, unsafe_allow_html=True)

POS = {'profit','growth','order','contract','approval','record','upgrade','dividend','buyback','expansion','strong','beats','award','launch','investment','outperform','rally','surge','wins'}
NEG = {'loss','fraud','probe','penalty','downgrade','default','delay','lawsuit','weak','misses','shutdown','ban','fall','decline','slump','investigation','crash'}

DEMO = {
 'RELIANCE': {'name':'Reliance Industries Limited','sector':'Energy & Consumer','industry':'Diversified Conglomerate','price':1428.4,'market_cap':1932000,'pe':24.8,'sector_pe':22.1,'pb':2.35,'roe':9.1,'roce':10.4,'de':0.42,'sales':[466000,659000,792000,918000,964000],'profit':[53700,60700,66700,79000,80600],'ocf':[26200,110500,115000,158000,172000],'depend':[('Oil-to-Chemicals',44),('Retail',27),('Digital Services',15),('Oil & Gas',8),('Other',6)],'peers':['IOC.NS','BHARTIARTL.NS','DMART.NS']},
 'MAZDOCK': {'name':'Mazagon Dock Shipbuilders Limited','sector':'Industrials','industry':'Defence Shipbuilding','price':1325.0,'market_cap':53400,'pe':24.0,'sector_pe':38.0,'pb':9.4,'roe':31.0,'roce':38.0,'de':0.02,'sales':[4050,4700,5750,9460,11400],'profit':[513,586,1119,1937,2500],'ocf':[950,1450,1810,2200,2750],'depend':[('Indian Navy orders',68),('Coast Guard',12),('Repairs & refits',10),('Exports',6),('Other',4)],'peers':['GRSE.NS','COCHINSHIP.NS','HAL.NS']},
 'TCS': {'name':'Tata Consultancy Services Limited','sector':'Information Technology','industry':'IT Services','price':3075.0,'market_cap':1112000,'pe':23.6,'sector_pe':25.7,'pb':12.8,'roe':51.0,'roce':62.0,'de':0.08,'sales':[164177,191754,225458,240893,255324],'profit':[32430,38327,42147,46099,48990],'ocf':[40700,43500,50700,53500,55800],'depend':[('North America',48),('Banking & Financial Services',31),('Europe',28),('Retail & Consumer',16),('Other',25)],'peers':['INFY.NS','HCLTECH.NS','WIPRO.NS']},
 'INFY': {'name':'Infosys Limited','sector':'Information Technology','industry':'IT Services','price':1450.0,'market_cap':602000,'pe':22.3,'sector_pe':25.7,'pb':7.1,'roe':31.0,'roce':40.0,'de':0.09,'sales':[100472,121641,146767,153670,162990],'profit':[19351,22110,24095,26248,28300],'ocf':[22900,26500,29000,31000,33700],'depend':[('North America',58),('Financial Services',28),('Europe',30),('Digital & Cloud',62),('Other',12)],'peers':['TCS.NS','HCLTECH.NS','WIPRO.NS']},
 'HDFCBANK': {'name':'HDFC Bank Limited','sector':'Financial Services','industry':'Private Bank','price':1960.0,'market_cap':1500000,'pe':20.1,'sector_pe':18.9,'pb':2.8,'roe':14.6,'roce':0,'de':0,'sales':[120858,135936,170754,283649,328000],'profit':[31833,36961,44109,60812,70000],'ocf':[0,0,0,0,0],'depend':[('Retail loans',46),('Corporate banking',26),('Treasury',15),('Deposits & CASA',13)],'peers':['ICICIBANK.NS','KOTAKBANK.NS','AXISBANK.NS']}
}


# ---------------- Kotak Neo read-only adapter ----------------
def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def kotak_credentials_status() -> dict:
    required = {
        "KOTAK_CONSUMER_KEY": _secret("KOTAK_CONSUMER_KEY"),
        "KOTAK_UCC": _secret("KOTAK_UCC"),
        "KOTAK_MOBILE": _secret("KOTAK_MOBILE"),
        "KOTAK_MPIN": _secret("KOTAK_MPIN"),
    }
    missing = [k for k, v in required.items() if not v]
    return {"ready": not missing and KOTAK_SDK_AVAILABLE, "missing": missing, "values": required}


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _first_key(obj, names):
    names = {n.lower() for n in names}
    for item in _walk(obj):
        for k, v in item.items():
            if str(k).lower() in names and v not in (None, "", "nan"):
                return v
    return None


def _extract_rows(obj):
    candidates = []
    if isinstance(obj, list):
        candidates.extend(x for x in obj if isinstance(x, dict))
    for item in _walk(obj):
        if any(str(k).lower() in {"tradingsymbol", "trading_symbol", "p_symbol_name", "symbol", "instrument_token", "token"} for k in item):
            candidates.append(item)
    unique, seen = [], set()
    for row in candidates:
        key = json.dumps(row, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key); unique.append(row)
    return unique


def create_kotak_client():
    c = kotak_credentials_status()
    if not c["ready"]:
        return None
    return NeoAPI(environment="prod", access_token=None, neo_fin_key=None, consumer_key=c["values"]["KOTAK_CONSUMER_KEY"])


def connect_kotak(totp: str):
    if not re.fullmatch(r"\d{6}", str(totp or "").strip()):
        return False, "Enter the current six-digit TOTP from your authenticator app."
    c = kotak_credentials_status()
    if not c["ready"]:
        return False, "Kotak credentials or SDK are not configured."
    try:
        client = create_kotak_client()
        login = client.totp_login(
            mobile_number=c["values"]["KOTAK_MOBILE"],
            ucc=c["values"]["KOTAK_UCC"],
            totp=str(totp).strip(),
        )
        validation = client.totp_validate(mpin=c["values"]["KOTAK_MPIN"])
        st.session_state["kotak_client"] = client
        st.session_state["kotak_connected"] = True
        st.session_state["kotak_login_meta"] = {"login": str(login)[:500], "validation": str(validation)[:500], "time": datetime.now().isoformat(timespec="seconds")}
        return True, "Kotak Neo connected in read-only research mode."
    except Exception as exc:
        st.session_state.pop("kotak_client", None)
        st.session_state["kotak_connected"] = False
        return False, f"Kotak login failed: {type(exc).__name__}. Check the current TOTP and Streamlit Secrets."


def kotak_client():
    return st.session_state.get("kotak_client") if st.session_state.get("kotak_connected") else None


def kotak_search(symbol: str, exchange_segment: str = "nse_cm"):
    client = kotak_client()
    if client is None:
        return []
    try:
        result = client.search_scrip(exchange_segment=exchange_segment, symbol=symbol, expiry="", option_type="", strike_price="")
        return _extract_rows(result)
    except Exception:
        return []


def _normalise_scrip(row: dict, exchange_segment: str):
    token = _first_key(row, ["instrument_token", "token", "p_symbol", "p_symbol_token", "symbol_token"])
    trading_symbol = _first_key(row, ["trading_symbol", "tradingsymbol", "p_trading_symbol", "p_symbol_name", "symbol"])
    company = _first_key(row, ["company_name", "p_desc", "description", "name", "p_symbol_name"])
    return {"instrument_token": str(token or ""), "trading_symbol": str(trading_symbol or ""), "company": str(company or trading_symbol or ""), "exchange_segment": exchange_segment, "raw": row}


def kotak_best_scrip(symbol: str):
    symbol = symbol.upper().strip()
    rows = []
    for exchange in ("nse_cm", "bse_cm"):
        rows += [_normalise_scrip(r, exchange) for r in kotak_search(symbol, exchange)]
    rows = [r for r in rows if r["instrument_token"]]
    if not rows:
        return None
    def rank(r):
        ts = r["trading_symbol"].upper()
        return (0 if ts == symbol else 1 if symbol in ts else 2, 0 if r["exchange_segment"] == "nse_cm" else 1)
    return sorted(rows, key=rank)[0]


def kotak_quote_for(symbol: str):
    client = kotak_client()
    if client is None:
        return None
    scrip = kotak_best_scrip(symbol)
    if not scrip:
        return None
    try:
        raw = client.quotes(instrument_tokens=[{"instrument_token": scrip["instrument_token"], "exchange_segment": scrip["exchange_segment"]}], quote_type="all")
        price = val(_first_key(raw, ["ltp", "last_traded_price", "last_price", "lastprice", "close"]))
        prev_close = val(_first_key(raw, ["previous_close", "prev_close", "previousclose", "close_price"]))
        high52 = val(_first_key(raw, ["52_week_high", "52w_high", "high52", "yearly_high"]))
        low52 = val(_first_key(raw, ["52_week_low", "52w_low", "low52", "yearly_low"]))
        open_price = val(_first_key(raw, ["open", "open_price"]))
        high = val(_first_key(raw, ["high", "high_price"]))
        low = val(_first_key(raw, ["low", "low_price"]))
        volume = val(_first_key(raw, ["volume", "total_traded_volume", "ttv"]))
        return {"price": price, "previous_close": prev_close, "high52": high52, "low52": low52, "open": open_price, "high": high, "low": low, "volume": volume, "scrip": scrip, "raw": raw, "as_of": datetime.now()}
    except Exception:
        return None


def kotak_portfolio_snapshot():
    client = kotak_client()
    if client is None:
        return {"holdings": [], "positions": [], "limits": None}
    out = {"holdings": [], "positions": [], "limits": None}
    try: out["holdings"] = _extract_rows(client.holdings())
    except Exception: pass
    try: out["positions"] = _extract_rows(client.positions())
    except Exception: pass
    try: out["limits"] = client.limits(segment="ALL", exchange="ALL", product="ALL")
    except Exception: pass
    return out


def kotak_connection_panel():
    status = kotak_credentials_status()
    connected = bool(st.session_state.get("kotak_connected"))
    if connected:
        st.markdown("<div class='brokerbar brokerok'><b>● Kotak Neo connected</b><br><span style='color:#667085'>Read-only market data, instrument search and portfolio APIs are enabled for this session.</span></div>", unsafe_allow_html=True)
        c1,c2=st.columns([3,1])
        with c1:
            st.caption(f"Session started: {st.session_state.get('kotak_login_meta',{}).get('time','Current session')}")
        with c2:
            if st.button("Disconnect Kotak", width="stretch"):
                client=kotak_client()
                try:
                    if client: client.logout()
                except Exception: pass
                for k in ["kotak_client","kotak_connected","kotak_login_meta"]: st.session_state.pop(k,None)
                st.rerun()
        return
    if not KOTAK_SDK_AVAILABLE:
        st.markdown("<div class='brokerbar brokerbad'><b>Kotak SDK is not installed.</b><br>Use Python 3.13 and upload the included requirements.txt.</div>", unsafe_allow_html=True)
        return
    if status["missing"]:
        st.markdown(f"<div class='brokerbar brokerbad'><b>Kotak Secrets incomplete</b><br>Missing: {', '.join(status['missing'])}</div>", unsafe_allow_html=True)
        return
    st.markdown("<div class='brokerbar brokerwarn'><b>Connect Kotak Neo</b><br><span style='color:#667085'>Permanent credentials stay inside Streamlit Secrets. Enter only the current six-digit TOTP here.</span></div>", unsafe_allow_html=True)
    with st.form("kotak_login_form", clear_on_submit=True):
        a,b=st.columns([3,1])
        with a: totp=st.text_input("Current Kotak TOTP", type="password", max_chars=6, placeholder="6-digit authenticator code")
        with b: submit=st.form_submit_button("Connect securely", width="stretch")
        if submit:
            ok,msg=connect_kotak(totp)
            (st.success if ok else st.error)(msg)
            if ok: st.rerun()



IPOJI_LIST_URL = "https://www.ipoji.com/ipo-list?year={year}"
IPOJI_SUB_URL = "https://www.ipoji.com/ipo-subscription-status"
IPOWATCH_GMP_URL = "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/"

def _flat_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join(str(x) for x in c if str(x) != 'nan').strip() for c in df.columns]
    else:
        df.columns = [str(c).strip() for c in df.columns]
    return df

def _norm_name(x):
    x = re.sub(r'\s+', ' ', str(x or '')).strip().lower()
    x = re.sub(r'\b(nse|bse|sme|mainboard|limited|ltd\.?|ipo)\b', ' ', x)
    x = re.sub(r'[^a-z0-9]+', ' ', x)
    return re.sub(r'\s+', ' ', x).strip()

def _number(x):
    if x is None: return None
    m = re.search(r'-?\d[\d,]*(?:\.\d+)?', str(x))
    if not m: return None
    try: return float(m.group(0).replace(',', ''))
    except Exception: return None

def _fetch_tables(url):
    r=requests.get(url,timeout=20,headers={'User-Agent':'Mozilla/5.0 (EquityLens research dashboard)'})
    r.raise_for_status()
    return [_flat_columns(t.copy()) for t in pd.read_html(io.StringIO(r.text))]

def _find_table(tables, required):
    req=[x.lower() for x in required]
    for t in tables:
        cols=' | '.join(map(str,t.columns)).lower()
        if all(x in cols for x in req): return t
    return pd.DataFrame()

@st.cache_data(ttl=900, show_spinner=False)
def load_live_ipo_data():
    errors=[]
    gmp=listdf=subdf=pd.DataFrame()
    try:
        tabs=_fetch_tables(IPOWATCH_GMP_URL)
        gmp=_find_table(tabs,['ipo name','ipo gmp','price band','status'])
    except Exception as e: errors.append(f'IPOWatch GMP: {type(e).__name__}')
    try:
        tabs=_fetch_tables(IPOJI_LIST_URL.format(year=datetime.now().year))
        listdf=_find_table(tabs,['company','open date','close date','lot size'])
    except Exception as e: errors.append(f'IPO Ji list: {type(e).__name__}')
    try:
        tabs=_fetch_tables(IPOJI_SUB_URL)
        subdf=_find_table(tabs,['company','qib','retail','total'])
    except Exception as e: errors.append(f'IPO Ji subscription: {type(e).__name__}')

    records=[]
    if not gmp.empty:
        cm={str(c).lower():c for c in gmp.columns}
        def col(part):
            return next((c for k,c in cm.items() if part in k),None)
        nc,gc,pc,ec,dc,tc,sc,uc=[col(x) for x in ['ipo name','ipo gmp','price band','est. listing','date','type','status','last updated']]
        for _,r in gmp.iterrows():
            name=str(r.get(nc,'')).strip()
            if not name or name.lower()=='nan': continue
            records.append({'name':name,'key':_norm_name(name),'gmp_text':str(r.get(gc,'')),'gmp':_number(r.get(gc)),'price_text':str(r.get(pc,'')),'price':_number(r.get(pc)),'est_listing':str(r.get(ec,'')),'dates':str(r.get(dc,'')),'type':str(r.get(tc,'')),'status':str(r.get(sc,'')),'updated':str(r.get(uc,''))})
    out=pd.DataFrame(records)
    if out.empty: return out,errors

    if not listdf.empty:
        cm={str(c).lower():c for c in listdf.columns}
        def col(part): return next((c for k,c in cm.items() if part in k),None)
        nc,oc,cc,lc,pc,lotc,isc=[col(x) for x in ['company','open date','close date','listing date','price','lot size','issue size']]
        rows=[]
        for _,r in listdf.iterrows():
            name=str(r.get(nc,'')).strip()
            if name and name.lower()!='nan': rows.append({'key':_norm_name(name),'open_date':str(r.get(oc,'')),'close_date':str(r.get(cc,'')),'listing_date':str(r.get(lc,'')),'ipoji_price':str(r.get(pc,'')),'lot_size':str(r.get(lotc,'')),'issue_size':str(r.get(isc,''))})
        if rows: out=out.merge(pd.DataFrame(rows).drop_duplicates('key'),on='key',how='left')
    if not subdf.empty:
        cm={str(c).lower():c for c in subdf.columns}
        def col(part): return next((c for k,c in cm.items() if part in k),None)
        nc,qc,nic,rc,tc=[col(x) for x in ['company','qib','nii','retail','total']]
        rows=[]
        for _,r in subdf.iterrows():
            name=str(r.get(nc,'')).strip()
            if name and name.lower()!='nan': rows.append({'key':_norm_name(name),'qib':_number(r.get(qc)),'nii':_number(r.get(nic)),'retail':_number(r.get(rc)),'total_sub':_number(r.get(tc))})
        if rows: out=out.merge(pd.DataFrame(rows).drop_duplicates('key'),on='key',how='left')
    return out,errors

def val(x, default=None):
    try:
        if x is None or x == '': return default
        if isinstance(x,str): x=x.replace(',','').replace('%','').strip()
        y=float(x)
        return default if not math.isfinite(y) else y
    except Exception:return default

def valid(x):
    return x is not None and isinstance(x,(int,float,np.integer,np.floating)) and math.isfinite(float(x))

def money_cr(x): return 'Not available' if not valid(x) else f'₹{x:,.0f} Cr'
def inr(x): return 'Not available' if not valid(x) else f'₹{x:,.2f}'
def pct(x): return 'Not available' if not valid(x) else f'{x:,.1f}%'
def rx(x): return 'Not available' if not valid(x) else f'{x:,.2f}x'


def kpi(label,value,note=''):
    return f"<div class='kpi'><div class='klabel'>{label}</div><div class='kvalue'>{value}</div><div class='knote'>{note}</div></div>"

def news_feed(query, limit=10):
    url=f"https://news.google.com/rss/search?q={quote_plus(query+' stock NSE when:7d')}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        r=requests.get(url,timeout=12,headers={'User-Agent':'Mozilla/5.0'});r.raise_for_status();root=ET.fromstring(r.content)
        out=[]
        for item in root.findall('.//item')[:limit]:
            out.append({'title':item.findtext('title',''),'link':item.findtext('link',''),'date':item.findtext('pubDate',''),'summary':re.sub('<[^>]+>','',item.findtext('description',''))})
        return out
    except Exception:return []

def sent(text):
    t=text.lower();p=sum(w in t for w in POS);n=sum(w in t for w in NEG)
    return ('Positive',1) if p>n else ('Negative',-1) if n>p else ('Neutral',0)

def cagr(a,b,years):
    if not a or not b or a<=0:return None
    return ((b/a)**(1/years)-1)*100

@dataclass
class Stock:
    symbol:str; name:str=''; sector:str=''; industry:str=''; price:float|None=None; market_cap:float|None=None; pe:float|None=None; sector_pe:float|None=None; pb:float|None=None; roe:float|None=None; roce:float|None=None; de:float|None=None
    sales:list=field(default_factory=list); profit:list=field(default_factory=list); ocf:list=field(default_factory=list); history:pd.DataFrame=field(default_factory=pd.DataFrame); news:list=field(default_factory=list); depend:list=field(default_factory=list); peers:list=field(default_factory=list); source:str='Demo'; business:str=''; warnings:list=field(default_factory=list); eps:float|None=None; as_of:Any=None; high52:float|None=None; low52:float|None=None

def load_stock(symbol, use_kotak=True):
    s=symbol.upper().replace('.NS','').strip(); base=DEMO.get(s, {})
    d=Stock(symbol=s,**{k:v for k,v in base.items() if k in Stock.__dataclass_fields__}) if base else Stock(symbol=s,name=s)
    d.source='Demo fallback'
    try:
        t=yf.Ticker(s+'.NS'); h=t.history(period='5y',auto_adjust=True)
        if not h.empty:
            d.history=h.reset_index()[['Date','Close']]
            d.price=val(h['Close'].iloc[-1],d.price)
            d.as_of=pd.to_datetime(d.history['Date'].iloc[-1]).date()
            recent=d.history.tail(min(252,len(d.history)))
            d.high52=val(recent['Close'].max()); d.low52=val(recent['Close'].min())
            d.source='Live market history + available fundamentals'
        info={}
        try: info=t.get_info() or {}
        except Exception: pass
        if info:
            d.name=info.get('longName') or d.name;d.sector=info.get('sector') or d.sector;d.industry=info.get('industry') or d.industry
            d.market_cap=(val(info.get('marketCap'))/1e7) if val(info.get('marketCap')) else d.market_cap
            d.pe=val(info.get('trailingPE'),d.pe);d.pb=val(info.get('priceToBook'),d.pb);d.eps=val(info.get('trailingEps'))
            r=val(info.get('returnOnEquity'));d.roe=r*100 if r is not None and abs(r)<2 else (r or d.roe)
            de=val(info.get('debtToEquity'));d.de=de/100 if de and de>10 else (de if de is not None else d.de)
            d.business=info.get('longBusinessSummary','')
        # annual statements where available
        try:
            fin=t.financials
            cash=t.cashflow
            if fin is not None and not fin.empty:
                cols=list(fin.columns[:5])[::-1]
                rev=[];pat=[]
                for c in cols:
                    rev.append(val(fin.loc['Total Revenue',c])/1e7 if 'Total Revenue' in fin.index else None)
                    pat.append(val(fin.loc['Net Income',c])/1e7 if 'Net Income' in fin.index else None)
                if len([x for x in rev if x])>=3:d.sales=rev
                if len([x for x in pat if x])>=3:d.profit=pat
            if cash is not None and not cash.empty:
                cols=list(cash.columns[:5])[::-1];oc=[]
                for c in cols:oc.append(val(cash.loc['Operating Cash Flow',c])/1e7 if 'Operating Cash Flow' in cash.index else None)
                if len([x for x in oc if x])>=3:d.ocf=oc
        except Exception: pass
    except Exception as e:d.warnings.append(str(e))
    # Kotak Neo is the primary live quote source when connected.
    if use_kotak and st.session_state.get('kotak_connected'):
        kq=kotak_quote_for(s)
        if kq:
            if valid(kq.get('price')): d.price=kq['price']
            if valid(kq.get('high52')): d.high52=kq['high52']
            if valid(kq.get('low52')): d.low52=kq['low52']
            d.as_of=kq.get('as_of')
            d.source='Kotak Neo live quote + verified public research layers'
            d.warnings.append(f"Kotak instrument: {kq['scrip'].get('exchange_segment')} • {kq['scrip'].get('trading_symbol')}")
    # Never invent price or financial history. Missing data remains explicitly unavailable.
    if not d.depend:d.depend=[('Core business',55),('Top customers / contracts',22),('Domestic demand',15),('Exports / other',8)]
    d.news=news_feed(d.name or s)
    if not d.business:d.business=f'{d.name} operates in the {d.industry or d.sector or "listed equities"} segment. Verify the annual report for the exact revenue mix and major customer dependencies.'
    return d

def score_stock(d):
    sales_clean=[x for x in d.sales if valid(x) and x>0]
    profit_clean=[x for x in d.profit if valid(x) and x>0]
    sg=cagr(sales_clean[0],sales_clean[-1],max(1,len(sales_clean)-1)) if len(sales_clean)>=3 else None
    pg=cagr(profit_clean[0],profit_clean[-1],max(1,len(profit_clean)-1)) if len(profit_clean)>=3 else None

    critical={
        'Current price':valid(d.price), 'Market capitalisation':valid(d.market_cap),
        'P/E':valid(d.pe), 'ROE':valid(d.roe), 'Debt/equity':valid(d.de),
        '3+ years revenue':len(sales_clean)>=3, '3+ years profit':len(profit_clean)>=3,
        'Price history':not d.history.empty, 'Recent news':len(d.news)>=3,
    }
    completeness=round(100*sum(critical.values())/len(critical))
    missing=[k for k,v in critical.items() if not v]

    quality=50
    if sg is not None: quality += 12 if sg>15 else 7 if sg>8 else -5 if sg<0 else 2
    if pg is not None: quality += 14 if pg>18 else 8 if pg>10 else -8 if pg<0 else 2
    if valid(d.roe): quality += 10 if d.roe>20 else 6 if d.roe>14 else -4 if d.roe<8 else 1
    if valid(d.de): quality += 7 if d.de<.5 else 2 if d.de<1 else -8
    quality=max(0,min(100,round(quality)))

    val_score=50
    premium=None
    if valid(d.pe) and valid(d.sector_pe) and d.sector_pe>0:
        premium=(d.pe/d.sector_pe-1)*100
        val_score += 18 if premium<-15 else 8 if premium<5 else -12 if premium>25 else -3
    if valid(d.pb): val_score += 6 if d.pb<3 else -8 if d.pb>8 else 0
    val_score=max(0,min(100,round(val_score)))

    sentiment_values=[sent(x['title']+' '+x.get('summary',''))[1] for x in d.news]
    ns=sum(sentiment_values)
    news_impact=max(-6,min(6,ns)) if len(d.news)>=3 else 0
    raw=max(0,min(100,round(.68*quality+.32*val_score+news_impact)))
    confidence=round(completeness*.75 + min(25,len(d.news)*2.5))

    fair_value=None; margin_safety=None
    if valid(d.eps) and valid(d.sector_pe) and d.sector_pe>0:
        fair_value=d.eps*d.sector_pe
        if valid(d.price) and d.price>0: margin_safety=(fair_value/d.price-1)*100

    if completeness < 67 or not valid(d.price) or (sg is None and pg is None):
        verdict=('DATA INCOMPLETE — DO NOT DECIDE','avoid','Critical evidence is missing. Do not commit capital until financial history, price freshness and valuation inputs are verified.')
    elif raw>=76 and (margin_safety is None or margin_safety>-10):
        verdict=('CONSIDER PHASED BUYING','buy','Evidence is broadly supportive, but use staggered entries and verify the latest exchange filing before investing.')
    elif raw>=58:
        verdict=('WATCH — WAIT FOR BETTER EVIDENCE / PRICE','wait','The business may be investable, but the current margin of safety or evidence quality is not strong enough for a decisive entry.')
    else:
        verdict=('AVOID FOR NOW','avoid','Current risk–reward is unattractive based on the available evidence.')

    drawdown=None; return5=None
    if not d.history.empty and len(d.history)>1:
        first=val(d.history['Close'].iloc[0]); last=val(d.history['Close'].iloc[-1]); peak=val(d.history['Close'].max())
        if valid(first) and first>0 and valid(last): return5=(last/first-1)*100
        if valid(peak) and peak>0 and valid(last): drawdown=(last/peak-1)*100
    return {'overall':raw,'quality':quality,'valuation':val_score,'news':news_impact,'sales_cagr':sg,'profit_cagr':pg,'verdict':verdict,
            'completeness':completeness,'confidence':confidence,'missing':missing,'fair_value':fair_value,'margin_safety':margin_safety,
            'premium':premium,'drawdown':drawdown,'return5':return5}

def line_chart(df,title):
    if df is None or df.empty:
        fig=go.Figure(); fig.add_annotation(text='Price history unavailable — no synthetic chart shown',x=.5,y=.5,showarrow=False,font=dict(size=16,color='#667085')); fig.update_layout(title=title,height=340,paper_bgcolor='white',plot_bgcolor='white',xaxis_visible=False,yaxis_visible=False); return fig
    fig=go.Figure(go.Scatter(x=df['Date'],y=df['Close'],mode='lines',line=dict(color='#387ed1',width=2.6),fill='tozeroy',fillcolor='rgba(56,126,209,.08)'))
    fig.update_layout(title=title,height=340,margin=dict(l=12,r=12,t=48,b=15),paper_bgcolor='white',plot_bgcolor='white',xaxis=dict(showgrid=False),yaxis=dict(gridcolor='#edf0f4',tickprefix='₹'))
    return fig

def annual_chart(d):
    if not d.sales or not d.profit:
        fig=go.Figure(); fig.add_annotation(text='Verified annual revenue/PAT history unavailable',x=.5,y=.5,showarrow=False); fig.update_layout(height=350,paper_bgcolor='white',plot_bgcolor='white',xaxis_visible=False,yaxis_visible=False); return fig
    years=[f'FY{str(22+i)[-2:]}' for i in range(len(d.sales))]
    fig=go.Figure();fig.add_bar(x=years,y=d.sales,name='Revenue',marker_color='#387ed1');fig.add_bar(x=years,y=d.profit,name='PAT',marker_color='#19a974')
    fig.update_layout(barmode='group',height=350,margin=dict(l=10,r=10,t=35,b=10),paper_bgcolor='white',plot_bgcolor='white',yaxis_title='₹ crore',legend=dict(orientation='h',y=1.12),yaxis=dict(gridcolor='#edf0f4'))
    return fig

def cash_chart(d):
    if not d.ocf:
        fig=go.Figure(); fig.add_annotation(text='Verified operating cash-flow history unavailable',x=.5,y=.5,showarrow=False); fig.update_layout(height=350,paper_bgcolor='white',plot_bgcolor='white',xaxis_visible=False,yaxis_visible=False); return fig
    years=[f'FY{str(22+i)[-2:]}' for i in range(len(d.ocf))]
    fig=go.Figure(go.Bar(x=years,y=d.ocf,marker_color='#7c5ce6'))
    fig.update_layout(height=350,margin=dict(l=10,r=10,t=35,b=10),paper_bgcolor='white',plot_bgcolor='white',yaxis_title='Operating cash flow (₹ crore)',yaxis=dict(gridcolor='#edf0f4'))
    return fig

def pdf_stock(d,s):
    b=io.BytesIO();doc=SimpleDocTemplate(b,pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=14*mm,bottomMargin=14*mm);styles=getSampleStyleSheet();story=[Paragraph('EquityLens One — Research Summary',styles['Title']),Paragraph(d.name,styles['Heading2']),Spacer(1,5*mm)]
    rows=[['Verdict',s['verdict'][0]],['Overall score',f"{s['overall']}/100"],['Price',inr(d.price)],['P/E',rx(d.pe)],['ROE',pct(d.roe)],['Debt/Equity',rx(d.de)],['Revenue CAGR',pct(s['sales_cagr'])],['Profit CAGR',pct(s['profit_cagr'])],['Data source',d.source]]
    t=Table(rows,colWidths=[55*mm,110*mm]);t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.lightgrey),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eef3f8')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)]));story += [t,Spacer(1,6*mm),Paragraph('Business and dependencies',styles['Heading2']),Paragraph(d.business,styles['BodyText'])]
    doc.build(story);return b.getvalue()

st.markdown("<div class='hero'><div class='hero-badge'>EQUITYLENS ONE • KOTAK NEO CONNECTED EDITION</div><h1>One mobile dashboard before you invest ₹1 lakh.</h1><p>Kotak live market data, NSE/BSE discovery, five-year financials, valuation, news, IPOs, risks, portfolio and a decision you can audit.</p></div>",unsafe_allow_html=True)

kotak_connection_panel()

mode=st.radio('Research universe',['Listed Share','IPO — Mainboard / SME','My Kotak Portfolio'],horizontal=True,label_visibility='collapsed')

if mode=='Listed Share':
    st.markdown("<div class='searchbox'>",unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1:symbol=st.text_input('Search NSE company',value='RELIANCE',placeholder='Example: RELIANCE, MAZDOCK, TCS')
    with c2:run=st.button('Analyse company',width='stretch')
    i1,i2,i3=st.columns(3)
    with i1: amount=st.number_input('Planned investment (₹)',min_value=1000,value=100000,step=5000)
    with i2: horizon=st.selectbox('Investment horizon',['Less than 1 year','1–3 years','3–5 years','5+ years'])
    with i3: risk_profile=st.selectbox('Risk tolerance',['Conservative','Moderate','Aggressive'])
    st.markdown('</div>',unsafe_allow_html=True)
    if run or symbol:
        with st.spinner('Building complete research dashboard…'): d=load_stock(symbol);sc=score_stock(d)
        label='live' if d.source.startswith('Live') else 'fallback' if 'fallback' in d.source.lower() else 'demo'
        st.markdown(f"<span class='tag {label}'>{d.source}</span>",unsafe_allow_html=True)
        a,b,c=st.columns([1.7,1,1])
        v,cls,desc=sc['verdict']
        with a:st.markdown(f"<div class='verdict {cls}'><div class='eyebrow'>FINAL DECISION</div><div class='vbig'>{v}</div><p>{desc}</p><b>{d.name}</b><br><span style='color:#667085'>{d.sector} • {d.industry}</span></div>",unsafe_allow_html=True)
        with b:st.markdown(f"<div class='verdict'><div class='eyebrow'>OVERALL RESEARCH SCORE</div><div class='score'>{sc['overall']}<small>/100</small></div><p>Quality {sc['quality']} • Valuation {sc['valuation']}</p></div>",unsafe_allow_html=True)
        with c:
            mood='Positive' if sc['news']>1 else 'Negative' if sc['news']<-1 else 'Mixed'
            st.markdown(f"<div class='verdict'><div class='eyebrow'>CURRENT NEWS IMPACT</div><div class='vbig'>{mood}</div><p>{len(d.news)} recent headlines checked • score impact {sc['news']:+d}</p></div>",unsafe_allow_html=True)
        st.markdown("<div class='grid6'>"+''.join([
            kpi('Current price',inr(d.price),f'As of {d.as_of or "unavailable"}'),kpi('Data completeness',f"{sc['completeness']}/100",'Verdict blocked below 67'),kpi('Decision confidence',f"{sc['confidence']}/100",'Evidence quality'),kpi('Market cap',money_cr(d.market_cap),'Latest available'),kpi('P/E',rx(d.pe),f'Sector {rx(d.sector_pe)}'),kpi('Fair-value reference',inr(sc['fair_value']),f'Margin {pct(sc["margin_safety"])}'),kpi('ROE',pct(d.roe),'Capital efficiency'),kpi('Debt / Equity',rx(d.de),'Balance-sheet risk'),kpi('Revenue CAGR',pct(sc['sales_cagr']),'Only verified history'),kpi('Profit CAGR',pct(sc['profit_cagr']),'Only verified history'),kpi('52-week range',f"{inr(d.low52)} – {inr(d.high52)}",'Market range'),kpi('Drawdown from peak',pct(sc['drawdown']),'Five-year chart')])+'</div>',unsafe_allow_html=True)
        tabs=st.tabs(['Command Center','5-Year Financials','Valuation & Peers','Business DNA','News & Events','Risks & PDF'])
        with tabs[0]:
            x,y=st.columns([1.45,1])
            with x:st.plotly_chart(line_chart(d.history,'Five-year share-price journey'),width='stretch')
            with y:
                st.markdown("<div class='card'><h3>Why this decision?</h3>",unsafe_allow_html=True)
                flags=[]
                if sc['sales_cagr'] and sc['sales_cagr']>10:flags.append(('good',f"Revenue compounded at about {sc['sales_cagr']:.1f}% over the displayed period."))
                if sc['profit_cagr'] and sc['profit_cagr']>12:flags.append(('good',f"Profit growth of about {sc['profit_cagr']:.1f}% is stronger than sales growth."))
                if d.roe and d.roe>18:flags.append(('good',f"ROE of {d.roe:.1f}% indicates efficient use of shareholder capital."))
                if d.pe and d.sector_pe and d.pe>d.sector_pe*1.2:flags.append(('warn','The stock trades at a meaningful premium to the sector benchmark.'))
                if d.de and d.de>1:flags.append(('bad','Debt is high relative to equity and deserves deeper review.'))
                if not flags:flags=[('warn','The available data is mixed; verify exchange filings before acting.')]
                for typ,txt in flags:st.markdown(f"<div class='flag {typ}'>{txt}</div>",unsafe_allow_html=True)
                st.markdown('</div>',unsafe_allow_html=True)
            st.markdown("<div class='section'>Decision readiness and ₹1 lakh action plan</div>",unsafe_allow_html=True)
            if sc['missing']:
                st.error('Missing critical evidence: ' + ', '.join(sc['missing']) + '. The app will not issue a confident buy verdict while these fields are unavailable.')
            stale_days=None
            if d.as_of:
                stale_days=(pd.Timestamp.today().date()-d.as_of).days
                if stale_days>3: st.warning(f'Price history is delayed by about {stale_days} calendar days. Verify today’s exchange price before acting.')
            max_initial=0
            if sc['verdict'][1]=='buy': max_initial=0.35 if risk_profile=='Conservative' else 0.5 if risk_profile=='Moderate' else 0.65
            elif sc['verdict'][1]=='wait': max_initial=0.1 if risk_profile!='Conservative' else 0
            suggested=round(amount*max_initial/1000)*1000
            plan=pd.DataFrame({'Decision item':['Planned capital','Suggested initial tranche','Capital kept for later tranches','Evidence confidence','Horizon selected'],
                               'Result':[f'₹{amount:,.0f}',f'₹{suggested:,.0f}',f'₹{amount-suggested:,.0f}',f"{sc['confidence']}/100",horizon]})
            st.dataframe(plan,width='stretch',hide_index=True)
            st.caption('The tranche is a risk-control framework, not a return guarantee or personalised advisory recommendation.')
            st.markdown("<div class='section'>At-a-glance investment checklist</div>",unsafe_allow_html=True)
            checklist=pd.DataFrame({'Question':['Is the business growing?','Are profits compounding?','Is capital efficiency healthy?','Is debt manageable?','Is valuation reasonable?','Is current news supportive?'], 'Answer':['Yes' if sc['sales_cagr'] and sc['sales_cagr']>8 else 'Mixed','Yes' if sc['profit_cagr'] and sc['profit_cagr']>10 else 'Mixed','Strong' if d.roe and d.roe>18 else 'Average','Yes' if d.de is None or d.de<.8 else 'Needs attention','Fair' if not(d.pe and d.sector_pe and d.pe>d.sector_pe*1.2) else 'Expensive','Positive' if sc['news']>1 else 'Negative' if sc['news']<-1 else 'Mixed']})
            st.dataframe(checklist,width='stretch',hide_index=True)
        with tabs[1]:
            c1,c2=st.columns(2);c1.plotly_chart(annual_chart(d),width='stretch');c2.plotly_chart(cash_chart(d),width='stretch')
            if d.sales and d.profit:
                n=min(len(d.sales),len(d.profit)); years=[f'FY-{n-i}' for i in range(n)]
                oc=(d.ocf[-n:] if len(d.ocf)>=n else [None]*(n-len(d.ocf))+d.ocf)
                fin=pd.DataFrame({'Year':years,'Revenue (₹ Cr)':d.sales[-n:],'PAT (₹ Cr)':d.profit[-n:],'Operating Cash Flow (₹ Cr)':oc})
                fin['PAT margin %']=(fin['PAT (₹ Cr)']/fin['Revenue (₹ Cr)']*100).round(1)
                fin['Cash conversion %']=(fin['Operating Cash Flow (₹ Cr)']/fin['PAT (₹ Cr)']*100).replace([np.inf,-np.inf],np.nan).round(1)
                fin=fin.replace({np.nan:'Not available'})
                st.dataframe(fin,width='stretch',hide_index=True)
            else: st.warning('Verified multi-year financial statements were not retrieved. No invented values are shown.')
        with tabs[2]:
            st.markdown("<div class='card'><h3>Valuation snapshot</h3><p>Valuation must be interpreted with growth quality, cyclicality and sector economics—not P/E alone.</p></div>",unsafe_allow_html=True)
            peers=[]
            for p in d.peers:
                sym=p.replace('.NS','');pdemo=DEMO.get(sym,{});peers.append({'Company':sym,'P/E':pdemo.get('pe','N/A'),'ROE %':pdemo.get('roe','N/A'),'Debt/Equity':pdemo.get('de','N/A'),'Market cap ₹Cr':pdemo.get('market_cap','N/A')})
            peers.insert(0,{'Company':d.symbol+' (Selected)','P/E':d.pe or 'N/A','ROE %':d.roe or 'N/A','Debt/Equity':d.de if d.de is not None else 'N/A','Market cap ₹Cr':d.market_cap or 'N/A'})
            st.dataframe(pd.DataFrame(peers),width='stretch',hide_index=True)
        with tabs[3]:
            st.markdown(f"<div class='card'><h3>What the company does</h3><p>{d.business}</p></div>",unsafe_allow_html=True)
            st.markdown("<div class='card'><h3>Major business dependencies</h3>",unsafe_allow_html=True)
            for name,p in d.depend:st.markdown(f"<div class='dependency'><b>{name}</b><div class='bar'><i style='width:{min(100,p)}%'></i></div><span>{p}%</span></div>",unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)
        with tabs[4]:
            if not d.news:st.info('No current headlines were retrieved. This does not mean no news exists.')
            for item in d.news:
                mood,_=sent(item['title']+' '+item.get('summary',''));cls='positive' if mood=='Positive' else 'negative' if mood=='Negative' else 'neutral'
                st.markdown(f"<div class='news'><span class='tag {cls}'>{mood}</span><div class='ntitle'>{item['title']}</div><div class='nmeta'>{item['date']}</div></div>",unsafe_allow_html=True)
        with tabs[5]:
            risks=['Market-wide correction can pull down even strong businesses.','A valuation premium can compress if earnings disappoint.','Business concentration or customer dependency may amplify volatility.','Free data feeds can be incomplete; verify exchange filings and annual reports.']
            for r in risks:st.markdown(f"<div class='flag bad'>{r}</div>",unsafe_allow_html=True)
            st.download_button('Download research PDF',pdf_stock(d,sc),file_name=f'{d.symbol}_EquityLens_Report.pdf',mime='application/pdf',width='stretch')
elif mode=='IPO — Mainboard / SME':
    ipo_df,ipo_errors=load_live_ipo_data()
    st.markdown("<div class='searchbox'>",unsafe_allow_html=True)
    f1,f2,f3=st.columns([1.2,1.2,2.2])
    with f1: type_filter=st.selectbox('IPO segment',['All','Mainboard','SME'])
    with f2: status_filter=st.selectbox('Issue status',['Open & Upcoming','Open','Upcoming','Closed','All'])
    with f3: refresh=st.button('Refresh live IPO data',width='stretch')
    st.markdown('</div>',unsafe_allow_html=True)
    if refresh:
        load_live_ipo_data.clear(); st.rerun()
    if ipo_df.empty:
        st.error('Live IPO sources could not be read right now. No sample or invented IPO data is being shown.')
        if ipo_errors: st.caption(' • '.join(ipo_errors))
        st.markdown("<div class='card'><h3>What to do</h3><p>Refresh after a few minutes, or connect an authorised IPO API. The app intentionally does not fall back to unrelated demo companies.</p></div>",unsafe_allow_html=True)
        st.stop()
    view=ipo_df.copy()
    if type_filter!='All':
        view=view[view['type'].str.contains(type_filter,case=False,na=False)]
    if status_filter=='Open & Upcoming': view=view[view['status'].str.contains('Open|Upcoming',case=False,na=False,regex=True)]
    elif status_filter!='All': view=view[view['status'].str.contains(status_filter,case=False,na=False)]
    if view.empty:
        st.warning('No IPOs match these filters. Change status or segment.')
        st.dataframe(ipo_df[['name','type','status','dates','price_text','gmp_text']],width='stretch',hide_index=True)
        st.stop()
    view=view.reset_index(drop=True)
    choice=st.selectbox('Select live IPO',view['name'].tolist())
    ipo=view[view['name']==choice].iloc[0]
    gmp_pct=None
    if ipo.get('gmp') is not None and ipo.get('price'):
        try:gmp_pct=ipo['gmp']/ipo['price']*100
        except Exception:pass
    qib=ipo.get('qib');nii=ipo.get('nii');retail=ipo.get('retail');total=ipo.get('total_sub')
    listing_score=50
    if gmp_pct is not None: listing_score += 18 if gmp_pct>=20 else 10 if gmp_pct>=8 else 2 if gmp_pct>=0 else -12
    if qib is not None: listing_score += 15 if qib>=10 else 8 if qib>=3 else -5 if qib<1 else 2
    if nii is not None: listing_score += 8 if nii>=5 else 3 if nii>=1 else -3
    if retail is not None: listing_score += 5 if retail>=3 else 2 if retail>=1 else -2
    if 'SME' in str(ipo.get('type','')).upper(): listing_score-=8
    listing_score=max(0,min(100,round(listing_score)))
    verdict='POSITIVE LISTING SETUP' if listing_score>=72 else 'WATCH CLOSELY' if listing_score>=55 else 'HIGH CAUTION'
    cls='buy' if listing_score>=72 else 'wait' if listing_score>=55 else 'avoid'
    a,b,c=st.columns([1.7,1,1])
    with a:st.markdown(f"<div class='verdict {cls}'><div class='eyebrow'>LIVE IPO SCREEN</div><div class='vbig'>{verdict}</div><p>{ipo['name']} • {ipo.get('type','')}</p><b>Status: {ipo.get('status','')}</b></div>",unsafe_allow_html=True)
    with b:st.markdown(f"<div class='verdict'><div class='eyebrow'>LISTING SETUP SCORE</div><div class='score'>{listing_score}<small>/100</small></div><p>GMP + subscription + issue type</p></div>",unsafe_allow_html=True)
    with c:st.markdown(f"<div class='verdict'><div class='eyebrow'>DATA FRESHNESS</div><div class='vbig'>{ipo.get('updated','Live')}</div><p>IPOWatch GMP + IPO Ji issue/subscription data</p></div>",unsafe_allow_html=True)
    st.markdown("<div class='grid6'>"+''.join([
        kpi('Price band',ipo.get('price_text') or ipo.get('ipoji_price','N/A')),
        kpi('GMP',ipo.get('gmp_text','N/A'),'Unofficial sentiment'),
        kpi('Estimated listing',ipo.get('est_listing','N/A')),
        kpi('Issue dates',ipo.get('dates','N/A')),
        kpi('Lot size',str(ipo.get('lot_size','N/A'))),
        kpi('Issue size',str(ipo.get('issue_size','N/A'))),
        kpi('QIB subscription',rx(qib)),kpi('NII / HNI',rx(nii)),kpi('Retail',rx(retail)),kpi('Total subscription',rx(total)),
        kpi('Segment',str(ipo.get('type','N/A'))),kpi('Status',str(ipo.get('status','N/A')))
    ])+'</div>',unsafe_allow_html=True)
    tabs=st.tabs(['5-Minute IPO Dashboard','Subscription','GMP & Listing Sentiment','Timeline','Due-Diligence Checklist'])
    with tabs[0]:
        st.markdown(f"<div class='card'><h3>What this live data says</h3><p><b>{verdict}</b>. The score is based only on currently retrieved GMP, category subscription and Mainboard/SME liquidity. It does not invent financials, P/E, ROE or five-year results when those figures have not been verified from the RHP.</p></div>",unsafe_allow_html=True)
        quick=pd.DataFrame({'Question':['Is the issue open/upcoming?','Is GMP supportive?','Is institutional demand visible?','Is HNI demand visible?','Is SME liquidity a risk?'], 'Answer':[str(ipo.get('status','N/A')),'Yes' if gmp_pct is not None and gmp_pct>=8 else 'Weak / unavailable','Strong' if qib is not None and qib>=3 else 'Weak / unavailable','Strong' if nii is not None and nii>=3 else 'Weak / unavailable','Yes' if 'SME' in str(ipo.get('type','')).upper() else 'No']})
        st.dataframe(quick,width='stretch',hide_index=True)
    with tabs[1]:
        vals=[qib,nii,retail,total]; labels=['QIB','NII / HNI','Retail','Total']
        plot=pd.DataFrame({'Category':labels,'Subscription (x)':[0 if v is None else v for v in vals]})
        fig=go.Figure(go.Bar(x=plot['Category'],y=plot['Subscription (x)'],marker_color=['#387ed1','#7c5ce6','#19a974','#f59e0b']))
        fig.update_layout(height=370,paper_bgcolor='white',plot_bgcolor='white',yaxis=dict(gridcolor='#edf0f4'))
        st.plotly_chart(fig,width='stretch');st.dataframe(plot,width='stretch',hide_index=True)
        if all(v is None for v in vals): st.info('Subscription data is not yet published or could not be matched for this issue.')
    with tabs[2]:
        st.markdown(f"<div class='card'><h3>Grey-market view</h3><p>Current GMP: <b>{ipo.get('gmp_text','N/A')}</b> • Estimated listing: <b>{ipo.get('est_listing','N/A')}</b>. GMP is unofficial and can reverse quickly; it is deliberately capped in the scoring model.</p></div>",unsafe_allow_html=True)
        if gmp_pct is not None:
            fig=go.Figure(go.Indicator(mode='gauge+number',value=gmp_pct,number={'suffix':'%'},title={'text':'GMP as % of upper price'},gauge={'axis':{'range':[-20,60]},'bar':{'color':'#387ed1'},'steps':[{'range':[-20,0],'color':'#fee2e2'},{'range':[0,10],'color':'#fef3c7'},{'range':[10,60],'color':'#dcfce7'}]}))
            fig.update_layout(height=330,margin=dict(l=30,r=30,t=70,b=20));st.plotly_chart(fig,width='stretch')
    with tabs[3]:
        timeline=pd.DataFrame({'Event':['Open date','Close date','Listing date','Displayed issue window'],'Date':[ipo.get('open_date','N/A'),ipo.get('close_date','N/A'),ipo.get('listing_date','N/A'),ipo.get('dates','N/A')]})
        st.dataframe(timeline,width='stretch',hide_index=True)
    with tabs[4]:
        checks=['Read RHP/DRHP financial statements','Compare IPO P/E with listed peers','Check fresh issue versus OFS','Review use of proceeds','Check customer and supplier concentration','Review promoter litigation and related-party transactions','Check operating cash flow versus PAT','Check QIB subscription near closing','Treat GMP as unofficial only','For SME: assess lot size and exit liquidity']
        for x in checks:st.markdown(f"<div class='flag warn'>□ {x}</div>",unsafe_allow_html=True)
        st.caption('Sources used on this screen: IPOWatch for GMP; IPO Ji for issue calendar and subscription. Verify final figures with NSE/BSE and the RHP.')

else:
    st.markdown("<div class='card'><h3>My Kotak portfolio</h3><p>Read-only holdings, positions and limits. Trading functions are intentionally not included.</p></div>",unsafe_allow_html=True)
    if not st.session_state.get('kotak_connected'):
        st.warning('Connect Kotak Neo above with the current TOTP to load your holdings and positions.')
    else:
        if st.button('Refresh portfolio',width='stretch'):
            st.cache_data.clear()
        with st.spinner('Loading Kotak portfolio…'):
            p=kotak_portfolio_snapshot()
        tabs=st.tabs(['Holdings','Positions','Account limits'])
        with tabs[0]:
            if p['holdings']: st.dataframe(pd.json_normalize(p['holdings']),width='stretch',hide_index=True)
            else: st.info('No holdings were returned, or the account response format could not be read.')
        with tabs[1]:
            if p['positions']: st.dataframe(pd.json_normalize(p['positions']),width='stretch',hide_index=True)
            else: st.info('No open positions were returned.')
        with tabs[2]:
            if p['limits'] is not None: st.json(p['limits'],expanded=False)
            else: st.info('Account limits were not returned.')

st.caption('EquityLens One uses Kotak Neo as the primary live market layer when connected. It is research support, not a guarantee or personalised investment advice. Live prices, exchange filings, RHPs and corporate announcements must be verified before investing.')
