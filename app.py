import os
from datetime import date, timedelta, datetime, timezone
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title='EquityLens AI V4', page_icon='📈', layout='wide')

st.markdown('''
<style>
:root{--ink:#22252b;--muted:#6f7782;--line:#e4e7eb;--bg:#f7f8fa;--card:#ffffff;--blue:#387ed1;--green:#18864b;--red:#c83c3c;--amber:#a36a00}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{max-width:1180px;padding-top:1rem;padding-bottom:3rem}
h1,h2,h3,h4,p,span,div,label{color:var(--ink)}
[data-testid="stHeader"]{background:rgba(247,248,250,.92)}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line)}
.hero{background:#fff;border:1px solid var(--line);border-radius:8px;padding:22px 24px;margin:4px 0 18px}
.hero-title{font-size:1.65rem;font-weight:700;margin:0 0 5px}.hero-sub{color:var(--muted);margin:0}
.verdict{background:#fff;border:1px solid var(--line);border-left:5px solid var(--blue);border-radius:8px;padding:18px 20px;margin:14px 0}
.verdict.buy{border-left-color:var(--green)}.verdict.wait{border-left-color:var(--amber)}.verdict.avoid{border-left-color:var(--red)}
.verdict-kicker{font-size:.72rem;color:var(--muted);letter-spacing:.08em;font-weight:700}.verdict-title{font-size:1.5rem;font-weight:750;margin:4px 0 6px}
.kpi-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin:12px 0 18px}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 14px;min-width:0}
.kpi-label{font-size:.77rem;color:var(--muted);margin-bottom:6px}.kpi-value{font-size:1.28rem;font-weight:700;line-height:1.25;overflow-wrap:anywhere}.kpi-note{font-size:.72rem;color:var(--muted);margin-top:5px}
.section-card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:18px;margin:10px 0 16px}
.good{color:var(--green);font-weight:650}.bad{color:var(--red);font-weight:650}.neutral{color:var(--amber);font-weight:650}
.news-card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:9px 0}.news-title{font-weight:700;font-size:1rem;margin-bottom:5px}.news-meta{font-size:.76rem;color:var(--muted)}
.badge{display:inline-block;border-radius:999px;padding:3px 8px;font-size:.72rem;font-weight:700}.badge.pos{background:#e8f5ed;color:#14753f}.badge.neg{background:#fdeaea;color:#ad2e2e}.badge.neu{background:#eef1f5;color:#59616c}
[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.stButton>button{background:var(--blue);color:#fff;border:0;border-radius:5px;font-weight:650;min-height:42px}.stButton>button:hover{background:#2e6fb9;color:#fff}
.stTabs [data-baseweb="tab-list"]{gap:18px;border-bottom:1px solid var(--line)}.stTabs [data-baseweb="tab"]{height:44px;padding-left:0;padding-right:0}.stTabs [aria-selected="true"]{color:var(--blue)}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"] div[data-baseweb="select"]>div{background:#fff;color:var(--ink);border-color:#cfd4da}
@media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.block-container{padding-left:.8rem;padding-right:.8rem}.hero{padding:17px}.verdict-title{font-size:1.25rem}}
</style>
''', unsafe_allow_html=True)

BASE='https://api.upstox.com/v2'
BASE3='https://api.upstox.com/v3'

POSITIVE_WORDS={
    'profit','growth','surge','rally','gain','gains','wins','order','contract','approval','expansion','record','upgrade',
    'dividend','buyback','partnership','launch','strong','beats','outperform','award','investment','acquisition','raises guidance'
}
NEGATIVE_WORDS={
    'loss','decline','falls','fall','drop','slump','fraud','probe','investigation','penalty','downgrade','default','delay',
    'cancelled','lawsuit','weak','misses','cut guidance','debt concern','fire','accident','shutdown','ban','regulatory action'
}


def get_token():
    try:
        return st.secrets.get('UPSTOX_ACCESS_TOKEN','')
    except Exception:
        return os.getenv('UPSTOX_ACCESS_TOKEN','')


def headers(token):
    return {'Accept':'application/json','Authorization':f'Bearer {token}'}


def api_get(url, token, params=None):
    r=requests.get(url,headers=headers(token),params=params,timeout=30)
    if r.status_code!=200:
        try:
            body=r.json()
            msg=body.get('errors') or body.get('message') or body
        except Exception:
            msg=r.text
        raise RuntimeError(f'Upstox API error {r.status_code}: {msg}')
    body=r.json()
    return body.get('data',body)


def num(v):
    try:
        if v in (None,'','-'): return None
        if isinstance(v,str): return float(v.replace(',','').replace('%','').strip())
        return float(v)
    except Exception:return None


def fmt_money(v):
    if v is None:return 'N/A'
    av=abs(v)
    if av>=1e7:return f'₹{v/1e7:,.2f} Cr'
    if av>=1e5:return f'₹{v/1e5:,.2f} L'
    return f'₹{v:,.2f}'


def fmt_price(v): return f'₹{v:,.2f}' if v is not None else 'N/A'
def fmt_ratio(v): return f'{v:,.2f}x' if v is not None else 'N/A'
def fmt_pct(v): return f'{v:,.2f}%' if v is not None else 'N/A'


def kpi(label,value,note=''):
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div><div class='kpi-note'>{note}</div></div>",unsafe_allow_html=True)


def find_instrument(query, token):
    data=api_get(f'{BASE}/instruments/search',token,{'query':query,'exchange':'NSE','segment':'EQ','page_number':1,'records':20})
    items=data.get('instruments',data if isinstance(data,list) else []) if data else []
    eq=[x for x in items if x.get('segment')=='NSE_EQ' and x.get('instrument_type') in ('EQ','BE','SM')]
    exact=[x for x in eq if x.get('trading_symbol','').upper()==query.upper()]
    return (exact or eq)[:10]


def fetch_news(key,token):
    try:
        data=api_get(f'{BASE}/news',token,{'category':'instrument_keys','instrument_keys':key,'page_number':1,'page_size':30})
        if isinstance(data,dict):
            items=data.get(key)
            if items is None and data:
                items=next(iter(data.values()))
            return items if isinstance(items,list) else []
        return data if isinstance(data,list) else []
    except Exception as e:
        return [{'_error':str(e)}]


def fetch_bundle(inst, token):
    isin=inst['isin']; key=inst['instrument_key']
    paths={
      'profile':f'{BASE}/fundamentals/{isin}/profile','ratios':f'{BASE}/fundamentals/{isin}/key-ratios',
      'income':f'{BASE}/fundamentals/{isin}/income-statement','cash':f'{BASE}/fundamentals/{isin}/cash-flow',
      'balance':f'{BASE}/fundamentals/{isin}/balance-sheet','holding':f'{BASE}/fundamentals/{isin}/share-holdings',
      'competitors':f'{BASE}/fundamentals/{isin}/competitors','actions':f'{BASE}/fundamentals/{isin}/corporate-actions'}
    out={}
    for k,u in paths.items():
        try:
            params={'type':'consolidated'} if k in ('cash','balance') else None
            if k=='income':params={'type':'consolidated','time_period':'yearly'}
            out[k]=api_get(u,token,params)
        except Exception as e:out[k]={'_error':str(e)}
    try:
        q=api_get(f'{BASE3}/market-quote/ltp',token,{'instrument_key':key})
        out['quote']=next(iter(q.values())) if q else {}
    except Exception as e:out['quote']={'_error':str(e)}
    try:
        to=date.today();frm=to-timedelta(days=365*5);enc=quote(key,safe='')
        h=api_get(f'{BASE3}/historical-candle/{enc}/days/1/{to.isoformat()}/{frm.isoformat()}',token)
        candles=(h or {}).get('candles',[])
        out['history']=pd.DataFrame(candles,columns=['Date','Open','High','Low','Close','Volume','OI']) if candles else pd.DataFrame()
        if not out['history'].empty:out['history']['Date']=pd.to_datetime(out['history']['Date'])
    except Exception as e:out['history']=pd.DataFrame();out['history_error']=str(e)
    out['news']=fetch_news(key,token)
    return out


def ratio_map(data):
    if not isinstance(data,list):return {}
    return {str(x.get('name','')).upper():{'company':num(x.get('company_value')),'sector':num(x.get('sector_value'))} for x in data}


def category_history(data,names):
    if not isinstance(data,dict):return []
    rows=data.get('income_statement') or data.get('cash_flow') or data.get('balance_sheet') or []
    for row in rows:
        if str(row.get('category','')).lower() in [n.lower() for n in names]:return row.get('history',[])
    return []


def growth(hist):
    vals=[num(x.get('value')) for x in hist[:3] if num(x.get('value')) is not None]
    if len(vals)>=2 and vals[-1]!=0:
        return (vals[0]/vals[-1])**(1/(len(vals)-1))-1
    return None


def classify_news(item):
    txt=f"{item.get('heading','')} {item.get('summary','')}".lower()
    pos=sum(1 for w in POSITIVE_WORDS if w in txt)
    neg=sum(1 for w in NEGATIVE_WORDS if w in txt)
    if pos>neg:return 'Positive',1
    if neg>pos:return 'Negative',-1
    return 'Neutral',0


def news_summary(news):
    valid=[x for x in news if isinstance(x,dict) and not x.get('_error')]
    sentiments=[classify_news(x)[1] for x in valid]
    net=sum(sentiments)
    pos=sum(1 for s in sentiments if s>0);neg=sum(1 for s in sentiments if s<0)
    impact=max(-8,min(8,net*2))
    label='Positive' if net>1 else 'Negative' if net<-1 else 'Mixed/Neutral'
    return {'count':len(valid),'positive':pos,'negative':neg,'net':net,'impact':impact,'label':label}


def score_and_verdict(ratios,income,cash,news):
    score=50;reasons=[];risks=[]
    pe=ratios.get('P/E',{});roe=ratios.get('ROE',{});roce=ratios.get('ROCE',{})
    if roe.get('company') is not None:
        if roe['company']>=18:score+=12;reasons.append('ROE is strong')
        elif roe['company']<10:score-=10;risks.append('ROE is weak')
    if roce.get('company') is not None:
        if roce['company']>=18:score+=10;reasons.append('ROCE indicates efficient capital use')
        elif roce['company']<10:score-=8;risks.append('ROCE is below a healthy level')
    if pe.get('company') and pe.get('sector'):
        premium=(pe['company']/pe['sector']-1)*100
        if premium<-15:score+=10;reasons.append('P/E is below the sector benchmark')
        elif premium>35:score-=14;risks.append('P/E carries a large sector premium')
        elif premium>15:score-=6;risks.append('Valuation is above the sector benchmark')
    rev=category_history(income,['revenue']);profit=category_history(income,['net profit','profit after tax'])
    rg=growth(rev);pg=growth(profit)
    if rg is not None:
        if rg>.15:score+=8;reasons.append('Revenue growth is healthy')
        elif rg<0:score-=10;risks.append('Revenue is declining')
    if pg is not None:
        if pg>.15:score+=10;reasons.append('Profit growth is healthy')
        elif pg<0:score-=12;risks.append('Profit is declining')
    ocf=category_history(cash,['operating'])
    if ocf and num(ocf[0].get('value')) is not None:
        if num(ocf[0].get('value'))>0:score+=5;reasons.append('Operating cash flow is positive')
        else:score-=8;risks.append('Operating cash flow is negative')
    ns=news_summary(news)
    score+=ns['impact']
    if ns['impact']>=4:reasons.append('Recent news flow is broadly positive')
    elif ns['impact']<=-4:risks.append('Recent news flow is broadly negative')
    score=max(0,min(100,round(score)))
    if score>=72:verdict=('CONSIDER BUYING GRADUALLY','buy','The present fundamentals, valuation and recent news flow are supportive. Use staggered buying and confirm the latest exchange filings.')
    elif score>=52:verdict=('WATCH / WAIT FOR A BETTER ENTRY','wait','The investment case is mixed. Wait for a better price, stronger results or improved current developments.')
    else:verdict=('AVOID FOR NOW','avoid','The available risk–reward is not strong enough at present.')
    return score,verdict,reasons[:6],risks[:6],rg,pg,ns


def timestamp_text(ms):
    try:
        dt=datetime.fromtimestamp(float(ms)/1000,tz=timezone.utc).astimezone()
        return dt.strftime('%d %b %Y, %I:%M %p')
    except Exception:return ''


def show_news(news,summary):
    st.markdown(f"<div class='section-card'><h3>News impact on decision</h3><p><b>{summary['label']}</b> · {summary['count']} articles reviewed · {summary['positive']} positive · {summary['negative']} negative</p><p style='color:#6f7782'>News changes the score by a maximum of ±8 points. It does not override weak financials or an excessive valuation.</p></div>",unsafe_allow_html=True)
    valid=[x for x in news if isinstance(x,dict) and not x.get('_error')]
    if not valid:
        err=next((x.get('_error') for x in news if isinstance(x,dict) and x.get('_error')),None)
        st.info(f'No company-specific news returned for the past seven days. {err or ""}')
        return
    for item in valid[:12]:
        label,_=classify_news(item);cls={'Positive':'pos','Negative':'neg','Neutral':'neu'}[label]
        heading=item.get('heading') or 'Untitled article';summary_txt=item.get('summary') or ''
        link=item.get('url') or item.get('article_link') or item.get('link') or '#'
        published=item.get('published_at') or item.get('published_timestamp') or item.get('timestamp')
        st.markdown(f"<div class='news-card'><div><span class='badge {cls}'>{label}</span></div><div class='news-title'>{heading}</div><div>{summary_txt}</div><div class='news-meta'>{timestamp_text(published)} · <a href='{link}' target='_blank'>Open article</a></div></div>",unsafe_allow_html=True)


def show_stock(inst,b):
    profile=b.get('profile',{});ratios=ratio_map(b.get('ratios'));quote_data=b.get('quote',{}) if isinstance(b.get('quote'),dict) else {}
    score,verdict,reasons,risks,rg,pg,ns=score_and_verdict(ratios,b.get('income',{}),b.get('cash',{}),b.get('news',[]))
    title,kind,explain=verdict
    company=inst.get('short_name') or inst.get('name') or inst.get('trading_symbol')
    st.markdown(f"<div class='hero'><div class='hero-title'>{company}</div><p class='hero-sub'>{inst.get('trading_symbol')} · NSE · Data from Upstox</p></div>",unsafe_allow_html=True)
    st.markdown(f"<div class='verdict {kind}'><div class='verdict-kicker'>CURRENT RESEARCH VERDICT</div><div class='verdict-title'>{title}</div><p>{explain}</p><b>Overall decision score: {score}/100</b> · News: {ns['label']}</div>",unsafe_allow_html=True)

    ltp=num(quote_data.get('last_price'));cp=num(quote_data.get('cp'))
    pe=ratios.get('P/E',{}).get('company');roe=ratios.get('ROE',{}).get('company');roce=ratios.get('ROCE',{}).get('company')
    pb=ratios.get('P/B',{}).get('company');sector_pe=ratios.get('P/E',{}).get('sector')
    change=((ltp/cp-1)*100) if ltp and cp else None
    st.markdown("<div class='kpi-grid'>",unsafe_allow_html=True)
    cols=st.columns(6)
    with cols[0]:kpi('Current price',fmt_price(ltp),fmt_pct(change)+' today' if change is not None else '')
    with cols[1]:kpi('Overall score',f'{score}/100','Includes news impact')
    with cols[2]:kpi('P/E ratio',fmt_ratio(pe),f'Sector {fmt_ratio(sector_pe)}')
    with cols[3]:kpi('P/B ratio',fmt_ratio(pb),'Price vs book value')
    with cols[4]:kpi('ROE',fmt_pct(roe),'Shareholder efficiency')
    with cols[5]:kpi('ROCE',fmt_pct(roce),'Capital efficiency')
    st.markdown('</div>',unsafe_allow_html=True)

    tabs=st.tabs(['Overview','Financials','Valuation','Business','News & Events','Ownership & Risks'])
    with tabs[0]:
        c1,c2=st.columns(2)
        with c1:
            st.markdown("<div class='section-card'><h3>Why it may work</h3>"+''.join(f"<p class='good'>✓ {x}</p>" for x in reasons or ['No strong positive signal detected'])+'</div>',unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='section-card'><h3>What can go wrong</h3>"+''.join(f"<p class='bad'>⚠ {x}</p>" for x in risks or ['No major ratio-based warning detected'])+'</div>',unsafe_allow_html=True)
        summary_rows=[
            ['Should I invest?',title],['Business quality','Review profile and dependencies'],['Growth',fmt_pct(rg*100) if rg is not None else 'N/A'],
            ['Profit growth',fmt_pct(pg*100) if pg is not None else 'N/A'],['Valuation',f'P/E {fmt_ratio(pe)} vs sector {fmt_ratio(sector_pe)}'],
            ['Recent news',f"{ns['label']} ({ns['positive']} positive / {ns['negative']} negative)"]]
        st.dataframe(pd.DataFrame(summary_rows,columns=['5-minute question','Answer']),width='stretch',hide_index=True)
    with tabs[1]:
        inc=b.get('income',{});rev=category_history(inc,['revenue']);prof=category_history(inc,['net profit','profit after tax'])
        data=[]
        for label,hist in [('Revenue',rev),('Net profit',prof)]:
            for x in hist:data.append({'Period':x.get('period'),'Metric':label,'Value':num(x.get('value'))})
        if data:
            fig=px.bar(pd.DataFrame(data),x='Period',y='Value',color='Metric',barmode='group',title='Revenue and profit trend')
            fig.update_layout(template='plotly_white',legend_title_text='',margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig,width='stretch')
        else:st.info('Financial statement history was not returned for this company.')
        hist=b.get('history')
        if isinstance(hist,pd.DataFrame) and not hist.empty:
            fig=px.line(hist.sort_values('Date'),x='Date',y='Close',title='Five-year share-price trend')
            fig.update_layout(template='plotly_white',margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig,width='stretch')
    with tabs[2]:
        rows=[]
        for n in ['P/E','P/B','ROE','ROCE','EV/EBITDA']:
            v=ratios.get(n,{})
            rows.append({'Parameter':n,'Company':v.get('company'),'Sector benchmark':v.get('sector'),'How to read':'Lower is usually better' if n in ('P/E','P/B','EV/EBITDA') else 'Higher is usually better'})
        st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True)
        if pe and sector_pe:
            premium=(pe/sector_pe-1)*100
            text='discount' if premium<0 else 'premium'
            st.markdown(f"<div class='section-card'><h3>Valuation conclusion</h3><p>The company trades at a <b>{abs(premium):.1f}% {text}</b> to its sector P/E benchmark. This comparison is useful, but fair value also depends on growth, margins, debt and business quality.</p></div>",unsafe_allow_html=True)
    with tabs[3]:
        desc=profile.get('company_profile') if isinstance(profile,dict) else None
        st.markdown(f"<div class='section-card'><h3>What the company does</h3><p>{desc or 'Business description unavailable from Upstox.'}</p></div>",unsafe_allow_html=True)
        st.markdown("<div class='section-card'><h3>Business dependency checklist</h3><p>Before investing, verify what the company mainly depends on: top customers, product segment, geography, government orders, commodity prices, regulation, export demand, interest rates and working capital.</p><p><b>Important:</b> exact customer and segment concentration must be taken from the latest annual report and exchange filings.</p></div>",unsafe_allow_html=True)
        comps=b.get('competitors',[])
        if isinstance(comps,list) and comps:
            st.subheader('Competitors')
            st.dataframe(pd.DataFrame([{'Company':x.get('company_name') or x.get('short_name') or x.get('instrument_key'),'Sector':x.get('sector')} for x in comps]),width='stretch',hide_index=True)
    with tabs[4]:
        show_news(b.get('news',[]),ns)
        actions=b.get('actions',[])
        if isinstance(actions,list) and actions:
            st.subheader('Corporate actions')
            st.dataframe(pd.DataFrame(actions),width='stretch',hide_index=True)
    with tabs[5]:
        hold=b.get('holding',[]);rows=[]
        if isinstance(hold,list):
            for cat in hold:
                for h in cat.get('history',[]):rows.append({'Category':cat.get('category'),'Period':h.get('period'),'Holding %':h.get('value')})
        if rows:
            hdf=pd.DataFrame(rows)
            fig=px.line(hdf,x='Period',y='Holding %',color='Category',markers=True,title='Shareholding trend')
            fig.update_layout(template='plotly_white',margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig,width='stretch')
        else:st.info('Shareholding data unavailable.')
        st.warning('Also verify auditor remarks, promoter pledging, related-party transactions, litigation, contingent liabilities and the latest exchange announcements.')


def list_ipos(token,status,issue_type):
    return api_get(f'{BASE}/ipos',token,{'status':status,'issue_type':issue_type,'page_number':1,'records':30})

st.markdown("<div class='hero'><div class='hero-title'>EquityLens AI</div><p class='hero-sub'>Stocks, IPOs, fundamentals, valuation and current news — in one five-minute dashboard.</p></div>",unsafe_allow_html=True)
token=get_token()
if not token:
    st.error('Upstox access token is not configured.')
    st.code('UPSTOX_ACCESS_TOKEN = "paste_your_token_here"',language='toml')
    st.stop()
mode=st.radio('Research mode',['Listed share','IPO — Mainboard / SME'],horizontal=True)
if mode=='Listed share':
    c1,c2=st.columns([4,1])
    q=c1.text_input('Search NSE symbol or company name',value='RELIANCE')
    run=c2.button('Analyse',type='primary',width='stretch')
    if run:
        try:
            matches=find_instrument(q.strip(),token)
            if not matches:st.error('No NSE equity found. Try the exact trading symbol.');st.stop()
            labels=[f"{x.get('trading_symbol')} — {x.get('name')}" for x in matches]
            idx=0
            if len(matches)>1:idx=st.selectbox('Select the correct company',range(len(matches)),format_func=lambda i:labels[i])
            inst=matches[idx]
            with st.spinner('Fetching fundamentals, valuation, price history and recent news…'):
                bundle=fetch_bundle(inst,token)
            show_stock(inst,bundle)
        except Exception as e:st.error(str(e))
else:
    c1,c2=st.columns(2)
    status=c1.selectbox('IPO status',['open','upcoming','closed','listed'])
    issue=c2.selectbox('Issue type',[('regular','Mainboard'),('sme','SME')],format_func=lambda x:x[1])[0]
    if st.button('Load IPOs',type='primary',width='stretch'):
        try:
            data=list_ipos(token,status,issue);items=data.get('ipos',data if isinstance(data,list) else []) if data else []
            if not items:st.info('No IPOs found for this filter.');st.stop()
            st.dataframe(pd.DataFrame(items),width='stretch',hide_index=True)
            st.warning('IPO decisions also require RHP valuation, subscription trend, use of proceeds, promoter checks and market conditions. No model can guarantee listing gains.')
        except Exception as e:st.error(str(e))
