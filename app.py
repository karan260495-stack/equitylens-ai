import io
import math
import os
import re
import textwrap
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

st.set_page_config(
    page_title="EquityLens AI | IPO & Stock Research",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Styling ----------
st.markdown("""
<style>
:root { --ink:#111827; --muted:#5f6b7a; --brand:#6d28d9; --soft:#f7f5ff; --green:#087f5b; --amber:#b45309; --red:#b42318; }
html, body, [class*="css"] {font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;}
.stApp {background:#f8fafc; color:#111827;}
.block-container {padding-top: .8rem; padding-bottom: 3rem; max-width: 1180px;}
.hero {padding:22px; border-radius:22px; background:linear-gradient(135deg,#24153f,#6d28d9); color:#fff; margin-bottom:18px; box-shadow:0 12px 30px rgba(76,29,149,.18)}
.hero h1 {margin:0; font-size:2rem; color:#fff!important}.hero p{margin:.45rem 0 0;opacity:.9;color:#fff!important}
[data-testid="stMetric"] {background:#fff!important; border:1px solid #e5e7eb; border-radius:15px; padding:14px; box-shadow:0 3px 14px rgba(15,23,42,.05)}
[data-testid="stMetric"] * {color:#111827!important}
[data-testid="stMetricDelta"] * {color:#087f5b!important}
[data-testid="stDataFrame"], [data-testid="stTable"] {background:#fff;border-radius:14px;overflow:hidden}
[data-testid="stTabs"] button {font-weight:750;color:#374151!important}
[data-testid="stTabs"] button[aria-selected="true"] {color:#6d28d9!important}
.card {background:#fff; color:#111827; border:1px solid #e5e7eb; border-radius:16px; padding:18px; margin:10px 0; box-shadow:0 3px 14px rgba(15,23,42,.04)}
.decision {background:#fff;border:1px solid #e5e7eb;border-radius:20px;padding:22px;margin:14px 0;box-shadow:0 8px 25px rgba(15,23,42,.07)}
.decision h2{margin:0 0 6px;color:#111827!important}.decision p{color:#374151!important;margin:.3rem 0}
.action-buy{border-left:8px solid #10b981}.action-wait{border-left:8px solid #f59e0b}.action-avoid{border-left:8px solid #ef4444}
.action-badge{display:inline-block;border-radius:999px;padding:7px 12px;font-weight:800;margin-bottom:10px}
.badge-buy{background:#d1fae5;color:#065f46}.badge-wait{background:#fef3c7;color:#92400e}.badge-avoid{background:#fee2e2;color:#991b1b}
.step-title{font-size:1.1rem;font-weight:800;color:#111827;margin-top:18px;margin-bottom:6px}
.check-good,.check-warn,.check-bad{padding:11px 13px;border-radius:12px;margin:7px 0;color:#111827!important}
.check-good{background:#ecfdf5;border:1px solid #a7f3d0}.check-warn{background:#fffbeb;border:1px solid #fde68a}.check-bad{background:#fef2f2;border:1px solid #fecaca}
.verdict-good {background:#ecfdf5;color:#111827!important;border-left:6px solid #10b981;padding:18px;border-radius:14px}
.verdict-warn {background:#fffbeb;color:#111827!important;border-left:6px solid #f59e0b;padding:18px;border-radius:14px}
.verdict-bad {background:#fef2f2;color:#111827!important;border-left:6px solid #ef4444;padding:18px;border-radius:14px}
.small {font-size:.86rem;color:#64748b}.pill{display:inline-block;padding:5px 10px;border-radius:999px;background:#f1f5f9;margin-right:6px;font-size:.8rem}
.stAlert * {color:#111827!important}
@media (prefers-color-scheme: dark){
  .stApp{background:#111318;color:#f9fafb}.card,.decision,[data-testid="stMetric"]{background:#1c2028!important;border-color:#303743}.decision h2,.decision p,.step-title,[data-testid="stMetric"] *{color:#f9fafb!important}
  [data-testid="stTabs"] button{color:#d1d5db!important}.check-good,.check-warn,.check-bad,.verdict-good,.verdict-warn,.verdict-bad{color:#111827!important}
}
@media (max-width:700px){.hero{padding:17px}.hero h1{font-size:1.5rem}.block-container{padding-left:.7rem;padding-right:.7rem}.decision{padding:17px}}
</style>
""", unsafe_allow_html=True)

NSE_HOME = "https://www.nseindia.com"
NSE_CURRENT = "https://www.nseindia.com/api/ipo-current-issue"
NSE_UPCOMING = "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": NSE_UPCOMING,
}

# ---------- Helpers ----------
def fnum(v, default=0.0):
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        if isinstance(v, (int, float, np.number)):
            return float(v)
        s = re.sub(r"[^0-9.\-]", "", str(v).replace(",", ""))
        return float(s) if s else default
    except Exception:
        return default

def pct(v):
    return "—" if v is None else f"{v:.1f}%"

def money(v, cr=False):
    if v is None or not np.isfinite(v): return "—"
    if cr: return f"₹{v:,.0f} Cr"
    return f"₹{v:,.2f}"

def safe_div(a,b,default=0):
    return a/b if b not in (0,None) else default

def cagr(start,end,years):
    if start and end and start>0 and end>0 and years>0:
        return ((end/start)**(1/years)-1)*100
    return 0.0

def score_label(s):
    if s >= 80: return "Excellent"
    if s >= 65: return "Good"
    if s >= 50: return "Average"
    if s >= 35: return "Weak"
    return "High Risk"

def verdict_class(s):
    return "verdict-good" if s>=65 else "verdict-warn" if s>=48 else "verdict-bad"


def stock_action(d):
    score=d.get('overall',0); val=d.get('scores',{}).get('Valuation',50); risk_count=len(d.get('risks',[]))
    if score>=72 and val>=48 and risk_count<=3:
        return ('CONSIDER BUYING GRADUALLY','buy','Fundamentals look supportive, but buy in parts rather than committing everything at one price.')
    if score>=58:
        return ('WATCH / BUY ONLY AT A BETTER PRICE','wait','The business has positives, but valuation or risk does not give a strong margin of safety yet.')
    return ('AVOID FOR NOW','avoid','The current combination of fundamentals, valuation and risk is not strong enough for a fresh investment.')

def ipo_action(d, segment):
    if d['listing']>=72 and d['overall']>=65:
        return ('APPLY SELECTIVELY FOR LISTING','buy','The issue setup is favourable, but listing profit is never guaranteed and allotment may be low.')
    if d['listing']>=55 or d['overall']>=55:
        return ('WAIT FOR FINAL SUBSCRIPTION / APPLY CAUTIOUSLY','wait','The IPO is mixed. Final QIB demand, valuation and market mood should decide the application.')
    return ('SKIP / AVOID','avoid','The current issue quality and listing setup do not justify the risk.')

def decision_html(action, tone, reason, score, second_label, second_value):
    return f"""<div class='decision action-{tone}'><span class='action-badge badge-{tone}'>{action}</span><h2>Should you invest?</h2><p><b>My structured view:</b> {reason}</p><p><b>Overall score:</b> {score}/100 &nbsp; • &nbsp; <b>{second_label}:</b> {second_value}</p><p class='small'>This is decision support, not a guarantee. Verify exchange filings and current price before investing.</p></div>"""

def explain_pe(pe, industry_pe=0):
    if pe <= 0: return "P/E is unavailable or earnings are negative, so valuation needs other methods."
    base = f"You are paying about ₹{pe:.1f} for every ₹1 of annual earnings."
    if industry_pe > 0:
        premium=(pe/industry_pe-1)*100
        if premium > 30: return base+f" That is about {premium:.0f}% above the industry level, so growth expectations are demanding."
        if premium < -15: return base+f" That is about {abs(premium):.0f}% below the industry level, which may be attractive or may signal business concerns."
        return base+" It is broadly near the industry valuation."
    return base

def gauge(title, value, max_value=100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=float(value), title={'text':title},
        gauge={'axis':{'range':[0,max_value]}, 'bar':{'color':'#7c3aed'},
               'steps':[{'range':[0,max_value*.4],'color':'#fee2e2'},
                        {'range':[max_value*.4,max_value*.65],'color':'#fef3c7'},
                        {'range':[max_value*.65,max_value],'color':'#d1fae5'}]}
    ))
    fig.update_layout(height=250, margin=dict(l=20,r=20,t=55,b=10))
    return fig

# ---------- IPO discovery ----------
@st.cache_data(ttl=900, show_spinner=False)
def fetch_nse_ipos():
    session=requests.Session(); session.headers.update(HEADERS)
    try:
        session.get(NSE_HOME,timeout=12)
        r=session.get(NSE_CURRENT,timeout=20); r.raise_for_status()
        payload=r.json(); rows=payload.get('data',payload) if isinstance(payload,dict) else payload
        df=pd.DataFrame(rows)
        if not df.empty:
            aliases={
                'company':['companyName','company','issuerCompanyName','symbol'],
                'symbol':['symbol','issueSymbol'], 'segment':['securityType','issueType','series'],
                'open_date':['issueStartDate','openDate','biddingStartDate'],
                'close_date':['issueEndDate','closeDate','biddingEndDate'],
                'status':['status','issueStatus'], 'price_band':['issuePrice','priceBand','floorPrice'],
                'subscription_x':['noOfTime','subscription','timesSubscribed']}
            out=pd.DataFrame(index=df.index)
            for k,opts in aliases.items():
                col=next((c for c in opts if c in df.columns),None); out[k]=df[col] if col else ''
            out['company']=out['company'].fillna(out['symbol']).astype(str)
            raw=out['segment'].astype(str).str.upper()
            out['segment']=np.where(raw.str.contains('SME|EMERGE',na=False),'SME','MAINBOARD')
            return out.drop_duplicates('company')
    except Exception:
        pass
    return pd.DataFrame()

DEMO_IPOS = pd.DataFrame([
    {'company':'Demo Consumer Technologies Ltd','symbol':'DEMOIPO','segment':'MAINBOARD','open_date':'Demo','close_date':'Demo','status':'Sample report','price_band':'₹310–₹326','subscription_x':'18.4'},
    {'company':'Demo Precision SME Ltd','symbol':'DEMOSME','segment':'SME','open_date':'Demo','close_date':'Demo','status':'Sample report','price_band':'₹88–₹92','subscription_x':'44.1'},
])

# ---------- Listed stock data ----------
@st.cache_data(ttl=1200, show_spinner=False)
def load_stock(symbol: str) -> Tuple[Dict, pd.DataFrame, Dict[str,pd.DataFrame]]:
    symbol=symbol.strip().upper()
    if not symbol.endswith(('.NS','.BO')): symbol += '.NS'
    t=yf.Ticker(symbol)
    info={}
    try: info=t.get_info()
    except Exception:
        try: info=t.info
        except Exception: info={}
    try: hist=t.history(period='5y',auto_adjust=False)
    except Exception: hist=pd.DataFrame()
    stmts={}
    for name,attr in [('income','financials'),('balance','balance_sheet'),('cashflow','cashflow')]:
        try: stmts[name]=getattr(t,attr)
        except Exception: stmts[name]=pd.DataFrame()
    return info,hist,stmts

def row_values(df:pd.DataFrame, candidates:List[str], n=4):
    if df is None or df.empty: return []
    idx=next((x for x in candidates if x in df.index),None)
    if idx is None: return []
    vals=[]
    for v in df.loc[idx].iloc[:n].tolist()[::-1]:
        vals.append(fnum(v)/1e7)  # INR crore
    return vals

def analyze_stock(symbol, info, hist, stmts):
    price=fnum(info.get('currentPrice') or info.get('regularMarketPrice'))
    marketcap=fnum(info.get('marketCap'))/1e7
    pe=fnum(info.get('trailingPE')); forward_pe=fnum(info.get('forwardPE'))
    pb=fnum(info.get('priceToBook')); book=fnum(info.get('bookValue')); eps=fnum(info.get('trailingEps'))
    roe=fnum(info.get('returnOnEquity'))*100; roa=fnum(info.get('returnOnAssets'))*100
    debt_equity=fnum(info.get('debtToEquity'))/100
    margin=fnum(info.get('profitMargins'))*100; opmargin=fnum(info.get('operatingMargins'))*100
    rev_growth=fnum(info.get('revenueGrowth'))*100; earn_growth=fnum(info.get('earningsGrowth'))*100
    dividend=fnum(info.get('dividendYield'))*100
    beta=fnum(info.get('beta'))
    revenues=row_values(stmts.get('income'),['Total Revenue','Operating Revenue'])
    profits=row_values(stmts.get('income'),['Net Income','Net Income Common Stockholders'])
    ocf=row_values(stmts.get('cashflow'),['Operating Cash Flow','Total Cash From Operating Activities'])
    debt=row_values(stmts.get('balance'),['Total Debt'])
    years=[]
    inc=stmts.get('income')
    if inc is not None and not inc.empty: years=[str(x.year) for x in inc.columns[:4]][::-1]
    if not years: years=[str(date.today().year-i) for i in [3,2,1,0]]
    rev_cagr=cagr(revenues[0],revenues[-1],len(revenues)-1) if len(revenues)>1 else rev_growth
    pat_cagr=cagr(abs(profits[0]),abs(profits[-1]),len(profits)-1) if len(profits)>1 and profits[0]*profits[-1]>0 else earn_growth
    cash_quality=safe_div(ocf[-1],profits[-1],0)*100 if ocf and profits and profits[-1]!=0 else 0

    scores={}
    scores['Growth']=max(0,min(100,50+rev_cagr*1.2+pat_cagr*.8))
    scores['Profitability']=max(0,min(100,35+roe*1.5+margin*.8))
    scores['Balance Sheet']=max(0,min(100,85-debt_equity*30))
    val=65
    if pe>0: val-=max(0,pe-25)*1.2; val+=max(0,18-pe)*1.2
    if pb>0: val-=max(0,pb-4)*3
    scores['Valuation']=max(0,min(100,val))
    scores['Cash Quality']=max(0,min(100,cash_quality if cash_quality else 45))
    scores['Market Quality']=max(0,min(100,60 + (10 if marketcap>50000 else 0) - max(0,beta-1.2)*15))
    overall=round(sum(scores.values())/len(scores))
    risks=[]; positives=[]
    if rev_cagr>12: positives.append(f"Revenue has grown at roughly {rev_cagr:.1f}% CAGR across available annual data.")
    elif rev_cagr<5: risks.append("Revenue growth is slow or inconsistent.")
    if pat_cagr>15: positives.append(f"Profit growth is strong at roughly {pat_cagr:.1f}% CAGR.")
    elif pat_cagr<0: risks.append("Profit has declined across the available period.")
    if roe>18: positives.append(f"ROE of about {roe:.1f}% indicates efficient use of shareholder capital.")
    elif roe and roe<10: risks.append(f"ROE of about {roe:.1f}% is weak.")
    if debt_equity<0.5: positives.append("Balance-sheet leverage appears manageable.")
    elif debt_equity>1.5: risks.append("Debt is high relative to equity and increases downside risk.")
    if cash_quality>80: positives.append("Operating cash flow broadly supports reported profit.")
    elif cash_quality and cash_quality<50: risks.append("Reported profit is not converting well into operating cash flow.")
    if pe>40: risks.append("The stock trades at a demanding earnings multiple.")
    if beta>1.4: risks.append("The share has historically shown above-market volatility.")
    target=fnum(info.get('targetMeanPrice'))
    upside=(target/price-1)*100 if target and price else None
    return {
        'symbol':symbol.upper(), 'name':info.get('longName') or info.get('shortName') or symbol,
        'sector':info.get('sector','—'), 'industry':info.get('industry','—'), 'summary':info.get('longBusinessSummary',''),
        'website':info.get('website',''), 'employees':info.get('fullTimeEmployees'),
        'price':price,'marketcap':marketcap,'pe':pe,'forward_pe':forward_pe,'pb':pb,'book':book,'eps':eps,
        'roe':roe,'roa':roa,'debt_equity':debt_equity,'margin':margin,'opmargin':opmargin,
        'revenue_growth':rev_growth,'earnings_growth':earn_growth,'dividend':dividend,'beta':beta,
        '52high':fnum(info.get('fiftyTwoWeekHigh')),'52low':fnum(info.get('fiftyTwoWeekLow')),
        'target':target,'upside':upside,'scores':scores,'overall':overall,'positives':positives,'risks':risks,
        'years':years[-len(revenues):] if revenues else years,'revenues':revenues,'profits':profits,'ocf':ocf,'debt':debt,
        'rev_cagr':rev_cagr,'pat_cagr':pat_cagr,'cash_quality':cash_quality,
    }

# ---------- IPO scoring ----------
def analyze_ipo(m):
    segment=m['segment']; score=50; positives=[]; risks=[]
    def add(points,text):
        nonlocal score; score+=points; (positives if points>0 else risks).append(text)
    if m['sales_cagr']>=20:add(8,'Strong revenue growth')
    elif m['sales_cagr']>=10:add(4,'Healthy revenue growth')
    elif m['sales_cagr']<0:add(-8,'Revenue is shrinking')
    if m['pat_cagr']>=25:add(10,'Strong profit growth')
    elif m['pat_cagr']>=10:add(5,'Healthy profit growth')
    elif m['pat_cagr']<0:add(-12,'Profit is declining')
    if m['roe']>=18:add(7,'Strong ROE')
    elif m['roe']<10:add(-5,'Weak ROE')
    if m['roce']>=18:add(7,'Strong ROCE')
    elif m['roce']<10:add(-5,'Weak ROCE')
    if m['de']<=.3:add(6,'Low leverage')
    elif m['de']>(1.5 if segment=='SME' else 1):add(-10,'High leverage')
    if m['pe'] and m['peer_pe']:
        prem=(m['pe']/m['peer_pe']-1)*100
        if prem<=-15:add(8,'Priced below peer P/E')
        elif prem<=10:add(4,'P/E broadly reasonable')
        elif prem>=40:add(-12,'Very expensive versus peers')
        elif prem>=20:add(-7,'Meaningful premium versus peers')
    if m['pb']>=8:add(-5,'Demanding price-to-book')
    if m['ofs']>=70:add(-8,'Issue is largely an OFS exit')
    elif m['fresh']>=60:add(5,'Most proceeds fund the company')
    if m['cash_quality']>=80:add(6,'Cash flow supports profit')
    elif m['cash_quality']<40:add(-8,'Weak cash conversion')
    if m['qib']>=10:add(7,'Strong QIB demand')
    elif 0<m['qib']<1:add(-7,'Weak QIB demand')
    if m['nii']>=10:add(4,'Strong HNI demand')
    if m['retail']>=5:add(3,'Healthy retail demand')
    if m['gmp']>=20:add(5,'Positive unofficial GMP sentiment')
    elif m['gmp']<0:add(-4,'Negative unofficial GMP sentiment')
    if segment=='SME':add(-6,'SME liquidity and exit risk')
    overall=max(0,min(100,round(score)))
    listing=max(0,min(100,round(35+min(m['qib'],25)*1.2+min(m['nii'],25)*.5+min(m['retail'],15)*.3+max(-10,min(m['gmp'],35))*.7-(8 if segment=='SME' else 0))))
    longterm=max(0,min(100,round(overall-min(max(m['gmp'],0),20)*.15)))
    return {'overall':overall,'listing':listing,'longterm':longterm,'positives':positives,'risks':risks}

# ---------- PDF ----------
def build_pdf(title, kind, data, dependency_text, bull, bear):
    bio=io.BytesIO(); doc=SimpleDocTemplate(bio,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=14*mm,bottomMargin=14*mm)
    ss=getSampleStyleSheet(); styles={
        'title':ParagraphStyle('title',parent=ss['Title'],fontSize=22,leading=26,textColor=colors.HexColor('#4c1d95'),alignment=TA_CENTER),
        'h':ParagraphStyle('h',parent=ss['Heading2'],fontSize=14,leading=18,textColor=colors.HexColor('#4c1d95'),spaceBefore=8,spaceAfter=5),
        'body':ParagraphStyle('body',parent=ss['BodyText'],fontSize=9.5,leading=14,textColor=colors.HexColor('#253047')),
        'small':ParagraphStyle('small',parent=ss['BodyText'],fontSize=8,leading=11,textColor=colors.HexColor('#64748b'))}
    story=[Paragraph('EquityLens AI Research Report',styles['title']),Spacer(1,5),Paragraph(title,ss['Heading1']),Paragraph(f"{kind} • Generated {datetime.now().strftime('%d %b %Y, %I:%M %p')}",styles['small']),Spacer(1,10)]
    if kind=='Listed Share':
        summary=[['Overall Score',f"{data['overall']}/100"],['Current Price',money(data['price'])],['Market Cap',money(data['marketcap'],True)],['P/E',f"{data['pe']:.1f}x" if data['pe'] else '—'],['P/B',f"{data['pb']:.1f}x" if data['pb'] else '—'],['ROE',pct(data['roe'])],['Debt/Equity',f"{data['debt_equity']:.2f}"],['5Y/available Revenue CAGR',pct(data['rev_cagr'])],['5Y/available Profit CAGR',pct(data['pat_cagr'])]]
    else:
        summary=[['Overall IPO Score',f"{data['overall']}/100"],['Listing Setup',f"{data['listing']}/100"],['Long-term Quality',f"{data['longterm']}/100"]]
    t=Table(summary,colWidths=[70*mm,80*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#f5f3ff')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#d8dbe2')),('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),9),('PADDING',(0,0),(-1,-1),7)])); story += [t,Spacer(1,10)]
    story += [Paragraph('5-minute verdict',styles['h']),Paragraph("This report is decision support, not a profit guarantee. Focus on business quality, valuation, cash flow and risks rather than one score.",styles['body'])]
    story += [Paragraph('Business dependency map',styles['h']),Paragraph(dependency_text or 'Add company-specific revenue, customer, geography, commodity and regulatory dependencies in the app.',styles['body'])]
    story += [Paragraph('Bull case',styles['h']),Paragraph(bull or 'No bull case entered.',styles['body']),Paragraph('Bear case',styles['h']),Paragraph(bear or 'No bear case entered.',styles['body'])]
    story += [Paragraph('Positive checks',styles['h'])]
    for x in data.get('positives',[]): story.append(Paragraph('• '+x,styles['body']))
    story += [Paragraph('Risks and disadvantages',styles['h'])]
    for x in data.get('risks',[]): story.append(Paragraph('• '+x,styles['body']))
    story += [Spacer(1,14),Paragraph('Important: Live prices and third-party data can be delayed or incomplete. Verify every material number against exchange filings, RHP/DRHP, annual reports and licensed market data before investing.',styles['small'])]
    doc.build(story); bio.seek(0); return bio.getvalue()

# ---------- Header ----------
st.markdown("""<div class="hero"><h1>EquityLens AI</h1><p>IPO + listed-share research in a 5-minute dashboard, with deeper institutional-style checks.</p></div>""",unsafe_allow_html=True)

mode=st.radio("Choose research mode",["Listed Share","IPO – Mainboard / SME"],horizontal=True)

# ================= LISTED SHARE =================
if mode=="Listed Share":
    c1,c2=st.columns([3,1])
    with c1: symbol=st.text_input("NSE symbol",value="TATAMOTORS",placeholder="Examples: RELIANCE, TCS, HDFCBANK")
    with c2: run=st.button("Analyse share",type="primary",use_container_width=True)
    st.caption("Enter the NSE symbol. The app automatically adds .NS. Yahoo Finance is used for prototype data and must be replaced/verified with a licensed Indian market-data source for production decisions.")
    if run or symbol:
        with st.spinner("Building research dashboard…"):
            info,hist,stmts=load_stock(symbol)
            d=analyze_stock(symbol,info,hist,stmts)
        if not info and hist.empty:
            st.error("Live stock data could not be fetched. Check the NSE symbol or try again later.")
            st.stop()
        st.subheader(d['name'])
        action,tone,reason=stock_action(d)
        st.markdown(decision_html(action,tone,reason,d['overall'],'Valuation score',f"{d['scores']['Valuation']:.0f}/100"),unsafe_allow_html=True)
        st.markdown("<div class='step-title'>Step 1 — The numbers that matter most</div>",unsafe_allow_html=True)
        top=st.columns(6)
        top[0].metric("Price",money(d['price']))
        top[1].metric("Overall",f"{d['overall']}/100",score_label(d['overall']))
        top[2].metric("Market cap",money(d['marketcap'],True))
        top[3].metric("P/E",f"{d['pe']:.1f}x" if d['pe'] else '—')
        top[4].metric("ROE",pct(d['roe']))
        top[5].metric("Debt/Equity",f"{d['debt_equity']:.2f}")

        st.markdown(f"<div class='{verdict_class(d['overall'])}'><b>Why this decision?</b><br>{explain_pe(d['pe'])} Revenue growth, profitability, debt, cash quality and valuation are considered together.</div>",unsafe_allow_html=True)
        st.markdown("<div class='step-title'>Step 2 — Read the company in order</div>",unsafe_allow_html=True)
        tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["1. Quick Decision","2. Financial Trend","3. Business & Dependency","4. Valuation","5. Risks","6. PDF"])
        with tab1:
            st.markdown("### Final decision in one minute")
            st.write(reason)
            summary_rows=[
                ['Decision',action],['Business quality',score_label(d['overall'])],['Growth',score_label(d['scores']['Growth'])],
                ['Profitability',score_label(d['scores']['Profitability'])],['Debt position',score_label(d['scores']['Balance Sheet'])],
                ['Valuation',score_label(d['scores']['Valuation'])],['Cash-flow quality',score_label(d['scores']['Cash Quality'])]
            ]
            st.dataframe(pd.DataFrame(summary_rows,columns=['Question','Answer']),use_container_width=True,hide_index=True)
            c1,c2=st.columns([1,1])
            with c1: st.plotly_chart(gauge("Overall quality",d['overall']),use_container_width=True)
            with c2:
                score_df=pd.DataFrame({'Area':list(d['scores'].keys()),'Score':list(d['scores'].values())})
                fig=px.bar(score_df,x='Score',y='Area',orientation='h',range_x=[0,100],text_auto='.0f')
                fig.update_layout(height=300,margin=dict(l=10,r=10,t=25,b=10),showlegend=False)
                st.plotly_chart(fig,use_container_width=True)
            dash=pd.DataFrame([
                ['Business',d['sector'],d['industry']],['Growth',score_label(d['scores']['Growth']),f"Revenue CAGR {d['rev_cagr']:.1f}% | Profit CAGR {d['pat_cagr']:.1f}%"],
                ['Profitability',score_label(d['scores']['Profitability']),f"ROE {d['roe']:.1f}% | PAT margin {d['margin']:.1f}%"],
                ['Valuation',score_label(d['scores']['Valuation']),f"P/E {d['pe']:.1f}x | P/B {d['pb']:.1f}x"],
                ['Balance sheet',score_label(d['scores']['Balance Sheet']),f"Debt/Equity {d['debt_equity']:.2f}"],
                ['Cash quality',score_label(d['scores']['Cash Quality']),f"OCF/PAT {d['cash_quality']:.0f}%" if d['cash_quality'] else 'Cash-flow data limited'],
                ['Volatility',('High' if d['beta']>1.4 else 'Moderate' if d['beta']>.8 else 'Low'),f"Beta {d['beta']:.2f}"],
                ['Analyst target','Indicative only',money(d['target'])+(f" ({d['upside']:.1f}% implied)" if d['upside'] is not None else '')]
            ],columns=['Area','Status','What it means'])
            st.dataframe(dash,use_container_width=True,hide_index=True)
            st.markdown("**Green flags**")
            for x in d['positives']: st.success(x)
            st.markdown("**Red flags**")
            for x in d['risks']: st.warning(x)
        with tab2:
            if not hist.empty:
                h=hist.reset_index(); fig=px.line(h,x=h.columns[0],y='Close',title='5-year share-price trend')
                fig.update_layout(height=350); st.plotly_chart(fig,use_container_width=True)
            if d['revenues']:
                fin=pd.DataFrame({'Year':d['years'][-len(d['revenues']):],'Revenue (₹ Cr)':d['revenues'],'PAT (₹ Cr)':d['profits'][-len(d['revenues']):] if d['profits'] else [0]*len(d['revenues'])})
                st.plotly_chart(px.bar(fin,x='Year',y=['Revenue (₹ Cr)','PAT (₹ Cr)'],barmode='group',title='Revenue and profit'),use_container_width=True)
            metrics=pd.DataFrame([
                ['Revenue growth (latest)',pct(d['revenue_growth'])],['Earnings growth (latest)',pct(d['earnings_growth'])],['Operating margin',pct(d['opmargin'])],['PAT margin',pct(d['margin'])],['ROE',pct(d['roe'])],['ROA',pct(d['roa'])],['Dividend yield',pct(d['dividend'])],['EPS',money(d['eps'])]
            ],columns=['Metric','Value'])
            st.dataframe(metrics,use_container_width=True,hide_index=True)
        with tab3:
            st.write(d['summary'] or 'Business description not returned by the current data provider.')
            dependency=st.text_area("Major business dependencies",value="Revenue mix; top customers; key geography; commodity/input prices; regulation; interest rates; currency; technology/platform dependency; supplier concentration.",height=120)
            c1,c2=st.columns(2)
            with c1: bull=st.text_area("Bull case",value="Growth accelerates, margins improve, new capacity/products scale, and valuation remains supported by earnings.",height=120)
            with c2: bear=st.text_area("Bear case / disadvantages",value="Demand slows, competition intensifies, margins compress, regulation changes, or the current valuation leaves little room for disappointment.",height=120)
            st.info("For a production-grade report, these dependency fields should be populated from annual reports, investor presentations, exchange filings, conference calls and segment notes—not guessed from ratios.")
        with tab4:
            v1,v2,v3,v4=st.columns(4)
            v1.metric('P/E',f"{d['pe']:.1f}x" if d['pe'] else '—');v2.metric('Forward P/E',f"{d['forward_pe']:.1f}x" if d['forward_pe'] else '—');v3.metric('P/B',f"{d['pb']:.1f}x" if d['pb'] else '—');v4.metric('Book value',money(d['book']))
            st.write(explain_pe(d['pe']))
            if d['price'] and d['52low'] and d['52high']:
                pos=(d['price']-d['52low'])/(d['52high']-d['52low'])*100 if d['52high']!=d['52low'] else 0
                st.progress(max(0,min(100,int(pos))),text=f"52-week position: low {money(d['52low'])} • current {money(d['price'])} • high {money(d['52high'])}")
            st.warning("A reliable fair value needs explicit assumptions and often more than one method: peer multiples, DCF, residual income, asset value or sum-of-the-parts. Do not treat an analyst target as guaranteed fair value.")
        with tab5:
            st.markdown("### What can go wrong?")
            for x in d['risks']: st.error(x)
            risk_template=pd.DataFrame([
                ['Customer concentration','How much revenue comes from top 1/5/10 customers?'],['Geography','Which country or region drives revenue/profit?'],['Input dependency','Which commodity, supplier or imported component matters most?'],['Regulatory','Which licence, policy or rule can alter economics?'],['Capital allocation','Is cash used for sensible capex, debt reduction, dividends or risky acquisitions?'],['Governance','Auditor changes, related-party transactions, pledging, litigation, dilution.'],['Disruption','Can technology or a lower-cost competitor weaken the moat?']
            ],columns=['Risk lens','Question to answer'])
            st.dataframe(risk_template,use_container_width=True,hide_index=True)
        with tab6:
            # Maintain values even if user never opened Business DNA tab
            dependency=locals().get('dependency','Revenue, customer, geography, regulation, input-cost and technology dependencies require filing-level verification.')
            bull=locals().get('bull','Business compounds earnings faster than expected and sustains returns on capital.')
            bear=locals().get('bear','Growth or margins disappoint, while valuation compresses.')
            pdf=build_pdf(d['name'],'Listed Share',d,dependency,bull,bear)
            st.download_button('Download research PDF',pdf,file_name=f"{d['symbol'].replace('.','_')}_EquityLens_Report.pdf",mime='application/pdf',type='primary')
            st.caption('The PDF is deliberately concise. The interactive app contains the full charts and drill-down sections.')

# ================= IPO =================
else:
    live=fetch_nse_ipos(); source='Live NSE attempt'
    if live.empty: live=DEMO_IPOS.copy(); source='Demo fallback — live NSE endpoint unavailable'
    filt=st.segmented_control('IPO section',['All','Mainboard','SME'],default='All') if hasattr(st,'segmented_control') else st.radio('IPO section',['All','Mainboard','SME'],horizontal=True)
    shown=live if filt=='All' else live[live['segment']==filt.upper()]
    selected=st.selectbox('Select IPO',shown['company'].tolist())
    manual=st.text_input('Or type an IPO/company name')
    company=manual.strip() or selected
    row=shown[shown['company']==selected].iloc[0]
    segment=row.get('segment','MAINBOARD')
    st.caption(f"IPO discovery source: {source}. For production, connect a documented authorised IPO API and store RHP/DRHP-derived data with citations.")
    top=st.columns(5)
    top[0].metric('Segment',segment);top[1].metric('Status',row.get('status','—'));top[2].metric('Open',row.get('open_date','—'));top[3].metric('Close',row.get('close_date','—'));top[4].metric('Price band',row.get('price_band','—'))
    st.markdown('### Financial and issue inputs')
    st.warning('IMPORTANT: These IPO fields are currently editable demo inputs unless live verified data is available. Do not invest using the default numbers. Replace them with verified RHP, NSE/BSE subscription and valuation data.')
    with st.expander('Enter / review IPO data',expanded=True):
        a,b,c=st.columns(3)
        sales=a.number_input('Revenue CAGR %',value=22.0); pat=b.number_input('PAT CAGR %',value=29.0); margin=c.number_input('PAT margin %',value=12.5)
        roe=a.number_input('ROE %',value=21.0); roce=b.number_input('ROCE %',value=24.0); de=c.number_input('Debt/Equity',value=.35)
        pe=a.number_input('IPO P/E',value=31.0); peer_pe=b.number_input('Peer median P/E',value=28.0); pb=c.number_input('Price/Book',value=4.2)
        fresh=a.number_input('Fresh issue %',0.0,100.0,65.0); ofs=b.number_input('OFS %',0.0,100.0,35.0); cash_quality=c.number_input('Operating cash flow / PAT %',value=92.0)
        qib=a.number_input('QIB subscription x',value=14.0); nii=b.number_input('NII/HNI subscription x',value=22.0); retail=c.number_input('Retail subscription x',value=8.0)
        gmp=a.number_input('Unofficial GMP %',value=16.0,help='Unofficial and manipulable; receives limited weight.')
    m={'segment':segment,'sales_cagr':sales,'pat_cagr':pat,'margin':margin,'roe':roe,'roce':roce,'de':de,'pe':pe,'peer_pe':peer_pe,'pb':pb,'fresh':fresh,'ofs':ofs,'cash_quality':cash_quality,'qib':qib,'nii':nii,'retail':retail,'gmp':gmp}
    d=analyze_ipo(m)
    st.subheader(company)
    action,tone,reason=ipo_action(d,segment)
    st.markdown(decision_html(action,tone,reason,d['overall'],'Listing score',f"{d['listing']}/100"),unsafe_allow_html=True)
    st.markdown("<div class='step-title'>Step 1 — IPO decision snapshot</div>",unsafe_allow_html=True)
    s1,s2,s3,s4=st.columns(4)
    s1.metric('Overall IPO',f"{d['overall']}/100",score_label(d['overall']));s2.metric('Listing setup',f"{d['listing']}/100");s3.metric('Long-term quality',f"{d['longterm']}/100");s4.metric('Valuation premium',f"{(pe/peer_pe-1)*100:.1f}%" if peer_pe else '—')
    st.markdown(f"<div class='{verdict_class(d['overall'])}'><b>Decision dashboard:</b> {score_label(d['overall'])}. Use listing and long-term scores separately. Allotment probability, market conditions and SME liquidity can materially change the outcome.</div>",unsafe_allow_html=True)
    t1,t2,t3,t4,t5=st.tabs(['1. Quick Decision','2. Graphs','3. Business & Dependency','4. Risks','5. PDF'])
    with t1:
        st.markdown("### Should you apply?")
        st.write(reason)
        summary_rows=[['Decision',action],['Overall issue quality',score_label(d['overall'])],['Listing setup',score_label(d['listing'])],['Long-term quality',score_label(d['longterm'])],['Segment risk','Higher liquidity risk' if segment=='SME' else 'Mainboard']]
        st.dataframe(pd.DataFrame(summary_rows,columns=['Question','Answer']),use_container_width=True,hide_index=True)
        c1,c2,c3=st.columns(3)
        c1.plotly_chart(gauge('Overall',d['overall']),use_container_width=True);c2.plotly_chart(gauge('Listing',d['listing']),use_container_width=True);c3.plotly_chart(gauge('Long term',d['longterm']),use_container_width=True)
        dash=pd.DataFrame([
            ['Growth',score_label(min(100,50+sales+pat*.5)),f"Revenue CAGR {sales:.1f}% | PAT CAGR {pat:.1f}%"],['Capital efficiency','Strong' if min(roe,roce)>=18 else 'Average/Weak',f"ROE {roe:.1f}% | ROCE {roce:.1f}%"],['Valuation','Expensive' if peer_pe and pe>peer_pe*1.25 else 'Reasonable/Discount',f"IPO P/E {pe:.1f}x | Peer {peer_pe:.1f}x"],['Issue quality','Fresh-capital led' if fresh>ofs else 'OFS led',f"Fresh {fresh:.0f}% | OFS {ofs:.0f}%"],['Institutional demand','Strong' if qib>=10 else 'Weak/Moderate',f"QIB {qib:.1f}x"],['Cash quality','Strong' if cash_quality>=80 else 'Weak/Moderate',f"OCF/PAT {cash_quality:.0f}%"],['Liquidity','Higher risk' if segment=='SME' else 'Normal mainboard caveats',segment]
        ],columns=['Check','Status','Evidence'])
        st.dataframe(dash,use_container_width=True,hide_index=True)
        for x in d['positives']: st.success(x)
        for x in d['risks']: st.warning(x)
    with t2:
        fig=px.bar(pd.DataFrame({'Category':['QIB','NII/HNI','Retail'],'Subscription':[qib,nii,retail]}),x='Category',y='Subscription',text_auto='.1f',title='Subscription by investor category')
        st.plotly_chart(fig,use_container_width=True)
        radar=go.Figure(go.Scatterpolar(r=[min(100,50+sales),min(100,50+pat*.8),max(0,100-(pe/peer_pe-1)*100 if peer_pe else 50),max(0,100-de*35),cash_quality],theta=['Revenue growth','Profit growth','Valuation','Balance sheet','Cash quality'],fill='toself'))
        radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),height=420,title='IPO quality radar')
        st.plotly_chart(radar,use_container_width=True)
    with t3:
        dependency=st.text_area('Major business dependencies',value='Top customers and revenue concentration; geography; raw material/input prices; licences and regulation; supplier concentration; technology; working-capital cycle; key promoter or management dependency.',height=130)
        use=st.text_area('Use of proceeds',value='Verify exact allocation to debt repayment, capex, working capital, acquisitions and general corporate purposes. High OFS means more money goes to selling shareholders rather than the company.',height=110)
        c1,c2=st.columns(2)
        with c1: bull=st.text_area('Bull case',value='Strong sector growth, earnings compounding, reasonable issue pricing, good institutional demand and effective use of fresh proceeds.',height=120)
        with c2: bear=st.text_area('Bear case / disadvantages',value='Valuation is too optimistic, growth normalises, promoter/investor exit dominates, cash flow is weak, or post-listing liquidity disappears.',height=120)
    with t4:
        risk_df=pd.DataFrame([
            ['Valuation risk',f"IPO P/E {pe:.1f}x vs peer {peer_pe:.1f}x"],['OFS/exit risk',f"{ofs:.0f}% OFS"],['Cash conversion',f"OCF/PAT {cash_quality:.0f}%"],['Leverage',f"Debt/Equity {de:.2f}"],['Demand quality',f"QIB {qib:.1f}x; retail {retail:.1f}x"],['SME liquidity','High' if segment=='SME' else 'Not applicable'],['Unverified risks','Litigation, promoter history, related parties, auditor notes, contingent liabilities, customer/supplier concentration must come from offer documents.']
        ],columns=['Risk','Current evidence'])
        st.dataframe(risk_df,use_container_width=True,hide_index=True)
        st.error('Never treat GMP, subscription or an AI score as guaranteed listing profit. Market direction on listing day can override the issue setup.')
    with t5:
        dependency=locals().get('dependency','Customer, geography, input, regulatory, working-capital and promoter dependencies require RHP verification.')
        bull=locals().get('bull','Growth and institutional demand support a premium listing and earnings compound after listing.')
        bear=locals().get('bear','Valuation, cash flow or liquidity disappoint after listing.')
        pdf=build_pdf(company,'IPO',d,dependency,bull,bear)
        st.download_button('Download IPO research PDF',pdf,file_name=f"{re.sub('[^A-Za-z0-9]+','_',company)}_IPO_Report.pdf",mime='application/pdf',type='primary')

st.divider()
st.caption("EquityLens AI is a research-assistance prototype. It does not provide guaranteed returns or personalised regulated investment advice. Verify all material facts with NSE/BSE/SEBI filings, annual reports, RHP/DRHP and licensed data before committing capital.")
