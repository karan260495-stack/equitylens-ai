from __future__ import annotations

import io, math, os, re, xml.etree.ElementTree as ET
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

st.set_page_config(page_title='EquityLens One', page_icon='◉', layout='wide', initial_sidebar_state='collapsed')

CSS = '''
<style>
:root{--ink:#17212b;--muted:#667085;--line:#e5e9ef;--bg:#f5f7fa;--card:#fff;--blue:#387ed1;--blue2:#eaf2fd;--green:#138a5b;--red:#d44747;--amber:#b7791f;--navy:#101828}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{max-width:1440px;padding:1rem 1.4rem 4rem}
[data-testid="stHeader"]{background:rgba(245,247,250,.92)}
.hero{background:linear-gradient(110deg,#0f172a,#173b70 62%,#387ed1);border-radius:18px;padding:28px 30px;color:white;box-shadow:0 14px 36px rgba(15,23,42,.16);margin-bottom:16px}
.hero h1{font-size:2.05rem;margin:0 0 5px;font-weight:800}.hero p{margin:0;color:#d7e5f8}.hero-badge{display:inline-block;background:rgba(255,255,255,.14);padding:5px 10px;border:1px solid rgba(255,255,255,.22);border-radius:99px;font-size:.75rem;margin-bottom:10px}
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

IPO_DEMO = [
 {'name':'Apex Renewables Limited','type':'Mainboard','price_min':315,'price_max':332,'lot':45,'fresh':820,'ofs':180,'rev':[890,1180,1560,2090,2710],'pat':[62,91,139,208,291],'roe':24.2,'roce':27.8,'de':0.31,'peer_pe':31,'ipo_pe':28.4,'qib':18.7,'nii':12.4,'retail':6.1,'gmp':9.5,'depend':[('Solar EPC',54),('Government tenders',24),('Private PPAs',14),('O&M',8)],'risks':['Tender concentration','Working-capital cycle','Module-price volatility']},
 {'name':'Nova Precision Components Limited','type':'SME','price_min':118,'price_max':124,'lot':1000,'fresh':42,'ofs':0,'rev':[54,72,94,128,161],'pat':[3.1,4.8,7.5,11.2,15.4],'roe':29.1,'roce':32.5,'de':0.18,'peer_pe':26,'ipo_pe':21.7,'qib':0,'nii':41.5,'retail':38.2,'gmp':13.0,'depend':[('Top 3 customers',61),('Auto components',48),('Exports',22),('Industrial products',30)],'risks':['SME liquidity','Customer concentration','Small scale']}
]


def val(x, default=None):
    try:
        if x is None or x == '': return default
        if isinstance(x,str): x=x.replace(',','').replace('%','')
        return float(x)
    except Exception:return default

def money_cr(x):
    return 'N/A' if x is None else f'₹{x:,.0f} Cr'
def inr(x): return 'N/A' if x is None else f'₹{x:,.2f}'
def pct(x): return 'N/A' if x is None else f'{x:,.1f}%'
def rx(x): return 'N/A' if x is None else f'{x:,.2f}x'

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
    sales:list=field(default_factory=list); profit:list=field(default_factory=list); ocf:list=field(default_factory=list); history:pd.DataFrame=field(default_factory=pd.DataFrame); news:list=field(default_factory=list); depend:list=field(default_factory=list); peers:list=field(default_factory=list); source:str='Demo'; business:str=''; warnings:list=field(default_factory=list)

def load_stock(symbol):
    s=symbol.upper().replace('.NS','').strip(); base=DEMO.get(s, {})
    d=Stock(symbol=s,**{k:v for k,v in base.items() if k in Stock.__dataclass_fields__}) if base else Stock(symbol=s,name=s)
    d.source='Demo fallback'
    try:
        t=yf.Ticker(s+'.NS'); h=t.history(period='5y',auto_adjust=True)
        if not h.empty:
            d.history=h.reset_index()[['Date','Close']]; d.price=val(h['Close'].iloc[-1],d.price);d.source='Live price + fallback fundamentals'
        info={}
        try: info=t.get_info() or {}
        except Exception: pass
        if info:
            d.name=info.get('longName') or d.name;d.sector=info.get('sector') or d.sector;d.industry=info.get('industry') or d.industry
            d.market_cap=(val(info.get('marketCap'))/1e7) if val(info.get('marketCap')) else d.market_cap
            d.pe=val(info.get('trailingPE'),d.pe);d.pb=val(info.get('priceToBook'),d.pb)
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
    if d.history.empty and d.price:
        dates=pd.date_range(end=pd.Timestamp.today(),periods=60,freq='MS');rng=np.random.default_rng(abs(hash(s))%10000);returns=rng.normal(.008,.06,len(dates));series=d.price*np.exp(np.cumsum(returns)-np.cumsum(returns)[-1]);d.history=pd.DataFrame({'Date':dates,'Close':series})
    if not d.sales:
        d.sales=[100,118,139,162,190];d.profit=[8,10,13,16,20];d.ocf=[7,9,12,15,19]
    if not d.depend:d.depend=[('Core business',55),('Top customers / contracts',22),('Domestic demand',15),('Exports / other',8)]
    d.news=news_feed(d.name or s)
    if not d.business:d.business=f'{d.name} operates in the {d.industry or d.sector or "listed equities"} segment. Verify the annual report for the exact revenue mix and major customer dependencies.'
    return d

def score_stock(d):
    sg=cagr(d.sales[0],d.sales[-1],max(1,len(d.sales)-1));pg=cagr(d.profit[0],d.profit[-1],max(1,len(d.profit)-1))
    quality=50
    if sg is not None: quality += 12 if sg>15 else 7 if sg>8 else -5 if sg<0 else 2
    if pg is not None: quality += 14 if pg>18 else 8 if pg>10 else -8 if pg<0 else 2
    if d.roe is not None: quality += 10 if d.roe>20 else 6 if d.roe>14 else -4 if d.roe<8 else 1
    if d.de is not None: quality += 7 if d.de<.5 else 2 if d.de<1 else -8
    val_score=60
    if d.pe and d.sector_pe:
        prem=(d.pe/d.sector_pe-1)*100;val_score += 15 if prem<-15 else 7 if prem<5 else -8 if prem>25 else -2
    if d.pb: val_score += 5 if d.pb<3 else -5 if d.pb>8 else 0
    ns=sum(sent(x['title']+' '+x.get('summary',''))[1] for x in d.news);news_impact=max(-8,min(8,ns*2))
    overall=max(0,min(100,round(.68*quality+.32*val_score+news_impact)))
    if overall>=74: verdict=('BUY GRADUALLY','buy','Strong enough for phased accumulation, subject to entry price and verification of filings.')
    elif overall>=57: verdict=('WATCH / WAIT','wait','Business may be investable, but valuation, data gaps or current risks reduce the margin of safety.')
    else: verdict=('AVOID FOR NOW','avoid','Risk–reward is currently unattractive or the available evidence is insufficient.')
    return {'overall':overall,'quality':round(quality),'valuation':round(val_score),'news':news_impact,'sales_cagr':sg,'profit_cagr':pg,'verdict':verdict}

def line_chart(df,title):
    fig=go.Figure(go.Scatter(x=df['Date'],y=df['Close'],mode='lines',line=dict(color='#387ed1',width=2.6),fill='tozeroy',fillcolor='rgba(56,126,209,.08)'))
    fig.update_layout(title=title,height=340,margin=dict(l=12,r=12,t=48,b=15),paper_bgcolor='white',plot_bgcolor='white',xaxis=dict(showgrid=False),yaxis=dict(gridcolor='#edf0f4',tickprefix='₹'))
    return fig

def annual_chart(d):
    years=[f'FY{str(22+i)[-2:]}' for i in range(len(d.sales))]
    fig=go.Figure();fig.add_bar(x=years,y=d.sales,name='Revenue',marker_color='#387ed1');fig.add_bar(x=years,y=d.profit,name='PAT',marker_color='#19a974')
    fig.update_layout(barmode='group',height=350,margin=dict(l=10,r=10,t=35,b=10),paper_bgcolor='white',plot_bgcolor='white',yaxis_title='₹ crore',legend=dict(orientation='h',y=1.12),yaxis=dict(gridcolor='#edf0f4'))
    return fig

def cash_chart(d):
    years=[f'FY{str(22+i)[-2:]}' for i in range(len(d.ocf))]
    fig=go.Figure(go.Bar(x=years,y=d.ocf,marker_color='#7c5ce6'))
    fig.update_layout(height=350,margin=dict(l=10,r=10,t=35,b=10),paper_bgcolor='white',plot_bgcolor='white',yaxis_title='Operating cash flow (₹ crore)',yaxis=dict(gridcolor='#edf0f4'))
    return fig

def pdf_stock(d,s):
    b=io.BytesIO();doc=SimpleDocTemplate(b,pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=14*mm,bottomMargin=14*mm);styles=getSampleStyleSheet();story=[Paragraph('EquityLens One — Research Summary',styles['Title']),Paragraph(d.name,styles['Heading2']),Spacer(1,5*mm)]
    rows=[['Verdict',s['verdict'][0]],['Overall score',f"{s['overall']}/100"],['Price',inr(d.price)],['P/E',rx(d.pe)],['ROE',pct(d.roe)],['Debt/Equity',rx(d.de)],['Revenue CAGR',pct(s['sales_cagr'])],['Profit CAGR',pct(s['profit_cagr'])],['Data source',d.source]]
    t=Table(rows,colWidths=[55*mm,110*mm]);t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.lightgrey),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eef3f8')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)]));story += [t,Spacer(1,6*mm),Paragraph('Business and dependencies',styles['Heading2']),Paragraph(d.business,styles['BodyText'])]
    doc.build(story);return b.getvalue()

st.markdown("<div class='hero'><div class='hero-badge'>EQUITYLENS ONE • DECISION COMMAND CENTER</div><h1>Everything you need before investing — on one dashboard.</h1><p>Stocks, Mainboard IPOs, SME IPOs, five-year financials, valuation, news, risks, dependencies and a clear decision.</p></div>",unsafe_allow_html=True)

mode=st.radio('Research universe',['Listed Share','IPO — Mainboard / SME'],horizontal=True,label_visibility='collapsed')

if mode=='Listed Share':
    st.markdown("<div class='searchbox'>",unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1:symbol=st.text_input('Search NSE company',value='RELIANCE',placeholder='Example: RELIANCE, MAZDOCK, TCS')
    with c2:run=st.button('Analyse company',width='stretch')
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
            kpi('Current price',inr(d.price),'Latest available'),kpi('Market cap',money_cr(d.market_cap),'Approximate'),kpi('P/E',rx(d.pe),f'Sector {rx(d.sector_pe)}'),kpi('P/B',rx(d.pb),'Price to book'),kpi('ROE',pct(d.roe),'Capital efficiency'),kpi('Debt / Equity',rx(d.de),'Balance-sheet risk'),kpi('Revenue CAGR',pct(sc['sales_cagr']),'Five-year trend'),kpi('Profit CAGR',pct(sc['profit_cagr']),'Five-year trend'),kpi('ROCE',pct(d.roce),'Operating efficiency'),kpi('News adjustment',f"{sc['news']:+d}",'Max ±8 points'),kpi('Business quality',f"{sc['quality']}/100",'Fundamentals'),kpi('Valuation',f"{sc['valuation']}/100",'Relative pricing')])+'</div>',unsafe_allow_html=True)
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
            st.markdown("<div class='section'>At-a-glance investment checklist</div>",unsafe_allow_html=True)
            checklist=pd.DataFrame({'Question':['Is the business growing?','Are profits compounding?','Is capital efficiency healthy?','Is debt manageable?','Is valuation reasonable?','Is current news supportive?'], 'Answer':['Yes' if sc['sales_cagr'] and sc['sales_cagr']>8 else 'Mixed','Yes' if sc['profit_cagr'] and sc['profit_cagr']>10 else 'Mixed','Strong' if d.roe and d.roe>18 else 'Average','Yes' if d.de is None or d.de<.8 else 'Needs attention','Fair' if not(d.pe and d.sector_pe and d.pe>d.sector_pe*1.2) else 'Expensive','Positive' if sc['news']>1 else 'Negative' if sc['news']<-1 else 'Mixed']})
            st.dataframe(checklist,width='stretch',hide_index=True)
        with tabs[1]:
            c1,c2=st.columns(2);c1.plotly_chart(annual_chart(d),width='stretch');c2.plotly_chart(cash_chart(d),width='stretch')
            years=[f'FY{str(22+i)[-2:]}' for i in range(len(d.sales))]
            fin=pd.DataFrame({'Year':years,'Revenue (₹ Cr)':d.sales,'PAT (₹ Cr)':d.profit,'Operating Cash Flow (₹ Cr)':d.ocf})
            fin['PAT margin %']=(fin['PAT (₹ Cr)']/fin['Revenue (₹ Cr)']*100).round(1);fin['Cash conversion %']=(fin['Operating Cash Flow (₹ Cr)']/fin['PAT (₹ Cr)']*100).replace([np.inf,-np.inf],np.nan).round(1)
            st.dataframe(fin,width='stretch',hide_index=True)
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
else:
    st.markdown("<div class='searchbox'>",unsafe_allow_html=True)
    c1,c2=st.columns([2,1])
    with c1:ipo_name=st.selectbox('Select IPO', [f"{x['name']} — {x['type']}" for x in IPO_DEMO])
    with c2:st.caption('Showcase dataset • connect an authorised IPO feed for live issues')
    st.markdown('</div>',unsafe_allow_html=True)
    ipo=IPO_DEMO[[f"{x['name']} — {x['type']}" for x in IPO_DEMO].index(ipo_name)]
    rev_cagr=cagr(ipo['rev'][0],ipo['rev'][-1],4);pat_cagr=cagr(ipo['pat'][0],ipo['pat'][-1],4);premium=(ipo['ipo_pe']/ipo['peer_pe']-1)*100
    listing=55+(10 if ipo['qib']>10 else 0)+(8 if ipo['nii']>10 else 0)+(7 if ipo['retail']>5 else 0)+(8 if ipo['gmp']>8 else 0)-(10 if ipo['type']=='SME' else 0)
    longterm=50+(12 if rev_cagr>15 else 5)+(14 if pat_cagr>18 else 6)+(8 if ipo['roe']>18 else 0)+(7 if ipo['de']<.5 else -8)+(8 if premium<0 else -5)
    overall=max(0,min(100,round(.45*listing+.55*longterm)))
    verdict='APPLY SELECTIVELY' if overall>=70 else 'WATCH / APPLY CAUTIOUSLY' if overall>=56 else 'SKIP FOR NOW';cls='buy' if overall>=70 else 'wait' if overall>=56 else 'avoid'
    a,b,c=st.columns([1.7,1,1])
    with a:st.markdown(f"<div class='verdict {cls}'><div class='eyebrow'>IPO DECISION</div><div class='vbig'>{verdict}</div><p>{ipo['name']} • {ipo['type']}</p></div>",unsafe_allow_html=True)
    with b:st.markdown(f"<div class='verdict'><div class='eyebrow'>LISTING SETUP</div><div class='score'>{round(listing)}<small>/100</small></div><p>Subscription, GMP and issue type</p></div>",unsafe_allow_html=True)
    with c:st.markdown(f"<div class='verdict'><div class='eyebrow'>LONG-TERM QUALITY</div><div class='score'>{round(longterm)}<small>/100</small></div><p>Growth, returns, debt and valuation</p></div>",unsafe_allow_html=True)
    st.markdown("<div class='grid6'>"+''.join([kpi('Price band',f"₹{ipo['price_min']}–₹{ipo['price_max']}"),kpi('Lot size',f"{ipo['lot']} shares"),kpi('Fresh issue',money_cr(ipo['fresh'])),kpi('Offer for sale',money_cr(ipo['ofs'])),kpi('IPO P/E',rx(ipo['ipo_pe']),f"Peers {rx(ipo['peer_pe'])}"),kpi('Valuation premium',pct(premium)),kpi('Revenue CAGR',pct(rev_cagr)),kpi('PAT CAGR',pct(pat_cagr)),kpi('ROE',pct(ipo['roe'])),kpi('Debt/Equity',rx(ipo['de'])),kpi('QIB subscription',rx(ipo['qib'])),kpi('GMP sentiment',pct(ipo['gmp']),'Unofficial')])+'</div>',unsafe_allow_html=True)
    tabs=st.tabs(['IPO Command Center','5-Year Results','Subscription','Business & Dependencies','Risks'])
    with tabs[0]:
        st.markdown(f"<div class='card'><h3>Five-minute IPO verdict</h3><p><b>{verdict}</b>. The issue combines {rev_cagr:.1f}% revenue CAGR and {pat_cagr:.1f}% PAT CAGR. IPO valuation is {abs(premium):.1f}% {'below' if premium<0 else 'above'} the peer benchmark. Treat GMP only as a sentiment input, not proof of listing gains.</p></div>",unsafe_allow_html=True)
    with tabs[1]:
        years=['FY21','FY22','FY23','FY24','FY25'];fig=go.Figure();fig.add_bar(x=years,y=ipo['rev'],name='Revenue',marker_color='#387ed1');fig.add_bar(x=years,y=ipo['pat'],name='PAT',marker_color='#19a974');fig.update_layout(barmode='group',height=370,paper_bgcolor='white',plot_bgcolor='white',yaxis=dict(gridcolor='#edf0f4'),legend=dict(orientation='h',y=1.12));st.plotly_chart(fig,width='stretch')
        st.dataframe(pd.DataFrame({'Year':years,'Revenue ₹Cr':ipo['rev'],'PAT ₹Cr':ipo['pat']}),width='stretch',hide_index=True)
    with tabs[2]:
        sub=pd.DataFrame({'Category':['QIB','NII / HNI','Retail'],'Subscription (x)':[ipo['qib'],ipo['nii'],ipo['retail']]});fig=go.Figure(go.Bar(x=sub['Category'],y=sub['Subscription (x)'],marker_color=['#387ed1','#7c5ce6','#19a974']));fig.update_layout(height=350,paper_bgcolor='white',plot_bgcolor='white',yaxis=dict(gridcolor='#edf0f4'));st.plotly_chart(fig,width='stretch');st.dataframe(sub,width='stretch',hide_index=True)
    with tabs[3]:
        st.markdown("<div class='card'><h3>What drives this IPO business?</h3>",unsafe_allow_html=True)
        for name,p in ipo['depend']:st.markdown(f"<div class='dependency'><b>{name}</b><div class='bar'><i style='width:{p}%'></i></div><span>{p}%</span></div>",unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with tabs[4]:
        for r in ipo['risks']:st.markdown(f"<div class='flag bad'>{r}</div>",unsafe_allow_html=True)
        if ipo['type']=='SME':st.markdown("<div class='flag warn'>SME IPOs can have larger lots, thinner liquidity, sharper price moves and difficult exits after listing.</div>",unsafe_allow_html=True)

st.caption('EquityLens One is research support, not a guarantee or personalised investment advice. Live prices, exchange filings, RHPs and corporate announcements must be verified before investing.')
