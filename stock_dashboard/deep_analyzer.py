# deep_analyzer.py - 개별 종목 Deep Dive 분석 대시보드
# 실행: python -m streamlit run deep_analyzer.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import analysis_engine as ae
import importlib
importlib.reload(ae)  # 핫 리로드 시 analysis_engine 변경사항 즉시 반영
import base64

st.set_page_config(page_title="Deep Dive Analyzer", page_icon="🔬", layout="wide")

# === CSS 스타일 ===
st.markdown("""<style>
.stApp{background-color:#0D1117}
div[data-testid="stMetric"]{background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px}
div[data-testid="stMetric"] label{color:#8B949E!important;font-size:.75rem!important;text-transform:uppercase}
div[data-testid="stMetric"] div[data-testid="stMetricValue"]{color:#E6EDF3!important;font-size:1.4rem!important}
h1,h2,h3{color:#C9D1D9!important} hr{border-color:#30363D!important}
section[data-testid="stSidebar"]{background:#0D1117;border-right:1px solid #30363D}
.red-box{background:linear-gradient(135deg,#8B0000,#2D0A0A);border:1px solid #FF4444;border-radius:10px;padding:20px;margin:16px 0}
.red-box h3{color:#FF6B6B!important;margin:0 0 8px 0} .red-box p{color:#FFD0D0;margin:0;font-size:.9rem;line-height:1.6}
.score-card{background:#161B22;border:1px solid #30363D;border-radius:8px;padding:16px;margin:8px 0}
.tag{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.7rem;font-weight:600;margin:2px}
.tag-green{background:#1a4d2e;color:#4ade80} .tag-red{background:#4d1a1a;color:#f87171}
.tag-blue{background:#1a2d4d;color:#60a5fa} .tag-orange{background:#4d3a1a;color:#fbbf24}
.tag-purple{background:#2d1a4d;color:#c084fc}
.swot-card{border-radius:10px;padding:16px;margin:8px 0;min-height:200px}
.swot-s{background:#0a2e1a;border:1px solid #22c55e} .swot-w{background:#2e0a0a;border:1px solid #ef4444}
.swot-o{background:#0a1a2e;border:1px solid #3b82f6} .swot-t{background:#2e1a0a;border:1px solid #f59e0b}
.bull-card{background:#0a2e1a;border:2px solid #22c55e;border-radius:12px;padding:20px;text-align:center}
.base-card{background:#2e2a0a;border:2px solid #f59e0b;border-radius:12px;padding:20px;text-align:center}
.bear-card{background:#2e0a0a;border:2px solid #ef4444;border-radius:12px;padding:20px;text-align:center}
.verdict-box{background:#161B22;border:2px solid #FF6B00;border-radius:12px;padding:24px;margin:16px 0}
.metric-bar{background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 16px;text-align:center}
</style>""", unsafe_allow_html=True)

# === 관심종목(Watchlist) 파일 I/O 헬퍼 ===
import json
import os

WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return ["RKLB", "TSLA", "NVDA", "AAPL"]
    return ["RKLB", "TSLA", "NVDA", "AAPL"]

def save_watchlist(watchlist):
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.sidebar.error(f"관심종목 저장 실패: {e}")

if 'watchlist' not in st.session_state:
    st.session_state['watchlist'] = load_watchlist()

# 관심종목 핫스왑 분석 함수
def analyze_selected_ticker(t):
    st.session_state['ticker'] = t
    st.session_state['watchlist_selected_ticker'] = t  # Rerun 시 인풋 연동을 위해 임시 저장
    with st.spinner(f"◈ {t} 관심종목 분석 개시..."):
        # run_deep_analysis를 수동 구동하여 즉시 결과 갱신
        result = ae.run_deep_analysis(t, st.session_state.get('av_api_key', ''))
        if result:
            st.session_state['data'] = result
            st.rerun()

# === 사이드바 ===
st.sidebar.markdown("### 🔬 Deep Dive Analyzer")

# 핫링크 선택된 종목이 있을 경우 입력창의 기본값을 해당 티커로 우회
default_ticker = st.session_state.get('watchlist_selected_ticker', "RKLB")
if 'watchlist_selected_ticker' in st.session_state:
    # 1회성 소모 처리로 Rerun 후에는 유지
    pass

ticker_input = st.sidebar.text_input("종목 티커 입력", value=default_ticker, max_chars=10).upper().strip()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ API 설정 (어닝 팩트체크용)")
av_api_key = st.sidebar.text_input("Alpha Vantage API Key", value=st.session_state.get('av_api_key', ''), type="password", help="무료 발급: alphavantage.co (어닝 데이터 100% 팩트 렌더링용)")
if av_api_key:
    st.session_state['av_api_key'] = av_api_key

run_btn = st.sidebar.button("🚀 분석 실행", use_container_width=True)

# 💡 티커 입력값 변경 감지 또는 분석 실행 버튼 클릭 시 즉시 분석 개시
should_run = False
if run_btn:
    should_run = True
elif ticker_input and st.session_state.get('ticker') != ticker_input:
    should_run = True

if should_run:
    with st.spinner(f"◈ {ticker_input} 종합 분석 중... (약 10~20초 소요)"):
        result = ae.run_deep_analysis(ticker_input, av_api_key)
        if result:
            st.session_state['data'] = result
            st.session_state['ticker'] = ticker_input
        else:
            st.sidebar.error("존재하지 않는 티커이거나 데이터를 불러올 수 없습니다.")

# === 사이드바 관심종목(Watchlist) 센터 (좌측 끝 배치) ===
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 WATCHLIST (관심종목)")

# 관심종목 추가 입력창 (컴팩트하게 한 행에 배치)
wl_col1, wl_col2 = st.sidebar.columns([3, 1.2])
with wl_col1:
    new_ticker = st.text_input("➕ 추가 티커", placeholder="티커", key="watchlist_add_input", label_visibility="collapsed", max_chars=10).upper().strip()
with wl_col2:
    save_btn = st.button("저장", use_container_width=True, key="watchlist_save_btn")
    if save_btn:
        if new_ticker:
            if new_ticker not in st.session_state['watchlist']:
                st.session_state['watchlist'].append(new_ticker)
                save_watchlist(st.session_state['watchlist'])
                st.toast(f"✅ {new_ticker} 관심종목 추가 완료!")
                st.rerun()
            else:
                st.warning("이미 등록된 티커입니다.")
        else:
            st.error("티커 입력")

# 관심종목 세로 리스트
for t in st.session_state['watchlist']:
    btn_col, del_col = st.sidebar.columns([3, 1])
    with btn_col:
        # 원클릭 실시간 포트폴리오 퀀트 분석 핫링크
        if st.button(f"🎯 {t}", key=f"wl_click_{t}", use_container_width=True):
            analyze_selected_ticker(t)
    with del_col:
        # 삭제 버튼
        if st.button("🗑️", key=f"wl_del_{t}", use_container_width=True, help=f"{t} 관심종목 삭제"):
            st.session_state['watchlist'].remove(t)
            save_watchlist(st.session_state['watchlist'])
            st.toast(f"🗑️ {t} 삭제 완료!")
            st.rerun()

if 'data' not in st.session_state:
    st.markdown("## 🔬 Deep Dive Stock Analyzer")
    st.markdown("좌측 사이드바에서 **종목 티커**를 입력하고 엔터를 치거나 **분석 실행** 버튼을 누르세요.")
    st.stop()

data = st.session_state.get('data')
if not data:
    st.error("분석 데이터를 불러올 수 없습니다. 티커를 확인해주세요.")
    st.stop()

ov = data['overview']
scores = data['scores']
grade = data['grade']
total_score = data['total_score']
entry_score = data.get('entry_score', 50)
momentum = data['momentum']
targets = data['targets']
swot = data['swot']
news = data['news']
analyst = data['analyst']
verdict = data['verdict']
bull_case = data['bull_case']
bear_case = data['bear_case']
financials = data['financials']
earnings = data.get('earnings', [])
ticker = st.session_state.get('ticker', '')

# === 포맷 헬퍼 ===
def fmt_mcap(v):
    if not v: return "N/A"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9: return f"${v/1e9:.1f}B"
    if v >= 1e6: return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"

def fmt_pct(v):
    if v is None: return "N/A"
    return f"{v*100:.1f}%"

def pct_color(v):
    if v is None: return "#8B949E"
    return "#4ade80" if v > 0 else "#f87171" if v < 0 else "#8B949E"

# 글로벌 기업 국문명 & 핵심 비즈니스 정밀 사전 (한글 이중병기용)
KOREAN_COMPANY_DICTIONARY = {
    'TSLA': {
        'name_kr': '테슬라',
        'summary_kr': '세계 최대의 순수 전기차(EV) 제조업체이자 자율주행 FSD 소프트웨어, 에너지 저장장치(ESS), 휴머노이드 로봇(옵티머스)을 개발하는 종합 AI 및 에너지 기업입니다.'
    },
    'NVDA': {
        'name_kr': '엔비디아',
        'summary_kr': '전 세계 AI 가속기 및 GPU(그래픽 처리 장치) 시장의 절대적인 지배자이며, 독점적인 소프트웨어 플랫폼 CUDA 생태계를 통해 글로벌 인공지능 인프라 혁신을 주도하고 있습니다.'
    },
    'AAPL': {
        'name_kr': '애플',
        'summary_kr': '아이폰, 아이패드, 맥 등 독보적인 하드웨어 라인업과 iOS 생태계 서비스를 기반으로 하는 글로벌 시가총액 최상위의 전자기기 및 플랫폼 기업입니다.'
    },
    'MSFT': {
        'name_kr': '마이크로소프트',
        'summary_kr': '클라우드 플랫폼 Azure(애저), Windows 운영체제, Office 생산성 소프트웨어의 글로벌 거인이며, OpenAI와의 긴밀한 동맹을 통해 생성형 AI 비즈니스 솔루션을 강력히 이끌고 있습니다.'
    },
    'AMZN': {
        'name_kr': '아마존',
        'summary_kr': '세계 최대의 글로벌 전자상거래 플랫폼이자 압도적 점유율 1위의 클라우드 서비스인 AWS(아마존 웹 서비스)를 운영하고 있으며, 물류 인프라 및 AI 클라우드 혁신에 주력하는 기업입니다.'
    },
    'RKLB': {
        'name_kr': '로켓 랩',
        'summary_kr': '미국 우주항공 부품 제조 및 소형 위성 발사 서비스(일렉트론 로켓, 뉴트론 대형 로켓) 분야의 글로벌 혁신 주자로, 민간 및 우주 방산 우주선 솔루션을 제공하는 2대 민간 우주 기업입니다.'
    },
    'COHR': {
        'name_kr': '코히런트',
        'summary_kr': 'AI 데이터센터용 차세대 광통신 모듈(800G/1.6T 광트랜시버), 고출력 산업용 레이저 장비, 화합물 반도체(SiC) 소재 등을 생산하는 글로벌 1위 광학 및 엔지니어링 신소재 전문 기업입니다.'
    },
    'GOOGL': {
        'name_kr': '알파벳 (구글)',
        'summary_kr': '글로벌 1위 인터넷 검색엔진 구글, 유튜브 플랫폼, 크롬 브라우저, 안드로이드 운영체제를 보유한 거대 플랫폼 기업으로, 제미나이(Gemini) 거대언어모델 기반의 미래형 AI 검색 및 클라우드 비즈니스를 선도하고 있습니다.'
    },
    'GOOG': {
        'name_kr': '알파벳 (구글)',
        'summary_kr': '글로벌 1위 인터넷 검색엔진 구글, 유튜브 플랫폼, 크롬 브라우저, 안드로이드 운영체제를 보유한 거대 플랫폼 기업으로, 제미나이(Gemini) 거대언어모델 기반의 미래형 AI 검색 및 클라우드 비즈니스를 선도하고 있습니다.'
    },
    'META': {
        'name_kr': '메타 플랫폼스',
        'summary_kr': '페이스북, 인스타그램, 왓츠앱 등 글로벌 최대 소셜네트워크서비스(SNS)를 운영하며, 메타버스 하드웨어 Quest와 오픈소스 LLM인 Llama(라마) 생태계를 활발히 구축하고 있는 AI 소셜 미디어 리더입니다.'
    },
    'NFLX': {
        'name_kr': '넷플릭스',
        'summary_kr': '전 세계 2억 명 이상의 유료 구독자를 보유한 글로벌 1위 온라인 동영상 서비스(OTT) 및 독창적 미디어 오리지널 콘텐츠 제작 미디어 플랫폼 대기업입니다.'
    },
    'LMT': {
        'name_kr': '록히드 마틴',
        'summary_kr': 'F-35 스텔스 전투기를 생산하는 전 세계 압도적 1위의 항공우주 및 첨단 우주 국방 방위산업 전문 대기업입니다.'
    },
    'PLTR': {
        'name_kr': '팔란티어 테크놀로지스',
        'summary_kr': '미국 정보기관 및 군 정보망을 위한 고도화된 빅데이터 분석 플랫폼 Gotham(고담)과 민간 기업 비즈니스 지형 의사결정을 돕는 Foundry(파운드리), 그리고 최신 AIP(AI 플랫폼) 솔루션을 공급하는 퀀트 정보 기술 전문 기업입니다.'
    },
    'AVGO': {
        'name_kr': '브로드컴',
        'summary_kr': '네트워크 스위치 칩, 브로드밴드 솔루션, 모바일 핵심 무선주파수 부품 등을 제조하는 유무선 하이브리드 반도체 및 인프라 소프트웨어의 글로벌 최강 강자입니다.'
    },
    'SMCI': {
        'name_kr': '슈퍼 마이크로 컴퓨터',
        'summary_kr': '고출력 엔비디아 GPU 가속 서버 및 수냉식 랙(Rack) 솔루션을 신속히 제작 및 통합하여 대규모 AI 데이터센터에 즉각 공급하는 최고의 AI 서버 인프라 설계 및 구축 전문 회사입니다.'
    }
}

def generate_korean_fallback_summary(ticker, name_eng, sector, industry, summary_eng):
    """미등록 생소한 종목에 대한 실시간 한글 비즈니스 지능형 요약 생성기"""
    if not summary_eng:
        return f"{name_eng}은(는) {sector} 섹터의 {industry} 산업군에 위치한 글로벌 상장 기업입니다."
    
    keywords_map = {
        'develops': '개발', 'manufactures': '제조', 'designs': '설계', 'markets': '마케팅/유통',
        'semiconductor': '반도체', 'aerospace': '항공우주', 'automotive': '자동차', 'energy': '에너지',
        'software': '소프트웨어', 'hardware': '하드웨어', 'biotechnology': '바이오테크', 'medical': '의료',
        'financial': '금융', 'defense': '국방/방산', 'cloud': '클라우드', 'satellite': '인공위성',
        'communications': '통신', 'materials': '엔지니어링 소재', 'laser': '레이저 장비',
        'optical': '광학 광통신', 'infrastructure': '인프라', 'services': '서비스'
    }
    
    found_activities = []
    found_sectors = []
    
    summary_lower = summary_eng.lower()
    for eng_k, kor_k in keywords_map.items():
        if eng_k in summary_lower:
            if eng_k in ['develops', 'manufactures', 'designs', 'markets', 'services']:
                found_activities.append(kor_k)
            else:
                found_sectors.append(kor_k)
                
    act_str = " 및 ".join(found_activities) if found_activities else "비즈니스"
    sec_str = "/".join(found_sectors) if found_sectors else f"{sector} 및 {industry}"
    
    return f"본 기업은 글로벌 {sec_str} 시장을 타겟으로 혁신적인 솔루션 및 제품을 전문적으로 {act_str}하는 기업입니다."

# ================================================================
# 헤더 영역
# ================================================================
ex_label = ov.get('exchange_name', ov.get('exchange', 'N/A'))
cap_label = ov.get('cap_size', 'N/A')

hdr_left, hdr_right = st.columns([3, 1])
with hdr_left:
    tags = f"<span class='tag tag-blue' style='background:#1f6feb;color:#fff;font-weight:bold'>{ex_label}</span>"
    if cap_label != "N/A":
        tags += f" <span class='tag tag-green' style='background:#238636;color:#fff;font-weight:bold'>{cap_label}</span>"
    tags += f" <span class='tag tag-blue'>{ticker}</span>"
    if ov['sector'] != 'N/A':
        tags += f" <span class='tag tag-purple'>{ov['sector']}</span>"
    if ov['industry'] != 'N/A':
        tags += f" <span class='tag tag-orange'>{ov['industry']}</span>"
    st.markdown(f"{tags}", unsafe_allow_html=True)
    
    ticker_upper = ticker.upper()
    dict_info = KOREAN_COMPANY_DICTIONARY.get(ticker_upper, None)
    if dict_info:
        name_kr = dict_info['name_kr']
        summary_kr = dict_info['summary_kr']
    else:
        name_kr = ov['name']
        summary_kr = generate_korean_fallback_summary(ticker_upper, ov['name'], ov['sector'], ov['industry'], ov.get('summary',''))
        
    st.markdown(f"<h1 style='font-size:2.6rem;margin:0;color:#E6EDF3!important;line-height:1.2'>{ov['name']} <span style='font-size:1.6rem;color:#8B949E;font-weight:normal'>({name_kr})</span></h1>", unsafe_allow_html=True)
    desc_short = ov.get('summary','')[:200] + '...' if len(ov.get('summary','')) > 200 else ov.get('summary','')
    st.markdown(f"""
    <div style='margin-top:6px;margin-bottom:12px'>
        <p style='color:#8B949E;font-size:0.82rem;margin-bottom:4px;line-height:1.5'>{desc_short}</p>
        <p style='color:#4ade80;font-size:0.88rem;font-weight:500;line-height:1.5;background:#161B22;border-left:3px solid #238636;padding:6px 12px;border-radius:0 4px 4px 0'>💡 <b>[국문 요약]</b> {summary_kr}</p>
    </div>
    """, unsafe_allow_html=True)
with hdr_right:
    pc = pct_color(momentum.get('1d',0)/100 if momentum.get('1d') else None)
    chg = momentum.get('1d', 0)
    st.markdown(f"""
    <div style='text-align:right;padding:16px'>
        <p style='color:#8B949E;margin:0;font-size:.8rem'>현재주가 ({datetime.now().strftime('%Y.%m.%d')})</p>
        <h1 style='font-size:3rem;margin:0;color:#E6EDF3!important'>${ov['current_price']}</h1>
        <p style='color:{pc};font-size:1.1rem;margin:0'>일간 {chg:+.2f}%</p>
    </div>""", unsafe_allow_html=True)

tech_result = data.get('tech_result', {})

# === 주요 지표 바 (3열 2행) ===
metrics = [
    ("52주 최저", f"${ov['low_52w']}"), ("52주 최고", f"${ov['high_52w']}"),
    ("시가총액", fmt_mcap(ov['market_cap'])),
    ("직원수", f"{ov['employees']:,}명" if ov['employees'] else "N/A"),
    ("P/E 비율", f"{ov['pe_ratio']:.1f}x <span style='font-size:0.8rem;color:{ov.get('pe_color', '#8B949E')}'>({ov.get('pe_eval', 'N/A')})</span>" if ov['pe_ratio'] else "산정 불가"),
    ("P/S 비율", f"{ov['ps_ratio']:.1f}x <span style='font-size:0.8rem;color:{ov.get('ps_color', '#8B949E')}'>({ov.get('ps_eval', 'N/A')})</span>" if ov['ps_ratio'] else "산정 불가"),
]

row_cols = st.columns(3)
for j, (label, val) in enumerate(metrics[:3]):
    row_cols[j].markdown(f"<div class='metric-bar' style='margin-bottom:10px'><small style='color:#8B949E'>{label}</small><br><b style='color:#E6EDF3'>{val}</b></div>", unsafe_allow_html=True)

row_cols2 = st.columns(3)
for j, (label, val) in enumerate(metrics[3:]):
    row_cols2[j].markdown(f"<div class='metric-bar'><small style='color:#8B949E'>{label}</small><br><b style='color:#E6EDF3'>{val}</b></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================================================================
# 7:3 대단위 퀀트 레이아웃 개편
# ================================================================
col_main, col_side = st.columns([7.2, 2.8])

# --- 1) 좌측 메인 뷰 (70%) ---
with col_main:
    # 4대 기술적 신호 타이밍 평가
    st.markdown("#### 🔬 차트 4가지 신호 타이밍 평가")
    t_cols = st.columns(4)
    signal_icons = {'추세': '📈', '모멘텀': '🚀', '변동성': '⚡', '수급': '🔋'}
    for idx, (sig_name, sig_score) in enumerate(tech_result['scores'].items()):
        sig_desc = tech_result['details'].get(sig_name, '')
        stars = "★" * int(sig_score) + "☆" * (5 - int(sig_score))
        t_cols[idx].markdown(f"""
        <div style='background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;text-align:center'>
            <span style='font-size:1.5rem'>{signal_icons.get(sig_name, '📊')}</span>
            <p style='color:#C9D1D9;margin:4px 0 2px 0;font-size:0.9rem;font-weight:bold'>{sig_name}</p>
            <p style='color:#FFD700;margin:0;font-size:0.85rem'>{stars}</p>
            <small style='color:#8B949E;font-size:0.72rem'>{sig_desc}</small>
        </div>
        """, unsafe_allow_html=True)

    # 핵심 관찰 자동 코멘트 박스
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background:#1f1515;border:1px solid #FF4444;border-radius:10px;padding:16px;margin-bottom:16px'>
        <h4 style='color:#FF6B6B!important;margin:0 0 8px 0;font-size:1.15rem'>📝 퀀트 분석 핵심 관찰 코멘트</h4>
        <p style='color:#FFD0D0;margin:0;font-size:0.95rem;line-height:1.6'>
            <b>[기술적 신호]</b> {tech_result['timing_desc']} (종합 타이밍 점수 {tech_result['timing_score']}점) / 현재 RSI는 {tech_result['rsi']}로 {tech_result['details']['모멘텀']} 상태입니다.<br>
            <b>[판단 및 가이드]</b> {verdict['desc']}<br>
            <b>[진입 가이드]</b> {verdict['buy_zone']} 내에서 분할 매수 진입을 고려하십시오. 🚨 {verdict['stop_loss']}로 철저한 리스크 관리가 필요합니다.<br>
            <b>[보유자 가이드]</b> {verdict.get('holder_guide', '기존 보유자는 분석 엔진 피드백 보유 권장.')}
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- 2) 우측 사이드 스코어보드 뷰 (30%) ---
with col_side:
    # 2x2 듀얼 계기판 스코어보드 개편
    entry_desc = "적극 매수 (Strong)" if entry_score >= 80 else "매수 유효 (Buy)" if entry_score >= 70 else "조정 관망 (Hold)" if entry_score >= 50 else "위험 보류 (Avoid)"
    entry_border = "#FF6B00" if entry_score >= 70 else "#f87171"
    entry_color = "#ff7b72" if entry_score < 70 else "#FFD700"

    st.markdown(f"""
    <div style='display:flex;gap:10px;margin-bottom:12px;'>
        <!-- 좌측: TotalScore -->
        <div style='flex:1;text-align:center;padding:12px 8px;background:#161B22;border-radius:10px;border:2px solid #1f6feb;'>
            <p style='color:#8B949E;margin:0;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.5px;font-weight:bold'>TOTAL SCORE (우량)</p>
            <h1 style='color:#58a6ff!important;font-size:2.0rem;margin:6px 0;font-family:"Outfit", sans-serif'>{total_score}<span style='font-size:0.9rem;color:#8B949E'>/100</span></h1>
            <div style='background:#1f6feb;color:#fff;font-weight:bold;padding:1px 8px;border-radius:10px;display:inline-block;font-size:0.68rem;margin-bottom:4px'>
                {grade} 등급
            </div>
            <p style='color:#8B949E;margin:0;font-size:0.62rem;line-height:1.2'>중장기 가치/안정성</p>
        </div>
        <!-- 우측: EntryScore -->
        <div style='flex:1;text-align:center;padding:12px 8px;background:#161B22;border-radius:10px;border:2px solid {entry_border};'>
            <p style='color:#8B949E;margin:0;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.5px;font-weight:bold'>ENTRY SCORE (타점)</p>
            <h1 style='color:{entry_color}!important;font-size:2.0rem;margin:6px 0;font-family:"Outfit", sans-serif'>{entry_score}<span style='font-size:0.9rem;color:#8B949E'>/100</span></h1>
            <div style='background:#FF6B00;color:#fff;font-weight:bold;padding:1px 8px;border-radius:10px;display:inline-block;font-size:0.68rem;margin-bottom:4px'>
                {entry_desc}
            </div>
            <p style='color:#8B949E;margin:0;font-size:0.62rem;line-height:1.2'>단기 진입 안전마진</p>
        </div>
    </div>
    
    <!-- 2차원 매트릭스 진단 지표 배너 -->
    <div style='background:#1f1910;border:1px solid #fbbf24;border-radius:10px;padding:12px;margin-bottom:12px;text-align:center'>
        <span style='font-size:0.75rem;color:#fbbf24;font-weight:bold'>🎯 QUANT PORTFOLIO MATRIX</span>
        <h4 style='color:#E6EDF3;margin:4px 0;font-size:0.92rem'>{verdict["tone"]}</h4>
        <p style='color:#C9D1D9;margin:0 0 6px 0;font-size:0.72rem;line-height:1.4'>{verdict["desc"]}</p>
        <hr style='margin:6px 0;border-color:#3e3016!important'>
        <p style='color:#ffd700;margin:0;font-size:0.7rem;line-height:1.4;text-align:left'><b>[보유주주]</b> {verdict.get("holder_guide", "")}</p>
    </div>
    """, unsafe_allow_html=True)

    # 목표가 및 핵심 지표 요약
    upside = 0
    if ov.get('avg_target') and ov['avg_target'] > ov['current_price']:
        upside = ((ov['avg_target'] - ov['current_price']) / ov['current_price']) * 100
        
    conviction = "HIGH" if total_score >= 80 else "MEDIUM" if total_score >= 65 else "LOW"
    conviction_kr = "강력 확신" if conviction == "HIGH" else "일반 확신" if conviction == "MEDIUM" else "보수 관망"
    conv_color = "#4ade80" if conviction == "HIGH" else "#fbbf24" if conviction == "MEDIUM" else "#f87171"
    
    st.markdown(f"""
    <div style='background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin-bottom:12px'>
        <table style='width:100%;font-size:0.8rem;color:#C9D1D9'>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:5px 0;color:#8B949E'>현재 주가</td>
                <td style='padding:5px 0;text-align:right;font-weight:bold'>${ov['current_price']}</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:5px 0;color:#8B949E'>평균 목표가</td>
                <td style='padding:5px 0;text-align:right;font-weight:bold'>${ov['avg_target'] or 'N/A'} ({upside:+.1f}%)</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:5px 0;color:#8B949E'>상대강도 RSI</td>
                <td style='padding:5px 0;text-align:right;font-weight:bold;color:#c084fc'>{tech_result['rsi']}</td>
            </tr>
            <tr>
                <td style='padding:5px 0;color:#8B949E'>퀀트 확신도(Conviction)</td>
                <td style='padding:5px 0;text-align:right;font-weight:bold;color:{conv_color}'>{conviction_kr}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # 진입 타이밍 타점 (매수/손절/익절)
    price = ov['current_price']
    atr = tech_result['atr']
    tp = tech_result.get('tp_levels', {})
    
    st.markdown(f"""
    <div style='background:#1f1910;border:1px solid #fbbf24;border-radius:8px;padding:12px;margin-bottom:12px'>
        <h5 style='color:#fbbf24;margin:0 0 8px 0;font-size:0.85rem'>🎯 기술적 정밀 타점 가이드</h5>
        <table style='width:100%;font-size:0.8rem;color:#C9D1D9;border-collapse:collapse'>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:6px 0;color:#8B949E;font-weight:bold'>일간 VWAP 기준가</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#60a5fa'>${tech_result['vwap']:.2f}</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:6px 0;color:#8B949E;font-weight:bold'>주간 EM 상단 (1σ)</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#f87171'>${tp.get('em_upper', 0.0):.2f}</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:6px 0;color:#8B949E;font-weight:bold'>주간 EM 하단 (1σ)</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#4ade80'>${tp.get('em_lower', 0.0):.2f}</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:6px 0;color:#8B949E;font-weight:bold'>매수 적정구간</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#4ade80'>{tp.get('buy_zone', f"${price*0.95:.1f}~${price:.1f}")}</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D;background-color:#1c1313'>
                <td style='padding:6px 0;color:#f87171;font-weight:bold'>기술적 손절가</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#f87171'>${tp.get('stop_loss', round(price*0.85, 2)):.2f}</td>
            </tr>
            <tr style='border-bottom:1px solid #30363D'>
                <td style='padding:6px 0;color:#8B949E;font-weight:bold'>1차 목표 익절가</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#4ade80'>${tp.get('target_1', round(price + atr*1.5, 2)):.2f}</td>
            </tr>
            <tr>
                <td style='padding:6px 0;color:#8B949E;font-weight:bold'>2차 목표 익절가</td>
                <td style='padding:6px 0;text-align:right;font-weight:bold;color:#22c55e'>${tp.get('target_2', round(price + atr*3.0, 2)):.2f}</td>
            </tr>
        </table>
        <div style='margin-top:8px;font-size:0.72rem;color:#8B949E;line-height:1.4;border-top:1px solid #30363D;padding-top:6px'>
            📊 <b>Expected Move:</b> ±${tp.get('em_move', 0.0):.2f} ({tp.get('em_expiry', 'N/A')} 만기)<br>
            💡 <b>매수 근거:</b> {tp.get('buy_reason', '스윙 로우 지지 영역')}<br>
            🚨 <b>손절 근거:</b> {tp.get('stop_reason', 'ATR 변동성 기준선 붕괴')}<br>
            🎯 <b>1차 익절:</b> {tp.get('t1_reason', '피보나치 38.2% & 저항선 부근')}<br>
            🚀 <b>2차 익절:</b> {tp.get('t2_reason', '피보나치 61.8% 돌파 영역')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 하단 재무 4칸 핵심 타일 (yfinance info 실패 시 financials 직접 연산 극강 폴백 탑재)
    import math
    def is_valid_num(v):
        if v is None: return False
        try:
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                return False
            return True
        except:
            return False

    roe = ov.get('roe')
    if not is_valid_num(roe) or roe == 0:
        try:
            a_inc = financials.get('a_income')
            a_bal = financials.get('a_balance')
            if a_inc is not None and not a_inc.empty and a_bal is not None and not a_bal.empty:
                net_income = None
                for idx in ['Net Income', 'NetIncome', 'Net Income Common Stockholders']:
                    if idx in a_inc.index:
                        val = a_inc.loc[idx].iloc[0]
                        if is_valid_num(val):
                            net_income = float(val)
                        break
                total_equity = None
                for idx in ["Stockholders' Equity", "Total Stockholders' Equity", "Total Equity", "Total Stockholder Equity"]:
                    if idx in a_bal.index:
                        val = a_bal.loc[idx].iloc[0]
                        if is_valid_num(val):
                            total_equity = float(val)
                        break
                if net_income is not None and total_equity is not None and total_equity > 0:
                    roe = net_income / total_equity
        except:
            roe = 0
    if not is_valid_num(roe): roe = 0

    eps_growth = ov.get('earnings_growth')
    if not is_valid_num(eps_growth) or eps_growth == 0:
        try:
            a_inc = financials.get('a_income')
            if a_inc is not None and not a_inc.empty:
                eps_row = None
                for idx in ['Basic EPS', 'Diluted EPS', 'BasicEPS', 'DilutedEPS']:
                    if idx in a_inc.index:
                        eps_row = a_inc.loc[idx]
                        break
                if eps_row is not None and len(eps_row) >= 2:
                    current_eps = eps_row.iloc[0]
                    prev_eps = eps_row.iloc[1]
                    if is_valid_num(current_eps) and is_valid_num(prev_eps):
                        c_eps = float(current_eps)
                        p_eps = float(prev_eps)
                        if p_eps > 0:
                            eps_growth = (c_eps - p_eps) / p_eps
                        elif p_eps < 0:
                            eps_growth = (c_eps - p_eps) / abs(p_eps)
        except:
            eps_growth = 0
    if not is_valid_num(eps_growth): eps_growth = 0

    y1_return = momentum.get('1y') or 0
    rs_rating = "A" if total_score >= 80 else "B" if total_score >= 65 else "C" if total_score >= 50 else "D"
    
    st.markdown("<h5 style='font-size:0.85rem;color:#E6EDF3;margin-bottom:8px'>🔑 핵심 펀더멘털 & 팩터</h5>", unsafe_allow_html=True)
    f_cols1 = st.columns(2)
    f_cols1[0].markdown(f"""
    <div style='background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px;text-align:center;margin-bottom:6px'>
        <small style='color:#8B949E;font-size:0.7rem'>EPS 성장률</small><br>
        <b style='color:#4ade80;font-size:0.95rem'>{eps_growth*100:+.1f}%</b>
    </div>
    """, unsafe_allow_html=True)
    f_cols1[1].markdown(f"""
    <div style='background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px;text-align:center;margin-bottom:6px'>
        <small style='color:#8B949E;font-size:0.7rem'>자기자본이익률</small><br>
        <b style='color:#60a5fa;font-size:0.95rem'>{roe*100:.1f}%</b>
    </div>
    """, unsafe_allow_html=True)

    f_cols2 = st.columns(2)
    f_cols2[0].markdown(f"""
    <div style='background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px;text-align:center'>
        <small style='color:#8B949E;font-size:0.7rem'>12M 가격수익률</small><br>
        <b style='color:#fbbf24;font-size:0.95rem'>{y1_return:+.1f}%</b>
    </div>
    """, unsafe_allow_html=True)
    f_cols2[1].markdown(f"""
    <div style='background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px;text-align:center'>
        <small style='color:#8B949E;font-size:0.7rem'>상대강도(RS)</small><br>
        <b style='color:#c084fc;font-size:0.95rem'>{rs_rating} 등급</b>
    </div>
    """, unsafe_allow_html=True)



# ================================================================
# 차트 렌더링에 필요한 컴포넌트 정의 및 데이터 동기화
# ================================================================
from plotly.subplots import make_subplots

with col_main:
    # --- 3) 재무 실적 및 어닝 서프라이즈 테이블 가로 배치 (좌측 하단 빈 공간 채우기) ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### 📊 분기 실적 & 어닝 서프라이즈 종합")
    
    f1_col, f2_col = st.columns(2)
    with f1_col:
        st.markdown("##### 📅 분기 재무 실적 (최근 12분기)")
        if financials and financials.get('q_income') is not None and not financials['q_income'].empty:
            qi = financials['q_income']
            rows_data = []
            rev_row = qi.loc['Total Revenue'] if 'Total Revenue' in qi.index else None
            gp_row = qi.loc['Gross Profit'] if 'Gross Profit' in qi.index else None
            ni_row = qi.loc['Net Income'] if 'Net Income' in qi.index else None
            if rev_row is not None:
                for col in qi.columns[:12]:
                    r = rev_row[col] if rev_row is not None else 0
                    g = gp_row[col] if gp_row is not None else 0
                    n = ni_row[col] if ni_row is not None else 0
                    margin_val = (g/r*100) if r and r != 0 else 0
                    rows_data.append({
                        '분기': f"{col.year} Q{col.quarter}" if hasattr(col,'quarter') else str(col)[:10],
                        '매출': fmt_mcap(r), '총이익': fmt_mcap(g), '순이익': fmt_mcap(n),
                        '마진': f"{margin_val:.1f}%"
                    })
                if rows_data:
                    st.dataframe(pd.DataFrame(rows_data), use_container_width=True, hide_index=True, height=260)
        else:
            st.info("재무제표 데이터 없음")
            
    with f2_col:
        st.markdown("##### 📈 어닝(EPS) 서프라이즈 이력")
        if earnings:
            html_rows = ""
            for e in earnings:
                beat_emoji = '✅' if e['beat'] == 'BEAT' else ('❌' if e['beat'] == 'MISS' else '➖')
                beat_color = '#4ade80' if e['beat'] == 'BEAT' else ('#f87171' if e['beat'] == 'MISS' else '#8B949E')
                
                pchg = e.get('price_chg')
                pchg_str = f"{pchg:+.1f}%" if pchg is not None else 'N/A'
                pchg_color = '#4ade80' if pchg and pchg > 0 else '#f87171' if pchg and pchg < 0 else '#8B949E'
                
                surp = e.get('surprise_pct', 0)
                surp_str = f"{surp:+.1f}%" if surp else 'N/A'
                
                est = f"${e['eps_est']:.3f}" if e['eps_est'] is not None else 'N/A'
                act = f"${e['eps_act']:.3f}" if e['eps_act'] is not None else 'N/A'
                
                safe_date = str(e['date'])[:10]
                
                html_rows += f"""<tr style='border-bottom:1px solid #30363D'>
                    <td style='padding:5px 4px;font-size:0.8rem;color:#C9D1D9'>{safe_date}</td>
                    <td style='padding:5px 4px;font-size:0.8rem;color:#C9D1D9'>{est}</td>
                    <td style='padding:5px 4px;font-size:0.8rem;color:#C9D1D9'>{act}</td>
                    <td style='padding:5px 4px;font-size:0.8rem;color:{beat_color};font-weight:bold'>{surp_str}</td>
                    <td style='padding:5px 4px;font-size:0.8rem;color:{beat_color}'>{beat_emoji} {e['beat']}</td>
                    <td style='padding:5px 4px;font-size:0.8rem;color:{pchg_color};font-weight:bold'>{pchg_str}</td>
                </tr>"""
                
            st.markdown(f"""
            <div style='max-height:260px;overflow-y:auto;border:1px solid #30363D;border-radius:6px'>
                <table style='width:100%;text-align:left;border-collapse:collapse'>
                    <thead>
                        <tr style='background:#161B22;border-bottom:1px solid #30363D;color:#8B949E;font-size:0.75rem'>
                            <th style='padding:6px 4px'>발표일</th>
                            <th style='padding:6px 4px'>예상</th>
                            <th style='padding:6px 4px'>실제</th>
                            <th style='padding:6px 4px'>서프%</th>
                            <th style='padding:6px 4px'>판정</th>
                            <th style='padding:6px 4px'>발표 후 1주 변동</th>
                        </tr>
                    </thead>
                    <tbody>{html_rows}</tbody>
                </table>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("어닝 서프라이즈 데이터 없음")

    # --- 4) SWOT 분석 렌더링 ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### 🔬 SWOT 분석 및 리스크 가이드")
    sw1, sw2, sw3, sw4 = st.columns(4)
    for col, title, key, cls in [(sw1,"STRENGTH 강점","strength","swot-s"),
                                  (sw2,"WEAKNESS 약점","weakness","swot-w"),
                                  (sw3,"OPPORTUNITY 기회","opportunity","swot-o"),
                                  (sw4,"THREAT 위협","threat","swot-t")]:
        items = "".join([f"<li style='color:#C9D1D9;font-size:0.8rem;margin:3px 0'>{s}</li>" for s in swot.get(key,[])])
        col.markdown(f"<div class='swot-card {cls}' style='min-height:180px'><b style='color:#E6EDF3;font-size:0.85rem'>{title}</b><ul style='padding-left:14px;margin-top:6px'>{items}</ul></div>", unsafe_allow_html=True)

    # --- 5) 매수/매도 핵심 논거 ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### 📌 퀀트 핵심 강점 및 리스크 논거")
    bg1, bg2 = st.columns(2)
    with bg1:
        st.markdown("**✔ 매수 핵심 강점**")
        for item in bull_case:
            tag_cls = {'성장모멘텀':'tag-green','대형주':'tag-blue','기관매수':'tag-purple','재무건전':'tag-green','핵심역량':'tag-green','기회요인':'tag-blue'}.get(item['tag'],'tag-green')
            st.markdown(f"<div style='display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid #21262D'>"
                        f"<span class='tag {tag_cls}'>{item['tag']}</span><span style='color:#C9D1D9;font-size:0.8rem'>{item['text']}</span></div>", unsafe_allow_html=True)
    with bg2:
        st.markdown("**✘ 매도 리스크 요인**")
        for item in bear_case:
            tag_cls = {'수익성':'tag-red','재무':'tag-red','변동성':'tag-orange','리스크':'tag-red','고평가':'tag-orange','매크로':'tag-orange','위협':'tag-red'}.get(item['tag'],'tag-red')
            st.markdown(f"<div style='display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid #21262D'>"
                        f"<span class='tag {tag_cls}'>{item['tag']}</span><span style='color:#C9D1D9;font-size:0.8rem'>{item['text']}</span></div>", unsafe_allow_html=True)

    # --- 6) BULL / BASE / BEAR 시나리오 카드 & 최종 판단문 ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### 🎯 시나리오 가치 평가 및 최종 의사결정")
    t1, t2, t3 = st.columns(3)
    t1.markdown(f"""<div class='bull-card' style='padding:12px'>
    <p style='color:#4ade80;margin:0;font-weight:bold;font-size:0.85rem'>🐂 BULL 시나리오</p>
    <h2 style='color:#4ade80!important;font-size:1.8rem;margin:4px 0'>${targets['bull']}</h2>
    <p style='color:#86efac;margin:0;font-size:0.75rem'>현재가 대비 {targets['bull_pct']:+.1f}%</p>
    </div>""", unsafe_allow_html=True)
    
    t2.markdown(f"""<div class='base-card' style='padding:12px'>
    <p style='color:#fbbf24;margin:0;font-weight:bold;font-size:0.85rem'>■ BASE 시나리오</p>
    <h2 style='color:#fbbf24!important;font-size:1.8rem;margin:4px 0'>${targets['base']}</h2>
    <p style='color:#fde68a;margin:0;font-size:0.75rem'>현재가 대비 {targets['base_pct']:+.1f}%</p>
    </div>""", unsafe_allow_html=True)
    
    t3.markdown(f"""<div class='bear-card' style='padding:12px'>
    <p style='color:#f87171;margin:0;font-weight:bold;font-size:0.85rem'>🐻 BEAR 시나리오</p>
    <h2 style='color:#f87171!important;font-size:1.8rem;margin:4px 0'>${targets['bear']}</h2>
    <p style='color:#fca5a5;margin:0;font-size:0.75rem'>현재가 대비 {targets['bear_pct']:+.1f}%</p>
    </div>""", unsafe_allow_html=True)

    long_term_html = ""
    if targets.get('long_term_target') is not None and str(targets.get('long_term_target')).strip() != "":
        long_term_html = f"<br><span style='color:#E2B3FF;font-weight:bold;font-size:1rem'>🚀 초장기 목표: {targets['long_term_target']}</span>"

    opt_sentiment_html = ""
    if verdict.get('options_sentiment'):
        opt_sentiment_html = f"<br><span style='color:#58A6FF;font-weight:bold;font-size:0.8rem'>{verdict['options_sentiment']}</span>"

    verdict_html = (
        f"<div class='verdict-box' style='padding:16px;margin-top:12px'>"
        f"<h4 style='color:#FF6B00!important;margin:0 0 8px 0;font-size:1.15rem'>▶ 최종 판단 가이드</h4>"
        f"<p style='color:#C9D1D9;font-size:0.95rem;line-height:1.6;margin:0'>"
        f"<b>{verdict['short_term']}</b><br>"
        f"<b>{verdict['mid_term']}</b><br>"
        f"{verdict['long_term']}<br>"
        f"<span style='color:#FFD700;font-weight:bold'>{verdict['buy_zone']}</span><br>"
        f"<span style='color:#FF4444;font-weight:bold'>🚨 {verdict.get('stop_loss','')}</span>"
        f"{long_term_html}"
        f"{opt_sentiment_html}"
        f"</p></div>"
    )
    st.markdown(verdict_html, unsafe_allow_html=True)

    # --- 기술적 분석 차트 (하단 배치) ---
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    c_range, c_intv = st.columns(2)
    selected_range = c_range.radio("조회 기간", ["1D", "1W", "1M", "3M", "1Y", "2Y", "3Y"], horizontal=True, index=4)
    selected_interval = c_intv.radio("캔들 간격", ["자동 연동", "2분봉", "5분봉", "15분봉", "30분봉", "1시간봉", "4시간봉", "일봉", "주봉"], horizontal=True, index=0)
    
    ma_options = st.multiselect("이동평균선", [5, 10, 20, 60, 120, 200, 240], default=[5, 10, 20, 60, 120, 200, 240])
    
    if selected_interval == "자동 연동":
        interval_map = {"1D": "15분봉", "1W": "30분봉", "1M": "1시간봉", "3M": "4시간봉", "1Y": "일봉", "2Y": "일봉", "3Y": "일봉"}
        interval_str = interval_map.get(selected_range, "일봉")
    else:
        interval_str = selected_interval
        
    st.markdown(f"#### 📈 기술적 분석 차트 <span style='color:#58A6FF;font-size:0.9rem;font-weight:normal'>[{interval_str} 기준]</span>", unsafe_allow_html=True)
    
    with st.spinner("차트 데이터 동기화 중..."):
        df_c = ae.fetch_chart_data(st.session_state['ticker'], selected_range, selected_interval)
        
    if df_c is not None and not df_c.empty:
        # RSI 계산
        delta = df_c['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        avg_gain = gain.ewm(com=13, min_periods=14).mean()
        avg_loss = loss.ewm(com=13, min_periods=14).mean()
        rs = avg_gain / avg_loss
        df_c['RSI'] = 100 - (100 / (1 + rs))

        # MACD 계산
        ema12 = df_c['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df_c['Close'].ewm(span=26, adjust=False).mean()
        df_c['MACD'] = ema12 - ema26
        df_c['MACD_Signal'] = df_c['MACD'].ewm(span=9, adjust=False).mean()
        df_c['MACD_Hist'] = df_c['MACD'] - df_c['MACD_Signal']

        # 이동평균선 계산
        for ma in ma_options:
            if len(df_c) >= ma:
                df_c[f'MA_{ma}'] = df_c['Close'].rolling(window=ma).mean()

        # 4행 서브플롯: 캔들+MA | 거래량 | RSI | MACD + EPS
        fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.025,
                            row_heights=[0.40, 0.12, 0.12, 0.16, 0.20],
                            subplot_titles=None)

        # 1) 캔들스틱 (초록 양봉, 빨강 음봉 적용)
        fig.add_trace(go.Candlestick(x=df_c.index, open=df_c['Open'], high=df_c['High'],
                                      low=df_c['Low'], close=df_c['Close'], name='Price',
                                      increasing_line_color='#4ade80', increasing_fillcolor='#4ade80',
                                      decreasing_line_color='#f87171', decreasing_fillcolor='#f87171'), row=1, col=1)

        # 이동평균선
        ma_colors = {5:'#FFEB3B',10:'#FF9800',20:'#2196F3',60:'#9C27B0',120:'#00BCD4',200:'#F44336',240:'#E91E63'}
        for ma in ma_options:
            col_name = f'MA_{ma}'
            if col_name in df_c.columns:
                fig.add_trace(go.Scatter(x=df_c.index, y=df_c[col_name], mode='lines',
                                         name=f'{ma}일선', line=dict(width=1.2, color=ma_colors.get(ma,'#888'))), row=1, col=1)

        # 2) 거래량 (양봉 초록, 음봉 빨강)
        colors_vol = ['#f87171' if c < o else '#4ade80' for c, o in zip(df_c['Close'], df_c['Open'])]
        fig.add_trace(go.Bar(x=df_c.index, y=df_c['Volume'], name='Volume', marker_color=colors_vol, opacity=0.7), row=2, col=1)

        # 3) RSI
        fig.add_trace(go.Scatter(x=df_c.index, y=df_c['RSI'], name='RSI', line=dict(color='#AB47BC', width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", line_width=0.8, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", line_width=0.8, row=3, col=1)

        # 4) MACD
        fig.add_trace(go.Scatter(x=df_c.index, y=df_c['MACD'], name='MACD', line=dict(color='#2196F3', width=1.5)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df_c.index, y=df_c['MACD_Signal'], name='Signal', line=dict(color='#FF9800', width=1.5)), row=4, col=1)
        hist_colors = ['#4ade80' if v >= 0 else '#f87171' for v in df_c['MACD_Hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df_c.index, y=df_c['MACD_Hist'], name='MACD Hist', marker_color=hist_colors, opacity=0.6), row=4, col=1)

        # 5) EPS 차트 (트레이딩뷰 스타일)
        if earnings:
            eps_dates = []
            eps_est_vals = []
            eps_act_vals = []
            for e in earnings:
                try:
                    d = pd.Timestamp(e['date'])
                    eps_dates.append(d)
                    eps_est_vals.append(e.get('eps_est'))
                    eps_act_vals.append(e.get('eps_act'))
                except:
                    pass
            if eps_dates:
                fig.add_trace(go.Scatter(x=eps_dates, y=eps_est_vals, name='EPS 예상',
                    mode='lines+markers', line=dict(color='#fbbf24', width=1.5, dash='dash'),
                    marker=dict(size=6, symbol='diamond')), row=5, col=1)
                eps_bar_colors = ['#4ade80' if (a and e and a >= e) else '#f87171'
                                  for a, e in zip(eps_act_vals, eps_est_vals)]
                fig.add_trace(go.Bar(x=eps_dates, y=eps_act_vals, name='EPS 실제',
                    marker_color=eps_bar_colors, opacity=0.8, width=8*86400000), row=5, col=1)

        fig.update_layout(
            height=850, template='plotly_dark',
            plot_bgcolor='rgba(14,17,23,0.9)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
            margin=dict(l=40, r=10, t=10, b=10),
            dragmode='zoom', hovermode='x unified'
        )
        if not df_c.empty:
            start_dt = df_c.index[0]
            end_dt = df_c.index[-1]
            padding = (end_dt - start_dt) * 0.03
            if padding.total_seconds() == 0:
                padding = pd.Timedelta(hours=1)
            fig.update_xaxes(range=[start_dt - padding, end_dt + padding], fixedrange=False)
        else:
            fig.update_xaxes(fixedrange=False)
        fig.update_yaxes(fixedrange=False)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Vol", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1)
        fig.update_yaxes(title_text="MACD", row=4, col=1)
        fig.update_yaxes(title_text="EPS ($)", row=5, col=1)

        st.plotly_chart(fig, use_container_width=True)


# --- 7) 우측 사이드 뷰 하반부: 실시간 핵심 뉴스 목록 배치 ---
with col_side:
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("#### 📰 최신 분석 뉴스 & 플로우", unsafe_allow_html=True)
    for n in news[:12]:
        pub_date = str(n.get('date',''))[:10] if n.get('date') else ''
        date_str = f" · {pub_date}" if pub_date else ""
        st.markdown(f"<div style='padding:8px 0;border-bottom:1px solid #21262D'>"
                    f"<a href='{n['link']}' style='color:#58A6FF;text-decoration:none;font-size:0.88rem;font-weight:bold'>{n['title'][:75]}...</a>"
                    f"<br><small style='color:#8B949E;font-size:0.75rem'>{n.get('source','')}{date_str}</small></div>", unsafe_allow_html=True)
    # 풋/콜 옵션 체인 센티멘트 시각화 및 분석 배치
    opt_an = data.get('options_analysis')
    if opt_an and opt_an.get('oi_distribution'):
        try:
            st.markdown("<br><hr>", unsafe_allow_html=True)
            
            # 버터플라이 차트 그리기 헬퍼 함수 정의
            import pandas as pd
            import plotly.graph_objects as go
            
            def draw_options_oi_butterfly_chart(ticker, expiry, current_price, max_pain, oi_data):
                df = pd.DataFrame(oi_data)
                if df.empty:
                    return None
                df['put_oi_neg'] = -df['put_oi']
                
                fig = go.Figure()
                
                # 1) Put OI (왼쪽 오렌지색 막대, 음수 스케일)
                fig.add_trace(go.Bar(
                    y=df['strike'],
                    x=df['put_oi_neg'],
                    orientation='h',
                    name='Put OI (풋 미결제약정)',
                    marker_color='#FF8C00',
                    hovertemplate='Strike: $%{y}<br>Put OI: %{customdata:,.0f}<extra></extra>',
                    customdata=df['put_oi']
                ))
                
                # 2) Call OI (오른쪽 청록색 막대)
                fig.add_trace(go.Bar(
                    y=df['strike'],
                    x=df['call_oi'],
                    orientation='h',
                    name='Call OI (콜 미결제약정)',
                    marker_color='#00B2FF',
                    hovertemplate='Strike: $%{y}<br>Call OI: %{x:,.0f}<extra></extra>'
                ))
                
                # 3) 현재가 기준선 (청록색 실선)
                fig.add_hline(
                    y=current_price,
                    line_color='#00B2FF',
                    line_width=1.5,
                    annotation_text=f"Current(현재가): ${current_price:.2f}",
                    annotation_position="top left",
                    annotation_font=dict(size=9, color='#00B2FF', weight='bold')
                )
                
                # 4) Max Pain 기준선 (빨간색 대시선)
                fig.add_hline(
                    y=max_pain,
                    line_color='#FF3333',
                    line_width=1.5,
                    line_dash="dash",
                    annotation_text=f"Max Pain(최대고통가): ${max_pain:.1f}",
                    annotation_position="bottom right",
                    annotation_font=dict(size=9, color='#FF3333', weight='bold')
                )
                
                fig.update_layout(
                    title=dict(
                        text=f"<b>{ticker.upper()} — Strike-Level OI Distribution</b> <span style='font-size:0.75rem;color:#8B949E'>(만기: {expiry})</span>",
                        font=dict(size=11, color='#E6EDF3'),
                        x=0.01,
                        y=0.96
                    ),
                    barmode='relative',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=380,
                    margin=dict(l=40, r=20, t=50, b=35),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(size=8, color='#C9D1D9')
                    ),
                    xaxis=dict(
                        title="← Put OI (풋 미결제약정) | Call OI (콜 미결제약정) →",
                        title_font=dict(size=8, color='#8B949E'),
                        gridcolor='#21262D',
                        zerolinecolor='#30363D',
                        tickfont=dict(size=8, color='#8B949E')
                    ),
                    yaxis=dict(
                        title="Strike Price (행사가, $)",
                        title_font=dict(size=8, color='#8B949E'),
                        gridcolor='#21262D',
                        zerolinecolor='#30363D',
                        tickfont=dict(size=8, color='#8B949E'),
                        tickmode='linear',
                        dtick=round((df['strike'].max() - df['strike'].min()) / 12, 1) or 1.0
                    )
                )
                return fig

            current_price = float(ov.get('current_price', 0))
            max_pain = float(opt_an.get('max_pain_strike', 0))
            expiry = opt_an.get('expiry', '')
            oi_data = opt_an.get('oi_distribution', [])
            
            # 버터플라이 차트 생성 및 출력
            fig_opt = draw_options_oi_butterfly_chart(ticker, expiry, current_price, max_pain, oi_data)
            if fig_opt:
                st.plotly_chart(fig_opt, use_container_width=True)
                
            # 퀀트 세부 설명 요약 박스
            st.markdown(f"""
            <div style='background:#10141b;border:1px solid #30363D;border-radius:6px;padding:12px;margin-bottom:12px'>
                <p style='color:#C9D1D9;font-size:0.83rem;line-height:1.6;margin:0'>
                    💡 <b>옵션 PCR:</b> <span style='color:#58A6FF;font-weight:bold'>{opt_an['pcr_oi']}</span> (미결제약정 풋/콜 비율)<br>
                    🎯 <b>최대 고통가 (Max Pain):</b> <span style='color:#fbbf24;font-weight:bold'>${opt_an['max_pain_strike']:.1f}</span> (주가 회귀성 자석 타겟)<br>
                    🔴 <b>최대 콜 OI (저항선):</b> ${opt_an['max_call_oi_strike']:.1f} | 🟢 <b>최대 풋 OI (지지선):</b> ${opt_an['max_put_oi_strike']:.1f}<br>
                    💬 {opt_an['sentiment_desc']}
                </p>
            </div>
            """, unsafe_allow_html=True)
        except Exception as table_err:
            st.warning(f"⚠️ 옵션 분석 보드 시각화 실패: {table_err}")
            
    # --- Fear & Greed Index 실시간 CNN 연동 및 다이나믹 2WAY 다이얼/차트 카드 장착 ---
    def draw_fear_greed_index_card():
        import requests
        import numpy as np
        import pandas as pd
        import plotly.graph_objects as go
        from datetime import datetime, timedelta, timezone
        
        # 1) 기본값 세팅 (Fallback 대비)
        fg_score = 50
        rating_en = "neutral"
        state_kr = "🟡 중립 (Neutral)"
        desc = "CNN Fear & Greed 지수 데이터 연동 지연"
        color = "#FFCC00"
        source_type = "CNN Business (Official)"
        last_updated_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S (KST)")
        
        # 역사적 스냅샷 기본값 (Previous Close 등)
        fng_history = {
            'previous_close': 50,
            'previous_1_week': 50,
            'previous_1_month': 50,
            'previous_1_year': 50
        }
        historical_trend_data = []
        
        # 2) CNN 공식 Dataviz API 호출 시도
        api_success = False
        try:
            url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Referer': 'https://edition.cnn.com/'
            }
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data_json = r.json()
                fng = data_json.get('fear_and_greed', {})
                if 'score' in fng:
                    fg_score = int(round(float(fng['score'])))
                    rating_en = fng.get('rating', 'neutral').lower().strip()
                    
                    # 역사적 스냅샷 데이터 수급
                    fng_history['previous_close'] = int(round(float(fng.get('previous_close', 50))))
                    fng_history['previous_1_week'] = int(round(float(fng.get('previous_1_week', 50))))
                    fng_history['previous_1_month'] = int(round(float(fng.get('previous_1_month', 50))))
                    fng_history['previous_1_year'] = int(round(float(fng.get('previous_1_year', 50))))
                    
                    # 1년 역사적 트렌드 시계열 수급
                    hist_data = data_json.get('fear_and_greed_historical', {}).get('data', [])
                    if hist_data:
                        historical_trend_data = hist_data
                    
                    # 등급명 영한 번환 및 색상 매핑
                    if rating_en == 'extreme greed':
                        state_kr = "👑 극단적 탐욕 (Extreme Greed)"
                        color = "#00FF66"
                    elif rating_en == 'greed':
                        state_kr = "🟢 탐욕 (Greed)"
                        color = "#4ade80"
                    elif rating_en == 'neutral':
                        state_kr = "🟡 중립 (Neutral)"
                        color = "#FFCC00"
                    elif rating_en == 'fear':
                        state_kr = "🟠 공포 (Fear)"
                        color = "#f87171"
                    elif rating_en == 'extreme fear':
                        state_kr = "💀 극단적 공포 (Extreme Fear)"
                        color = "#FF3333"
                    else:
                        state_kr = f"🟢 {rating_en.capitalize()}"
                        color = "#4ade80"
                        
                    # 타임스탬프 파싱 후 KST 변환
                    ts_str = fng.get('timestamp', '')
                    if ts_str:
                        try:
                            ts_clean = ts_str.replace("Z", "+00:00")
                            dt = datetime.fromisoformat(ts_clean)
                            dt_kst = dt.astimezone(timezone(timedelta(hours=9)))
                            last_updated_str = dt_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")
                        except Exception:
                            last_updated_str = ts_str
                            
                    desc = f"CNN 공식 시장 센티멘트 7가지 팩터 실시간 합성 분석 결과"
                    api_success = True
        except Exception as e:
            print(f"[CNN FNG API Fetch Failed]: {e}")
            api_success = False
            
        # 3) Fallback 구동 (통신 장애용 VIX proxy)
        if not api_success:
            import yfinance as yf
            source_type = "vix proxy (Fallback)"
            try:
                sp500 = yf.Ticker("^GSPC")
                vix = yf.Ticker("^VIX")
                
                sp_hist = sp500.history(period="125d")
                vix_hist = vix.history(period="30d")
                
                if not sp_hist.empty and not vix_hist.empty:
                    current_sp = sp_hist['Close'].iloc[-1]
                    ma_125 = sp_hist['Close'].mean()
                    ratio = (current_sp - ma_125) / ma_125
                    score_sp = max(0, min(100, int((ratio + 0.08) * 625)))
                    
                    current_vix = vix_hist['Close'].iloc[-1]
                    score_vix = max(0, min(100, int(100 - (current_vix - 12) * (90 / 23))))
                    
                    hyg = yf.Ticker("HYG").history(period="10d")
                    ief = yf.Ticker("IEF").history(period="10d")
                    if not hyg.empty and not ief.empty:
                        hyg_ret = (hyg['Close'].iloc[-1] - hyg['Close'].iloc[0]) / hyg['Close'].iloc[0]
                        ief_ret = (ief['Close'].iloc[-1] - ief['Close'].iloc[0]) / ief['Close'].iloc[0]
                        diff = hyg_ret - ief_ret
                        score_safe = max(0, min(100, int(50 + diff * 1200)))
                    else:
                        score_safe = 50
                        
                    fg_score = int(score_sp * 0.45 + score_vix * 0.40 + score_safe * 0.15)
                    
                    if fg_score >= 75:
                        rating_en = "extreme greed"
                        state_kr = "👑 극단적 탐욕 (Extreme Greed)"
                        color = "#00FF66"
                    elif fg_score >= 55:
                        rating_en = "greed"
                        state_kr = "🟢 탐욕 (Greed)"
                        color = "#4ade80"
                    elif fg_score >= 45:
                        rating_en = "neutral"
                        state_kr = "🟡 중립 (Neutral)"
                        color = "#FFCC00"
                    elif fg_score >= 25:
                        rating_en = "fear"
                        state_kr = "🟠 공포 (Fear)"
                        color = "#f87171"
                    else:
                        rating_en = "extreme fear"
                        state_kr = "💀 극단적 공포 (Extreme Fear)"
                        color = "#FF3333"
                        
                    desc = f"Fallback Mode | S&P500 125MA 이격도: {ratio*100:+.1f}%, VIX 변동성: {current_vix:.1f}p"
                    last_updated_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S (KST)")
            except:
                pass
                
        state_en = rating_en.upper()
        
        # 4) 알약 토글용 고급 커스텀 CSS 인입 (가로형 st.radio 오버라이딩 기법)
        st.markdown("""
        <style>
            /* st.radio 라디오 그룹의 위젯 라벨 숨김 */
            div[data-testid="stHorizontalBlock"] div[data-testid="stWidgetLabel"] {
                display: none !important;
            }
            /* 라디오 배치 및 간격 둥글게 감싸기 */
            div[data-testid="stHorizontalBlock"] div[role="radiogroup"] {
                background-color: #10141b !important;
                border: 1px solid #30363D !important;
                border-radius: 30px !important;
                padding: 3px 5px !important;
                gap: 4px !important;
                display: inline-flex !important;
                float: right !important;
                margin-top: 10px !important;
                margin-bottom: 5px !important;
            }
            /* 기본 라디오 동그라미 아이콘 제거 */
            div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] div[data-testid="stRadioButtonUI"] {
                display: none !important;
            }
            /* 버튼 라벨 스타일링 */
            div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] {
                background: transparent !important;
                border: none !important;
                padding: 4px 14px !important;
                border-radius: 30px !important;
                color: #8B949E !important;
                cursor: pointer !important;
                margin: 0 !important;
                font-size: 0.72rem !important;
                font-family: "Outfit", sans-serif !important;
                transition: all 0.2s ease-in-out !important;
            }
            /* 선택 상태 하이라이트 */
            div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"]:has(input:checked) {
                background-color: #E6EDF3 !important;
                color: #0D1117 !important;
                font-weight: bold !important;
            }
            div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"]:has(input:checked) * {
                color: #0D1117 !important;
                font-weight: bold !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # 스위치 전용 가로 레이아웃 단 (오른쪽 정렬을 위해 더미 공간 확보)
        col_space, col_switch = st.columns([0.48, 0.52])
        with col_switch:
            mode = st.radio(
                "FNG_Switch_Mode",
                ["Overview", "Timeline"],
                horizontal=True,
                label_visibility="collapsed",
                key="fng_mode_radio_selector"
            )
            
        # =========================================================================
        # 1. OVERVIEW TAB: 프리미엄 아치 다이얼 + 4단 역사적 카드 뷰
        # =========================================================================
        if mode == "Overview":
            # 기하학적 삼각함수 기반 초호화 커스텀 반원 다이얼 렌더링 함수
            def draw_luxury_fng_gauge(score, rating_str):
                # 0~100 점수를 180도~0도로 매핑 (라디안)
                theta = np.pi * (1 - score / 100.0)
                
                fig = go.Figure()
                
                # ====================================================================
                # 기하학적 데카르트 좌표계 도넛 조각 폴리곤 렌더링 (Pie 차트의 오프셋 불일치 원천 차단)
                # 원점(0,0)을 완벽히 공유하여 모든 점선/텍스트/바늘과 단 1픽셀의 오차도 없이 결합
                # ====================================================================
                r_out = 1.0   # 띠 바깥쪽 반경
                r_in = 0.68   # 띠 안쪽 반경
                
                # 왼쪽(180도, 점수0)부터 오른쪽(0도, 점수100)으로 5개 스펙트럼 구간 정의
                # 각 구간은 36도(0.2pi)씩 차지
                segments = [
                    {'name': 'extreme fear', 'start': 1.0, 'end': 0.8},
                    {'name': 'fear', 'start': 0.8, 'end': 0.6},
                    {'name': 'neutral', 'start': 0.6, 'end': 0.4},
                    {'name': 'greed', 'start': 0.4, 'end': 0.2},
                    {'name': 'extreme greed', 'start': 0.2, 'end': 0.0}
                ]
                
                active_colors = {
                    'extreme fear': '#FF3333',
                    'fear': '#f87171',
                    'neutral': '#FFCC00',
                    'greed': '#00F5A0',
                    'extreme greed': '#00FF66'
                }
                bg_color = "rgba(48, 54, 61, 0.45)"
                
                active_idx = min(4, max(0, int(score // 20)))
                
                for idx, seg in enumerate(segments):
                    # 구간별 시작/종료 각도 (라디안)
                    theta_start = seg['start'] * np.pi
                    theta_end = seg['end'] * np.pi
                    
                    # 바깥쪽 호 (start -> end 각도 감소 방향)
                    theta_outer = np.linspace(theta_start, theta_end, 30)
                    x_outer = r_out * np.cos(theta_outer)
                    y_outer = r_out * np.sin(theta_outer) * 1.25
                    
                    # 안쪽 호 (end -> start 각도 증가 방향으로 돌아옴)
                    theta_inner = np.linspace(theta_end, theta_start, 30)
                    x_inner = r_in * np.cos(theta_inner)
                    y_inner = r_in * np.sin(theta_inner) * 1.25
                    
                    # 폴리곤 닫기 위해 배열 결합
                    x_poly = np.concatenate([x_outer, x_inner, [x_outer[0]]])
                    y_poly = np.concatenate([y_outer, y_inner, [y_outer[0]]])
                    
                    # 현재 구간 활성화 여부에 따른 색상 부여
                    is_active = (idx == active_idx)
                    fill_color = active_colors.get(rating_str.lower().strip(), '#00F5A0') if is_active else bg_color
                    
                    fig.add_trace(go.Scatter(
                        x=x_poly, y=y_poly,
                        fill='toself',
                        fillcolor=fill_color,
                        mode='lines',
                        line=dict(color='#0D1117', width=2.5),
                        hoverinfo='none',
                        showlegend=False
                    ))
                
                # 내측 가이드 점선 원호 (Inner Dotted Guide Arc)
                inner_r = 0.62
                arch_theta = np.linspace(np.pi, 0, 80)
                arch_x = inner_r * np.cos(arch_theta)
                arch_y = inner_r * np.sin(arch_theta) * 1.25
                
                fig.add_trace(go.Scatter(
                    x=arch_x, y=arch_y,
                    mode='lines',
                    line=dict(color='#8B949E', width=1.5, dash='dot'),
                    hoverinfo='none',
                    showlegend=False
                ))
                
                # 0...25...50...75...100 앵글 숫자 표기 (점선 가이드 안쪽에 칼정렬)
                marker_r = 0.53
                ticks = [0, 25, 50, 75, 100]
                for t in ticks:
                    t_rad = np.pi * (1 - t / 100.0)
                    tx = marker_r * np.cos(t_rad)
                    ty = marker_r * np.sin(t_rad) * 1.25
                    
                    # 끝단 0, 100은 잘림 방지를 위해 미세 보정
                    if t == 0: tx += 0.04
                    elif t == 100: tx -= 0.04
                    
                    fig.add_annotation(
                        x=tx, y=ty,
                        text=str(t),
                        showarrow=False,
                        font=dict(size=10.5, color='#8B949E', family='"Outfit", monospace', weight='bold')
                    )
                    
                # 각 구간별 한글/영문 궤적 텍스트 어노테이션 (구간별 중앙 각도 정렬)
                # 162도 (Extreme Fear), 126도 (Fear), 90도 (Neutral), 54도 (Greed), 18도 (Extreme Greed)
                text_r = 0.86
                sections = [
                    ("극단적 공포", 162, "EXTREME FEAR"),
                    ("공포", 126, "FEAR"),
                    ("중립", 90, "NEUTRAL"),
                    ("탐욕", 54, "GREED"),
                    ("극단적 탐욕", 18, "EXTREME GREED")
                ]
                for idx, (lbl_kr, angle_deg, lbl_en) in enumerate(sections):
                    rad = np.deg2rad(angle_deg)
                    lx = text_r * np.cos(rad)
                    ly = text_r * np.sin(rad) * 1.25
                    
                    is_active = (idx == active_idx)
                    text_color = '#0D1117' if is_active else '#8B949E'
                    font_size = 13.0 if is_active else 10.5
                    font_weight = 'bold' if is_active else 'normal'
                    
                    fig.add_annotation(
                        x=lx, y=ly,
                        text=lbl_kr,
                        showarrow=False,
                        font=dict(size=font_size, color=text_color, family='"Outfit", sans-serif', weight=font_weight),
                        textangle=90 - angle_deg # 아치 궤도에 맞춘 기하학 회전 각도 연산
                    )
                    
                # 초정밀 지침 바늘선 (Needle Hand)
                # 원점(0,0)에서 현재 score의 라디안 각도로 샤프한 레이저 라인 투사
                needle_r = 0.65
                nx = needle_r * np.cos(theta)
                ny = needle_r * np.sin(theta) * 1.25
                
                fig.add_trace(go.Scatter(
                    x=[0, nx], y=[0, ny],
                    mode='lines+markers',
                    line=dict(color='#FFFFFF', width=4),
                    marker=dict(color='#FFFFFF', size=6, symbol='circle'),
                    hoverinfo='none',
                    showlegend=False
                ))
                
                # 중앙 하단 팝업 원형 코어 플레이트 & 거대 네온 스코어 숫자 배치
                fig.add_annotation(
                    x=0, y=-0.08,
                    text=f"<span style='font-size:36px; font-weight:900; color:#FFFFFF; font-family:\"Outfit\", sans-serif'>{score}</span>",
                    showarrow=False,
                    bgcolor='#0D1117',
                    bordercolor='#30363D',
                    borderwidth=1.5,
                    borderpad=11
                )
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=10, b=5),
                    height=230,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.15, 1.15]),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, 1.45])
                )
                return fig
                
            # 헤더 정보 박스 출력 (초슬림 가로 플렉스박스로 높이를 0.75배 이하로 압축)
            st.markdown(f"""
            <div style='background:#10141b;border:1px solid #30363D;border-radius:8px;padding:5px 10px;margin-bottom:4px'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='font-size:0.85rem;color:#E6EDF3;font-family:"Outfit", sans-serif;letter-spacing:1px;font-weight:bold;'>FEAR & GREED</span>
                    <span style='font-size:0.8rem;color:{color};font-weight:bold;letter-spacing:0.8px;'>{state_en}</span>
                </div>
                <div style='text-align:left; margin-top:2px;'>
                    <span style='font-size:0.55rem;color:#8B949E;font-family:monospace'>Source: {source_type} | Last updated: {last_updated_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            fig_custom = draw_luxury_fng_gauge(fg_score, rating_en)
            st.plotly_chart(fig_custom, use_container_width=True, config={'displayModeBar': False})
            
            # 4단 역사적 변동 비교 카드 그리드 (Previous Close, 1 Week, 1 Month, 1 Year)
            def get_rating_kr(val):
                if val >= 75: return "👑 극단적 탐욕", "#00FF66"
                elif val >= 55: return "🟢 탐욕", "#4ade80"
                elif val >= 45: return "🟡 중립", "#FFCC00"
                elif val >= 25: return "🟠 공포", "#f87171"
                else: return "💀 극단적 공포", "#FF3333"
                
            pc_rating, pc_color = get_rating_kr(fng_history['previous_close'])
            pw_rating, pw_color = get_rating_kr(fng_history['previous_1_week'])
            pm_rating, pm_color = get_rating_kr(fng_history['previous_1_month'])
            py_rating, py_color = get_rating_kr(fng_history['previous_1_year'])
            
            st.markdown(f"""
            <div style='background:#10141b;border:1px solid #30363D;border-radius:8px;padding:12px;margin-bottom:6px'>
                <div style='display:flex; justify-content:space-between; margin-bottom:8px'>
                    <div style='width:48%; background:#0d1117; padding:8px; border-radius:6px; border:1px solid #21262D'>
                        <span style='font-size:0.65rem; color:#8B949E; display:block'>Previous close</span>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:2px'>
                            <span style='font-size:0.78rem; color:{pc_color}; font-weight:bold'>{pc_rating}</span>
                            <span style='font-size:0.75rem; color:#FFFFFF; font-weight:bold; background:#21262D; padding:2px 8px; border-radius:12px'>{fng_history['previous_close']}</span>
                        </div>
                    </div>
                    <div style='width:48%; background:#0d1117; padding:8px; border-radius:6px; border:1px solid #21262D'>
                        <span style='font-size:0.65rem; color:#8B949E; display:block'>1 week ago</span>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:2px'>
                            <span style='font-size:0.78rem; color:{pw_color}; font-weight:bold'>{pw_rating}</span>
                            <span style='font-size:0.75rem; color:#FFFFFF; font-weight:bold; background:#21262D; padding:2px 8px; border-radius:12px'>{fng_history['previous_1_week']}</span>
                        </div>
                    </div>
                </div>
                <div style='display:flex; justify-content:space-between'>
                    <div style='width:48%; background:#0d1117; padding:8px; border-radius:6px; border:1px solid #21262D'>
                        <span style='font-size:0.65rem; color:#8B949E; display:block'>1 month ago</span>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:2px'>
                            <span style='font-size:0.78rem; color:{pm_color}; font-weight:bold'>{pm_rating}</span>
                            <span style='font-size:0.75rem; color:#FFFFFF; font-weight:bold; background:#21262D; padding:2px 8px; border-radius:12px'>{fng_history['previous_1_month']}</span>
                        </div>
                    </div>
                    <div style='width:48%; background:#0d1117; padding:8px; border-radius:6px; border:1px solid #21262D'>
                        <span style='font-size:0.65rem; color:#8B949E; display:block'>1 year ago</span>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:2px'>
                            <span style='font-size:0.78rem; color:{py_color}; font-weight:bold'>{py_rating}</span>
                            <span style='font-size:0.75rem; color:#FFFFFF; font-weight:bold; background:#21262D; padding:2px 8px; border-radius:12px'>{fng_history['previous_1_year']}</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # =========================================================================
        # 2. TIMELINE TAB: 1개년 역사적 추세 차트 뷰
        # =========================================================================
        elif mode == "Timeline":
            if not historical_trend_data:
                st.warning("⚠️ 1년 역사적 트렌드 시계열 데이터가 존재하지 않습니다.")
            else:
                def draw_fear_greed_timeline_chart(hist_list):
                    df_trend = pd.DataFrame(hist_list)
                    df_trend['date'] = pd.to_datetime(df_trend['x'], unit='ms')
                    
                    fig = go.Figure()
                    
                    # 1년 역사 추세 라인
                    fig.add_trace(go.Scatter(
                        x=df_trend['date'], y=df_trend['y'],
                        mode='lines',
                        line=dict(color='#00B2FF', width=2),
                        name="Fear & Greed Index",
                        hovertemplate="<b>날짜</b>: %{x|%Y-%m-%d}<br><b>지수</b>: %{y:.1f}"
                    ))
                    
                    # Extreme Fear (25), Neutral (50), Extreme Greed (75) 점선 가이드라인 투사
                    guides = [
                        (25, "Extreme Fear (25)", "#f87171"),
                        (50, "Neutral (50)", "#FFCC00"),
                        (75, "Extreme Greed (75)", "#00FF66")
                    ]
                    for val, label, col_line in guides:
                        fig.add_shape(
                            type="line",
                            x0=df_trend['date'].min(), x1=df_trend['date'].max(),
                            y0=val, y1=val,
                            line=dict(color=col_line, width=1, dash="dash")
                        )
                        # 주석 글자 추가
                        fig.add_annotation(
                            x=df_trend['date'].min(), y=val,
                            text=label,
                            showarrow=False,
                            xanchor="left",
                            yanchor="bottom",
                            font=dict(size=8.5, color=col_line, family='sans-serif'),
                            opacity=0.8
                        )
                        
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=25, r=35, t=15, b=15),
                        height=210,
                        xaxis=dict(
                            gridcolor='#21262D',
                            zerolinecolor='#30363D',
                            tickfont=dict(size=9, color='#8B949E')
                        ),
                        yaxis=dict(
                            gridcolor='#21262D',
                            zerolinecolor='#30363D',
                            tickfont=dict(size=9, color='#8B949E'),
                            range=[0, 100],
                            tickvals=[0, 25, 50, 75, 100],
                            side="right" # CNN 원본 캡처에 똑맞춘 우측 Y축 정렬
                        ),
                        showlegend=False
                    )
                    return fig
                    
                fig_timeline = draw_fear_greed_timeline_chart(historical_trend_data)
                st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False})
                
                st.markdown(f"""
                <div style='background:#10141b;border:1px solid #30363D;border-radius:8px;padding:10px;margin-bottom:6px;text-align:center'>
                    <span style='font-size:0.65rem;color:#8B949E;font-family:monospace'>Source: CNN Business (Official 1-Year Database)</span><br>
                    <span style='font-size:0.65rem;color:#8B949E;font-family:monospace;font-weight:bold'>Last updated: {last_updated_str}</span>
                </div>
                """, unsafe_allow_html=True)
                
        # 공통 상세 요약 안내 문구
        st.markdown(f"""
        <div style='background:#10141b;border:1px solid #30363D;border-radius:8px;padding:10px;margin-bottom:12px'>
            <p style='color:#8B949E;font-size:0.7rem;margin:0;line-height:1.4;text-align:center'>
                ℹ️ {desc}
            </p>
        </div>
        """, unsafe_allow_html=True)

    draw_fear_greed_index_card()
    
    # 좌우 컬럼 높이 오와열 정렬을 위해 약간의 여백 추가
    st.markdown("<br>" * 1, unsafe_allow_html=True)

# ================================================================
# 리포트 다운로드 및 하단 면책 조항
# ================================================================
def generate_pdf_html():
    html = f"""<html><head><meta charset='utf-8'><style>
    body{{font-family:Arial,sans-serif;background:#0D1117;color:#C9D1D9;padding:40px}}
    h1{{color:#E6EDF3}} h2{{color:#FFD700}} h3{{color:#58A6FF}}
    table{{width:100%;border-collapse:collapse;margin:12px 0}}
    td,th{{border:1px solid #30363D;padding:8px;text-align:left}}
    .green{{color:#4ade80}} .red{{color:#f87171}} .yellow{{color:#fbbf24}}
    </style></head><body>
    <h1>{ov['name']} ({ticker}) — Deep Dive Analysis</h1>
    <p>분석일: {datetime.now().strftime('%Y-%m-%d')} | 현재가: ${ov['current_price']}</p>
    <h2>종합 등급: {grade} ({total_score:.1f}/100)</h2>
    <h3>스코어링</h3><table><tr><th>항목</th><th>점수</th></tr>
    {''.join(f"<tr><td>{k}</td><td>{v}/5</td></tr>" for k,v in scores.items())}
    </table>
    <h3>BULL ${targets['bull']} | BASE ${targets['base']} | BEAR ${targets['bear']}</h3>
    <h3>최종 판단</h3><p>{verdict['short_term']}<br>{verdict['mid_term']}<br>{verdict['long_term']}<br>{verdict['buy_zone']}</p>
    </body></html>"""
    return html

def generate_full_pdf_html():
    # 1. SWOT 아이템 가공
    swot_s = "".join([f"<li>{s}</li>" for s in swot.get('strength',[])])
    swot_w = "".join([f"<li>{s}</li>" for s in swot.get('weakness',[])])
    swot_o = "".join([f"<li>{s}</li>" for s in swot.get('opportunity',[])])
    swot_t = "".join([f"<li>{s}</li>" for s in swot.get('threat',[])])
    
    # 2. 매수 핵심 강점 & 매도 리스크 요인 가공
    bull_items = "".join([
        f"<div style='display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #21262D;'>"
        f"<span style='background:#0e4429;color:#3fb950;font-size:0.75rem;padding:3px 8px;border-radius:12px;font-weight:bold;'>{item['tag']}</span>"
        f"<span style='font-size:0.9rem;'>{item['text']}</span></div>" 
        for item in bull_case
    ])
    bear_items = "".join([
        f"<div style='display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #21262D;'>"
        f"<span style='background:#4c1514;color:#ff7b72;font-size:0.75rem;padding:3px 8px;border-radius:12px;font-weight:bold;'>{item['tag']}</span>"
        f"<span style='font-size:0.9rem;'>{item['text']}</span></div>" 
        for item in bear_case
    ])
    
    # 3. 주요 재무 지표 가공 (DataFrame 객체 직접 출력을 방지하고 정갈한 핵심 지표들로 매핑)
    fin_list = [
        ("시가총액 (Market Cap)", fmt_mcap(ov.get('market_cap')) if ov.get('market_cap') else "N/A"),
        ("52주 가격 범위 (52W Range)", f"${ov.get('low_52w')} - ${ov.get('high_52w')}"),
        ("P/E 비율 (Price to Earnings)", f"{ov.get('pe_ratio', 0):.1f}x ({ov.get('pe_eval', 'N/A')})" if ov.get('pe_ratio') else "산정 불가"),
        ("P/S 비율 (Price to Sales)", f"{ov.get('ps_ratio', 0):.1f}x ({ov.get('ps_eval', 'N/A')})" if ov.get('ps_ratio') else "산정 불가"),
        ("자기자본이익률 (ROE)", f"{ov.get('roe', 0)*100:.2f}%" if ov.get('roe') else "N/A"),
        ("매출 성장률 (Revenue Growth)", f"{ov.get('revenue_growth', 0)*100:.2f}%" if ov.get('revenue_growth') else "N/A"),
        ("순이익 성장률 (Earnings Growth)", f"{ov.get('earnings_growth', 0)*100:.2f}%" if ov.get('earnings_growth') else "N/A"),
        ("총마진율 (Gross Margin)", f"{ov.get('gross_margins', 0)*100:.2f}%" if ov.get('gross_margins') else "N/A"),
        ("영업마진율 (Operating Margin)", f"{ov.get('operating_margin', 0)*100:.2f}%" if ov.get('operating_margin') else "N/A"),
        ("순이익률 (Net Profit Margin)", f"{ov.get('profit_margin', 0)*100:.2f}%" if ov.get('profit_margin') else "N/A"),
        ("총 부채 (Total Debt)", fmt_mcap(ov.get('total_debt')) if ov.get('total_debt') else "N/A"),
        ("총 현금 (Total Cash)", fmt_mcap(ov.get('total_cash')) if ov.get('total_cash') else "N/A"),
        ("잉여현금흐름 (Free Cash Flow)", fmt_mcap(ov.get('free_cashflow')) if ov.get('free_cashflow') else "N/A"),
        ("배당수익률 (Dividend Yield)", f"{ov.get('dividend_yield', 0)*100:.2f}%" if ov.get('dividend_yield') else "0.00%"),
    ]
    fin_rows = "".join([
        f"<tr><td style='border:1px solid #30363D;padding:10px;font-size:0.9rem;'>{label}</td>"
        f"<td style='border:1px solid #30363D;padding:10px;font-size:0.9rem;font-weight:bold;color:#58A6FF;'>{val}</td></tr>"
        for label, val in fin_list
    ])

    html = f"""<html>
<head>
<meta charset='utf-8'>
<title>{ov['name']} ({ticker}) 퀀트 종합 정밀 의사결정 리포트</title>
<style>
    body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #0D1117;
        color: #C9D1D9;
        max-width: 1000px;
        margin: 0 auto;
        padding: 40px 20px;
    }}
    .header {{
        border-bottom: 2px solid #30363D;
        padding-bottom: 24px;
        margin-bottom: 30px;
    }}
    .header h1 {{
        color: #E6EDF3;
        margin: 0;
        font-size: 2.2rem;
    }}
    .header p {{
        color: #8B949E;
        margin: 6px 0 0 0;
        font-size: 0.95rem;
    }}
    .score-badge {{
        background: linear-gradient(135deg, #1f2937, #111827);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px;
        display: inline-flex;
        align-items: center;
        gap: 30px;
        margin-bottom: 30px;
    }}
    .score-badge .score {{
        font-size: 2.5rem;
        font-weight: bold;
        color: #58A6FF;
    }}
    .score-badge .grade {{
        font-size: 1.8rem;
        font-weight: bold;
        color: #4ade80;
        border-left: 2px solid #30363D;
        padding-left: 25px;
    }}
    h2 {{
        color: #FFD700;
        font-size: 1.4rem;
        margin-top: 40px;
        border-left: 4px solid #58A6FF;
        padding-left: 10px;
    }}
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 20px;
    }}
    .card {{
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 20px;
    }}
    .swot-s {{ border-top: 4px solid #2ea44f; }}
    .swot-w {{ border-top: 4px solid #f85149; }}
    .swot-o {{ border-top: 4px solid #1f6feb; }}
    .swot-t {{ border-top: 4px solid #d29922; }}
    
    .swot-title {{
        font-weight: bold;
        margin-bottom: 12px;
        font-size: 1rem;
        color: #F0F6FC;
    }}
    ul {{
        padding-left: 20px;
        margin: 0;
    }}
    li {{
        margin-bottom: 6px;
        font-size: 0.9rem;
        line-height: 1.4;
    }}
    .scenario-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 20px;
    }}
    .scenario-card {{
        text-align: center;
        padding: 15px;
        border-radius: 8px;
    }}
    .bull-bg {{ background: #0e4429; border: 1px solid #238636; }}
    .base-bg {{ background: #161b22; border: 1px solid #30363d; }}
    .bear-bg {{ background: #4c1514; border: 1px solid #da3633; }}
    
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }}
    th, td {{
        border: 1px solid #30363D;
        padding: 10px;
        text-align: left;
        font-size: 0.9rem;
    }}
    th {{
        background-color: #161B22;
        color: #F0F6FC;
    }}
    .verdict-box {{
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 20px;
        line-height: 1.6;
        font-size: 0.95rem;
    }}
</style>
</head>
<body>
    <div class="header">
        <h1>{ov['name']} ({ticker}) 퀀트 정밀 의사결정 리포트</h1>
        <p>분석 기준일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 현재가: ${ov['current_price']}</p>
    </div>
    
    <div class="score-badge">
        <div>
            <div style="font-size: 0.8rem; color: #8B949E; margin-bottom: 4px;">QUANT SCORE</div>
            <div class="score">{total_score:.1f} / 100</div>
        </div>
        <div class="grade">
            <div style="font-size: 0.8rem; color: #8B949E; margin-bottom: 4px;">DECISION GRADE</div>
            <div>{grade}</div>
        </div>
        <div style="border-left: 2px solid #30363D; padding-left: 25px;">
            <div style="font-size: 0.8rem; color: #8B949E; margin-bottom: 4px;">ENTRY SCORE</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #FFD700;">{entry_score:.1f} / 100</div>
        </div>
    </div>
    
    <h2>1. 최종 매매 의사결정 및 투자 가이드</h2>
    <div class="verdict-box">
        <strong>단기적 관점:</strong> {verdict['short_term']}<br><br>
        <strong>중기적 관점:</strong> {verdict['mid_term']}<br><br>
        <strong>장기적 관점:</strong> {verdict['long_term']}<br><br>
        <strong>정밀 진입 밴드 (Buy Zone):</strong> <span style="color:#FFD700; font-weight:bold;">{verdict['buy_zone']}</span><br>
        <strong>지정 손절가 (Stop Loss):</strong> <span style="color:#FF4444; font-weight:bold;">{verdict.get('stop_loss','N/A')}</span>
    </div>
    
    <h2>2. 시나리오별 가치 평가 (Target Price)</h2>
    <div class="scenario-grid">
        <div class="scenario-card bull-bg">
            <div style="color: #3fb950; font-weight: bold;">🐂 BULL 시나리오</div>
            <div style="font-size: 2rem; font-weight: bold; margin: 10px 0; color: #3fb950;">${targets['bull']}</div>
            <div style="font-size: 0.8rem; color: #86efac;">현재가 대비 {targets['bull_pct']:+.1f}%</div>
        </div>
        <div class="scenario-card base-bg">
            <div style="color: #fbbf24; font-weight: bold;">■ BASE 시나리오</div>
            <div style="font-size: 2rem; font-weight: bold; margin: 10px 0; color: #fbbf24;">${targets['base']}</div>
            <div style="font-size: 0.8rem; color: #fde047;">현재가 대비 {targets['base_pct']:+.1f}%</div>
        </div>
        <div class="scenario-card bear-bg">
            <div style="color: #ff7b72; font-weight: bold;">🐻 BEAR 시나리오</div>
            <div style="font-size: 2rem; font-weight: bold; margin: 10px 0; color: #ff7b72;">${targets['bear']}</div>
            <div style="font-size: 0.8rem; color: #fca5a5;">현재가 대비 {targets['bear_pct']:+.1f}%</div>
        </div>
    </div>
    
    <h2>3. 매수 강점 vs 리스크 핵심 논거</h2>
    <div class="grid-2">
        <div class="card" style="border-left: 4px solid #2ea44f;">
            <div class="swot-title" style="color: #3fb950;">✔ 매수 핵심 강점</div>
            {bull_items}
        </div>
        <div class="card" style="border-left: 4px solid #f85149;">
            <div class="swot-title" style="color: #ff7b72;">✘ 매도 리스크 요인</div>
            {bear_items}
        </div>
    </div>
    
    <h2>4. SWOT 분석 및 리스크 매트릭스</h2>
    <div class="grid-2">
        <div class="card swot-s">
            <div class="swot-title">STRENGTH (강점)</div>
            <ul>{swot_s}</ul>
        </div>
        <div class="card swot-w">
            <div class="swot-title">WEAKNESS (약점)</div>
            <ul>{swot_w}</ul>
        </div>
        <div class="card swot-o">
            <div class="swot-title">OPPORTUNITY (기회)</div>
            <ul>{swot_o}</ul>
        </div>
        <div class="card swot-t">
            <div class="swot-title">THREAT (위협)</div>
            <ul>{swot_t}</ul>
        </div>
    </div>
    
    <h2>5. 핵심 펀더멘털 및 기술적 스코어링</h2>
    <div class="grid-2">
        <div>
            <h3 style="color:#58A6FF; margin: 5px 0; font-size: 1.1rem;">정밀 펀더멘털 스코어</h3>
            <table>
                <tr><th>평가 항목</th><th>스코어</th></tr>
                {''.join(f"<tr><td>{k}</td><td>{v}/5</td></tr>" for k,v in scores.items())}
            </table>
        </div>
        <div>
            <h3 style="color:#FFD700; margin: 5px 0; font-size: 1.1rem;">기업 주요 펀더멘털 데이터</h3>
            <table>
                <tr><th>지표명</th><th>값</th></tr>
                {fin_rows}
            </table>
        </div>
    </div>
    
    <div style="text-align: center; color: #8B949E; font-size: 0.8rem; margin-top: 50px; border-top: 1px solid #30363D; padding-top: 20px;">
        본 보고서는 정량적 퀀트 모델링 및 파생상품 흐름 분석에 근거하여 자동 생성되었습니다. 투자 결정의 최종 책임은 본인에게 있습니다.
    </div>
</body>
</html>"""
    return html

pdf_html = generate_pdf_html()
full_pdf_html = generate_full_pdf_html()
st.markdown("<br>", unsafe_allow_html=True)

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    st.download_button("📥 분석 리포트 요약본 HTML 다운로드", data=pdf_html, file_name=f"{ticker}_deep_analysis_{datetime.now().strftime('%Y%m%d')}.html", mime="text/html")

with col_dl2:
    st.download_button("📥 분석 리포트 전체 HTML 다운로드", data=full_pdf_html, file_name=f"{ticker}_full_analysis_{datetime.now().strftime('%Y%m%d')}.html", mime="text/html")

st.markdown(f"""<div style='text-align:center;padding:20px;color:#484F58;font-size:.7rem;border-top:1px solid #21262D;margin-top:24px'>
{ov['name']} ({ticker}) 종합 분석 | 분석 기준일: {datetime.now().strftime('%Y.%m.%d')} | 
본 자료는 투자 권고가 아닙니다. 투자의 책임은 투자자 본인에게 있습니다.
</div>""", unsafe_allow_html=True)

