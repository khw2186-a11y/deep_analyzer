# ============================================================
# main_dashboard.py - Quantitative Volatility & Flow Analytics Matrix
# ============================================================
# Grafana/Datadog 스타일의 데이터 모니터링 콘솔 UI입니다.
# engine.py에서 계산된 데이터를 시각화합니다.
# 실행 방법: python -m streamlit run main_dashboard.py
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 같은 폴더에 있는 백엔드 엔진 파일을 불러옵니다.
import engine
import importlib
importlib.reload(engine) # 수정 사항 즉시 반영을 위해 강제 리로드

import os
print(f"DEBUG: engine file location: {os.path.abspath(engine.__file__)}")

# ============================================================
# [1] 페이지 기본 설정
# ============================================================
st.set_page_config(
    page_title="QV&F Analytics Matrix",
    page_icon="◈",
    layout="wide"  # 화면 전체 너비 사용
)

# ============================================================
# [2] 커스텀 CSS 스타일 (다크 모니터링 콘솔 테마)
# ============================================================
# Streamlit 기본 스타일 위에 추가로 CSS를 입혀서
# Grafana/Datadog 같은 전문적인 느낌을 줍니다.
st.markdown("""
<style>
    /* 메인 컨테이너 배경을 좀 더 어둡게 */
    .stApp {
        background-color: #0E1117;
    }

    /* KPI 메트릭 카드 스타일 */
    div[data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label {
        color: #8B949E !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #00BFA5 !important;
        font-size: 1.8rem !important;
        font-weight: 700;
    }

    /* 테이블 헤더 스타일 */
    .stDataFrame thead th {
        background-color: #161B22 !important;
        color: #00BFA5 !important;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
    }

    /* 섹션 타이틀 스타일 */
    h1, h2, h3 {
        color: #C9D1D9 !important;
        font-weight: 600 !important;
    }

    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #0D1117;
        border-right: 1px solid #30363D;
    }

    /* 구분선 색상 */
    hr {
        border-color: #30363D !important;
    }

    /* Expander(펼치기/접기) 패널 스타일 */
    .streamlit-expanderHeader {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px;
        color: #C9D1D9 !important;
    }

    /* 성공/경고/정보 알림 박스 스타일 오버라이드 */
    .stAlert {
        border-radius: 6px;
    }

    /* 사이드바 멀티셀렉트(종목 선택) 태그 글씨 크기 축소 */
    div[data-baseweb="tag"] {
        font-size: 0.7rem !important;
        height: 18px !important;
        background-color: #21262d !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="select"] span {
        font-size: 0.75rem !important;
    }

    /* 상단 헤더 영역 커스텀 */
    .console-header {
        background: linear-gradient(135deg, #0D1117 0%, #161B22 100%);
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 24px 32px;
        margin-bottom: 24px;
    }
    .console-header h1 {
        color: #00BFA5 !important;
        font-size: 1.6rem !important;
        margin-bottom: 4px;
        font-family: 'Courier New', monospace;
        letter-spacing: 1px;
    }
    .console-header p {
        color: #8B949E;
        font-size: 0.85rem;
        margin: 0;
    }
    .status-badge {
        display: inline-block;
        background-color: #238636;
        color: #FFFFFF;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-right: 12px;
        letter-spacing: 0.5px;
    }
    .status-text {
        color: #8B949E;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# [3] Control Panel (사이드바)
# ============================================================
st.sidebar.markdown(f"### ⚙ Control Panel (v6.1)")
st.sidebar.markdown(f"**Engine Version:** `{engine.VERSION if hasattr(engine, 'VERSION') else 'UNKNOWN'}`")

# 캐시 초기화 버튼 추가 (문구 수정 및 줄바꿈 적용)
if st.sidebar.button("♻ Force Refresh\n\n(데이터 강제 새로고침)"):
    st.cache_data.clear()
    importlib.reload(engine) # 버튼 클릭 시에도 강제 리로드
    st.rerun()

# 종목(노드) 선택
@st.cache_data(ttl=3600, show_spinner=False)
def get_universe_v6():
    """Yahoo Finance Most Active Top 100 종목을 가져오는 캐시 함수 (v6)"""
    return engine.fetch_most_active_tickers(count=100)

UNIVERSE = get_universe_v6()

st.sidebar.markdown(f"**Asset Node Selection (분석 대상 선택) — {len(UNIVERSE)}개 로드됨**")
selected_tickers = st.sidebar.multiselect(
    "분석 대상 노드를 선택하세요",
    options=UNIVERSE,
    default=UNIVERSE,
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Filter Parameters (필터 설정값)**")

# VCT 필터 파라미터 조정 슬라이더
iv_rank_threshold = st.sidebar.slider(
    "IV Rank Threshold (변동성 순위 기준값, %)",
    min_value=5, max_value=50, value=25,
    help="이 값 미만의 IV Rank를 가진 노드만 VCT로 분류합니다"
)
rsi_range = st.sidebar.slider(
    "RSI Detection Range (상대강도지수 탐지 범위)",
    min_value=10, max_value=90, value=(30, 55),
    help="이 RSI 범위 내의 노드를 상승 전환 직전으로 판단합니다"
)
min_vct_score = st.sidebar.select_slider(
    "Minimum VCT Score (최소 타깃 점수 선택)",
    options=[2, 3, 4],
    value=3,
    help="선택한 점수 이상의 조건을 만족하는 종목만 VCT 섹션에 표시합니다 (최대 4점)"
)

# 종목 선택 안 했을 때 예외 처리
if not selected_tickers:
    st.warning("⚠ Control Panel(제어 패널)에서 최소 1개의 Asset Node(분석 대상)를 선택해 주세요.")
    st.stop()

# ============================================================
# [4] 데이터 로드 및 분석 실행
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_and_analyze_v6(tickers):
    """데이터 수집 + 전체 분석을 실행하고 캐시에 저장합니다. (v6)"""
    data_dict = engine.fetch_stock_data(tickers, period='1y')
    analyzed_df = engine.run_full_analysis(data_dict)
    return data_dict, analyzed_df

with st.spinner("◈ Syncing data nodes (데이터 노드 동기화 및 정량 분석 중)..."):
    data_dict, analyzed_df = load_and_analyze_v6(selected_tickers)

# 데이터 정렬 적용 (Sorting 기능 삭제됨 - 시가총액순 기본 정렬 유지)
if not analyzed_df.empty:
    if 'Market Cap (시가총액)' in analyzed_df.columns:
        analyzed_df = analyzed_df.sort_values('Market Cap (시가총액)', ascending=False)

# ============================================================
# [5] 콘솔 헤더 (타이틀 영역 + Fear & Greed Index)
# ============================================================
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
node_count = len(analyzed_df) if not analyzed_df.empty else 0

# Fear & Greed Index 데이터 로드
fg_data = engine.get_fear_and_greed_index()
fg_val = fg_data['value']
fg_rating = fg_data['rating']

# 타이틀과 게이지를 나란히 배치하기 위해 컬럼 분할
head_col1, head_col2 = st.columns([3, 1])

with head_col1:
    st.markdown(f"""
    <div class="console-header">
        <h1>◈ Quantitative Volatility & Flow Analytics Matrix</h1>
        <p style='color:#8B949E; font-size:0.9rem; margin-top:2px;'>정량적 변동성 & 자금 흐름 분석 매트릭스 (Strategic Engineering Console)</p>
        <p>
            <span class="status-badge">● LIVE</span>
            <span class="status-text">Pipeline Sync: {now} KST &nbsp;|&nbsp; Nodes: {node_count} &nbsp;|&nbsp; Bilingual System Enabled</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

with head_col2:
    # 1. 지수 단계별 테마 색상 정의 (시인성 중심)
    # Extreme Fear: 빨강, Fear: 주황, Neutral: 회색, Greed: 연두, Extreme Greed: 진초록
    theme_colors = {
        "Extreme Fear": "#FF1744", 
        "Fear": "#FF9100", 
        "Neutral": "#E0E0E0", 
        "Greed": "#00E676", 
        "Extreme Greed": "#00C853"
    }
    # 현재 상태에 맞는 색상 선택
    current_color = theme_colors.get(fg_rating, "#00BFA5")
    fg_source = fg_data.get('source', 'Unknown')

    # 2. 게이지 시각화 (디자인 강화 버전)
    fig_fg = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = fg_val,
        domain = {'x': [0, 1], 'y': [0, 1]},
        # 숫자 폰트 크기 및 색상 조정
        number = {
            'font': {'size': 42, 'color': current_color, 'family': 'Arial Black'},
            'suffix': ""
        },
        title = {
            'text': f"<b style='font-size:1.4em; color:#FFFFFF;'>FEAR & GREED</b><br>"
                    f"<b style='font-size:1.2em; color:{current_color};'>{fg_rating.upper()}</b><br>"
                    f"<span style='font-size:0.6em; color:#8B949E;'>Source: {fg_source}</span>",
            'font': {'family': 'Courier New'}
        },
        gauge = {
            'axis': {
                'range': [None, 100], 
                'tickwidth': 2, 
                'tickcolor': "#484F58",
                'tickfont': {'size': 12, 'color': '#8B949E'}
            },
            # 바 두께 및 색상 (현재 단계 색상으로 동적 변경)
            'bar': {'color': current_color, 'thickness': 0.3},
            'bgcolor': "rgba(33, 38, 45, 0.5)",
            'borderwidth': 1,
            'bordercolor': "#30363D",
            'steps': [
                {'range': [0, 25], 'color': 'rgba(255, 23, 68, 0.2)'},
                {'range': [25, 45], 'color': 'rgba(255, 145, 0, 0.2)'},
                {'range': [45, 55], 'color': 'rgba(224, 224, 224, 0.1)'},
                {'range': [55, 75], 'color': 'rgba(0, 230, 118, 0.2)'},
                {'range': [75, 100], 'color': 'rgba(0, 200, 83, 0.2)'}
            ],
            # 현재 위치를 가리키는 포인터(흰색 선) 강화
            'threshold': {
                'line': {'color': "#FFFFFF", 'width': 5},
                'thickness': 0.75,
                'value': fg_val
            }
        }
    ))
    
    fig_fg.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=220,
        margin=dict(l=30, r=30, t=60, b=10)
    )
    st.plotly_chart(fig_fg, use_container_width=True)

# ============================================================
# [6] 상단 KPI 메트릭 카드 (4개)
# ============================================================
if not analyzed_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    cols = analyzed_df.columns

    # KPI 1: 평균 변동성 (IV Rank)
    if 'IV Rank (변동성 순위)' in cols:
        avg_iv = analyzed_df['IV Rank (변동성 순위)'].mean()
        col1.metric("AVG VARIANCE (평균 변동성 순위)", f"{avg_iv:.1f}%")
    else:
        col1.metric("AVG VARIANCE", "N/A")

    # KPI 2: 상승 추세 지속 (Positive Drift)
    if 'Positive Drift (상승 추세 지속)' in cols:
        pos_drift_count = len(analyzed_df[analyzed_df['Positive Drift (상승 추세 지속)'] == True])
        col2.metric("POSITIVE DRIFT (상승 추세 지속)", f"{pos_drift_count} Nodes")
    else:
        col2.metric("POSITIVE DRIFT", "N/A")

    # KPI 3: 거래량 급증 (Volume Surge)
    if 'Volume Surge (거래량 급증)' in cols:
        surge_count = len(analyzed_df[analyzed_df['Volume Surge (거래량 급증)'] == True])
        col3.metric("VOLUME SURGE (거래량 급증)", f"{surge_count} Anomalies")
    else:
        col3.metric("VOLUME SURGE", "N/A")

    # KPI 4: 핵심 수축 타깃 (BB Contract) - 사용자 요청에 따른 단일 조건 카운트로 변경
    if 'BB Contract (변동성 수축)' in cols:
        contract_count = len(analyzed_df[analyzed_df['BB Contract (변동성 수축)'] == True])
        col4.metric("CORE CONTRACTION (핵심 수축 타깃)", f"{contract_count} Nodes")
    else:
        col4.metric("CORE CONTRACTION", "N/A")

# [상단 요약 섹션]
if not analyzed_df.empty:
    st.markdown("---")
    # 핵심 수축 타깃 리스트 추출
    contraction_targets = analyzed_df[analyzed_df['BB Contract (변동성 수축)'] == True]['Node (자산명)'].tolist()
    
    col_summ1, col_summ2 = st.columns([1, 3])
    with col_summ1:
        st.write(f"📡 **Nodes Sync:** `{len(analyzed_df)}` Active")
    with col_summ2:
        if contraction_targets:
            targets_str = ", ".join(contraction_targets)
            st.success(f"**◉ 핵심 수축 타깃 (Energy Contraction):** {targets_str}")
        else:
            st.info("◉ 현재 임계치 이하로 수축된 핵심 노드가 없습니다.")

# ============================================================
# [7] Signal Matrix - 전체 노드 데이터 테이블
# ============================================================
st.markdown("---")
st.markdown("### 📡 Full Signal Matrix (전체 분석 매트릭스) — Bilingual Information System")

if not analyzed_df.empty:
    display_df = analyzed_df.copy()
    cols = display_df.columns

    # 불리언 값을 시각적 기호로 변환 (사용자 요청 기호 복구: ↗, ⚡, ◉, ✳)
    if 'Positive Drift (상승 추세 지속)' in cols:
        display_df['Positive Drift (상승 추세 지속)'] = display_df['Positive Drift (상승 추세 지속)'].map({True: '↗', False: '—'})
    if 'Volume Surge (거래량 급증)' in cols:
        display_df['Volume Surge (거래량 급증)'] = display_df['Volume Surge (거래량 급증)'].map({True: '⚡', False: '—'})
    if 'BB Contract (변동성 수축)' in cols:
        display_df['BB Contract (변동성 수축)'] = display_df['BB Contract (변동성 수축)'].map({True: '◉', False: '—'})
    if 'MACD Cross (추세 전환)' in cols:
        display_df['MACD Cross (추세 전환)'] = display_df['MACD Cross (추세 전환)'].map({True: '✳', False: '—'})

    # 시총 가독성 개선
    if 'Market Cap (시가총액)' in cols:
        display_df['Market Cap (시가총액)'] = display_df['Market Cap (시가총액)'].apply(
            lambda x: f"${x/1e9:.1f}B" if x >= 1e9 else (f"${x/1e6:.1f}M" if x >= 1e6 else f"${x}")
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "Node (자산명)": st.column_config.TextColumn("Node (자산명)", width="small", help="분석 대상 주식의 티커(Ticker) 명칭입니다."),
            "Price (현재가)": st.column_config.NumberColumn("Price (현재가)", format="$%.2f", help="가장 최근 거래일의 마감 가격입니다."),
            "Market Cap (시가총액)": st.column_config.TextColumn("Market Cap (시가총액)", width="medium", help="회사의 전체 가치(시가총액)를 나타냅니다."),
            "Momentum (1개월 모멘텀)": st.column_config.NumberColumn(
                "Momentum (모멘텀)", 
                format="%.2f%%", 
                help="최근 1개월(20거래일) 동안 가격이 얼마나 올랐는지(혹은 내렸는지) 추세의 강도를 나타냅니다."
            ),
            "RSI (상대강도)": st.column_config.ProgressColumn(
                "RSI (상대강도)", 
                min_value=0, max_value=100, format="%.1f",
                help="과매수(70이상) 또는 과매도(30이하) 상태를 측정하는 지표입니다."
            ),
            "IV Rank (변동성 순위)": st.column_config.ProgressColumn(
                "IV Rank (변동성 순위)", 
                min_value=0, max_value=100, format="%.1f%%",
                help="과거 1년 변동성 범위 중 현재 변동성의 상대적 위치입니다. 낮을수록 옵션 가격이 저렴함을 의미합니다."
            ),
            "Vol Ratio (거래 배수)": st.column_config.NumberColumn(
                "Vol Ratio (거래 배수)", 
                format="%.2fx",
                help="최근 3일 평균 거래량이 지난 20일 평균 거래량보다 몇 배 더 터졌는지 나타내는 수급 집중도 지표입니다."
            ),
            "Positive Drift (상승 추세 지속)": st.column_config.TextColumn(
                "↗", 
                help="Positive Drift: 주가가 20일 이동평균선 위에 있으며 상승 추세를 안정적으로 유지하고 있음을 뜻합니다."
            ),
            "Volume Surge (거래량 급증)": st.column_config.TextColumn(
                "⚡", 
                help="Volume Surge: 평소보다 거래량이 1.5배 이상 폭발하며 강력한 자금 흐름(Flow)이 유입된 상태입니다."
            ),
            "BB Contract (변동성 수축)": st.column_config.TextColumn(
                "◉", 
                help="BB Contract: 볼린저 밴드 폭이 좁아지며 에너지가 응축된 상태입니다. 조만간 위나 아래로 큰 움직임이 나올 가능성이 높습니다."
            ),
            "MACD Cross (추세 전환)": st.column_config.TextColumn(
                "✳", 
                help="MACD Cross: 하락 추세를 멈추고 상승 추세로 돌아설 때 나타나는 골든크로스 신호입니다."
            ),
        }
    )
else:
    st.info("◈ 데이터 노드가 로드되지 않았습니다.")

# ============================================================
# [8] Variance Contraction Targets (VCT) 섹션
# ============================================================
st.markdown("---")
st.markdown("### 🎯 Strategic Variance Contraction Targets (VCT, 전략적 변동성 수축 타깃)")
st.markdown(
    f"*Detection Logic: Target Score ≥ {min_vct_score}/4 (IV Rank < {iv_rank_threshold}% | "
    f"RSI {rsi_range[0]}–{rsi_range[1]} | MACD Cross | BB Contract)*"
)

if not analyzed_df.empty:
    cols = analyzed_df.columns
    vct_cols = ['IV Rank (변동성 순위)', 'RSI (상대강도)', 'MACD Cross (추세 전환)', 'BB Contract (변동성 수축)', 'Market Cap (시가총액)']
    
    if all(c in cols for c in vct_cols):
        # 전체 종목에 대해 점수 계산
        vct_scoring_df = analyzed_df.copy()
        vct_scoring_df['VCT_Score'] = 0
        
        vct_scoring_df.loc[(vct_scoring_df['IV Rank (변동성 순위)'].notna()) & (vct_scoring_df['IV Rank (변동성 순위)'] < iv_rank_threshold), 'VCT_Score'] += 1
        vct_scoring_df.loc[(vct_scoring_df['RSI (상대강도)'].notna()) & (vct_scoring_df['RSI (상대강도)'] >= rsi_range[0]) & (vct_scoring_df['RSI (상대강도)'] <= rsi_range[1]), 'VCT_Score'] += 1
        vct_scoring_df.loc[vct_scoring_df['MACD Cross (추세 전환)'] == True, 'VCT_Score'] += 1
        vct_scoring_df.loc[vct_scoring_df['BB Contract (변동성 수축)'] == True, 'VCT_Score'] += 1
        
        # 사용자가 선택한 최소 점수 이상만 필터링
        vct_display = vct_scoring_df[vct_scoring_df['VCT_Score'] >= min_vct_score].copy()
        
        # 정렬: 1순위 타깃 점수(내림차순), 2순위 시가총액(내림차순)
        vct_display = vct_display.sort_values(by=['VCT_Score', 'Market Cap (시가총액)'], ascending=[False, False])

        if vct_display.empty:
            st.warning(f"◈ 현재 점수 {min_vct_score}점 이상을 충족하는 VCT 노드가 감지되지 않았습니다. 사이드바의 필터나 최소 점수를 조정해 보십시오.")
        else:
            # 4점 만점 종목이 있는지 확인하여 메시지 출력 (사용자 요청 수정)
            high_score_count = len(vct_display[vct_display['VCT_Score'] == 4])
            if high_score_count > 0:
                st.success(f"◈ 점수 {min_vct_score}점 이상의 전략적 타깃 {len(vct_display)}개 노드가 감지되었습니다. (그 중 4점 만점: {high_score_count}개)")
            else:
                st.info(f"◈ 4점 만점 노드가 없어 사용자가 선택한 최소 기준({min_vct_score}점 이상)에 맞는 노드들을 표시합니다.")

            # VCT 결과 표시
            for _, row in vct_display.iterrows():
                ticker = row['Node (자산명)']
                score = int(row['VCT_Score'])
                score_bar = "█" * score + "░" * (4 - score)

                col_a, col_b, col_c = st.columns([1, 1, 1])
                col_a.metric(f"{ticker}", f"${row['Price (현재가)']}")
                col_b.metric("IV Rank (변동성 순위)", f"{row['IV Rank (변동성 순위)']}%" if pd.notna(row['IV Rank (변동성 순위)']) else "N/A")
                col_c.metric("VCT Score (타깃 점수)", f"{score_bar} ({score}/4)")

                with st.expander(f"📋 {ticker} — Detailed Variance Analysis Report"):
                    report = engine.generate_analysis_report(row)
                    st.markdown(report, unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.error(f"◈ 분석 데이터의 컬럼 구조가 일치하지 않습니다. (발견된 컬럼: {list(cols)})")
        st.info("상단 'Force Refresh' 버튼을 눌러주세요.")

# ============================================================
# [9] OI Profile - 양방향 바 차트
# ============================================================
st.markdown("### 📊 OI Profile (미결제약정 프로파일) — Bidirectional Flow Visualization (양방향 자금 흐름 시각화)")

# [수정] VCT 타깃 중 1순위 종목을 기본 선택값으로 설정 (전략적 자동화)
default_ticker_index = 0
if not analyzed_df.empty:
    # VCT 점수 재계산 및 정렬 (사전에 정의된 필터 기준 적용)
    vct_check = analyzed_df.copy()
    vct_check['VCT_Score'] = 0
    vct_check.loc[(vct_check['IV Rank (변동성 순위)'].notna()) & (vct_check['IV Rank (변동성 순위)'] < iv_rank_threshold), 'VCT_Score'] += 1
    vct_check.loc[(vct_check['RSI (상대강도)'].notna()) & (vct_check['RSI (상대강도)'] >= rsi_range[0]) & (vct_check['RSI (상대강도)'] <= rsi_range[1]), 'VCT_Score'] += 1
    vct_check.loc[vct_check['MACD Cross (추세 전환)'] == True, 'VCT_Score'] += 1
    vct_check.loc[vct_check['BB Contract (변동성 수축)'] == True, 'VCT_Score'] += 1
    
    vct_check = vct_check.sort_values(by=['VCT_Score', 'Market Cap (시가총액)'], ascending=[False, False])
    if not vct_check.empty:
        top_vct_ticker = vct_check.iloc[0]['Node (자산명)']
        if top_vct_ticker in selected_tickers:
            default_ticker_index = selected_tickers.index(top_vct_ticker)

# 차트를 볼 종목 선택
oi_ticker = st.selectbox(
    "Open Interest(미결제약정) 프로파일을 확인할 노드를 선택하세요:",
    selected_tickers,
    index=default_ticker_index, # VCT 1순위 자동 선택
    key="oi_select"
)

if oi_ticker:
    with st.spinner(f"◈ {oi_ticker} 파생 데이터 매트릭스 동기화 중..."):
        opt_data = engine.get_options_chain_with_oi(oi_ticker)

    if opt_data:
        calls_oi = opt_data['calls']
        puts_oi = opt_data['puts']
        max_pain = opt_data['max_pain']
        current_price = opt_data['current_price']

        # 양방향 바 차트 생성
        fig_oi = go.Figure()

        # 오른쪽: Call OI (청록색, 양의 값)
        fig_oi.add_trace(go.Bar(
            y=calls_oi['strike'],
            x=calls_oi['openInterest'],
            name='Call OI (콜 미결제약정)',
            orientation='h',
            marker_color='rgba(0, 191, 165, 0.7)',
            marker_line_color='#00BFA5',
            marker_line_width=1
        ))

        # 왼쪽: Put OI (주황색, 음의 값으로 반전)
        fig_oi.add_trace(go.Bar(
            y=puts_oi['strike'],
            x=-puts_oi['openInterest'],
            name='Put OI (풋 미결제약정)',
            orientation='h',
            marker_color='rgba(255, 152, 0, 0.7)',
            marker_line_color='#FF9800',
            marker_line_width=1
        ))

        # Max Pain 수평선
        fig_oi.add_hline(
            y=max_pain,
            line_dash="dash",
            line_color="#FF5252",
            line_width=2,
            annotation_text=f"Max Pain(최대고통가): ${max_pain}",
            annotation_position="top right"
        )

        # 현재가 수평선
        fig_oi.add_hline(
            y=current_price,
            line_dash="solid",
            line_color="#00BFA5",
            line_width=2,
            annotation_text=f"Current(현재가): ${current_price}",
            annotation_position="top left"
        )

        fig_oi.update_layout(
            title=f"{oi_ticker} — Strike-Level OI Distribution (만기: {opt_data['expiry']})",
            xaxis_title="← Put OI (풋 미결제약정) | Call OI (콜 미결제약정) →",
            yaxis_title="Strike Price (행사가, $)",
            template="plotly_dark",
            plot_bgcolor='rgba(14, 17, 23, 0.9)',
            paper_bgcolor='rgba(0,0,0,0)',
            barmode='overlay',
            height=600,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_oi, use_container_width=True)

        # OI 요약 정보 표시
        oi_col1, oi_col2, oi_col3, oi_col4 = st.columns(4)
        oi_col1.metric("Total Call OI (콜 총합)", f"{int(opt_data['total_call_oi']):,}")
        oi_col2.metric("Total Put OI (풋 총합)", f"{int(opt_data['total_put_oi']):,}")
        oi_col3.metric("PCR (풋/콜 비율)", f"{opt_data['pc_ratio']}")
        oi_col4.metric("Max Pain (최대고통가)", f"${max_pain}")

        # Greeks 계산
        if opt_data['avg_iv'] and opt_data['avg_iv'] > 0:
            T = 30 / 365
            r = 0.05
            delta, gamma = engine.compute_greeks_bsm(
                S=current_price, K=current_price, T=T, r=r, sigma=opt_data['avg_iv']
            )
            g_col1, g_col2 = st.columns(2)
            g_col1.metric("ATM Delta (등가격 델타)", f"{delta}")
            g_col2.metric("ATM Gamma (등가격 감마)", f"{gamma}")

        # ------------------------------------------------------------
        # [9-2] 옵션 수급 정밀 분석 리포트 (Bilingual Interpretation)
        # ------------------------------------------------------------
        st.markdown("---")
        st.markdown(f"#### 🧠 {oi_ticker} — Option Flow Intelligence (옵션 수급 정밀 분석)")
        
        col_r1, col_r2 = st.columns(2)
        
        # 1. Max Pain 및 현재가 위치 분석
        dist_to_maxpain = ((max_pain - current_price) / current_price) * 100
        with col_r1:
            st.markdown(f"**1. Max Pain Convergence (가격 수렴 분석)**")
            st.write(f"- 현재가: `${current_price}` / Max Pain: `${max_pain}`")
            if abs(dist_to_maxpain) < 3:
                st.write(f"- **상태:** 현재가가 Max Pain에 매우 근접해 있습니다. 만기일에 가격 변동이 억제되는 **핀 효과(Pinning Effect)**가 나타날 가능성이 큽니다.")
            elif dist_to_maxpain > 0:
                st.write(f"- **상태:** 현재가가 Max Pain보다 낮습니다. 만기일까지 주가를 위로 끌어올리려는 **자석 효과**가 발생할 수 있습니다.")
            else:
                st.write(f"- **상태:** 현재가가 Max Pain보다 높습니다. 만기일까지 주가에 하방 압력을 가하는 **차익 실현 및 헤지 물량**이 출현할 수 있습니다.")

        # 2. P/C Ratio 및 시장 심리
        pc_ratio = opt_data['pc_ratio']
        with col_r2:
            st.markdown(f"**2. P/C Ratio Sentiment (시장 심리 지표)**")
            st.write(f"- Put/Call Ratio: `{pc_ratio}`")
            if pc_ratio < 0.7:
                st.write("- **심리:** `Extremely Bullish` - 콜 옵션 매수가 압도적입니다. 시장이 강한 추가 상승을 기대하고 있습니다.")
            elif pc_ratio < 1.0:
                st.write("- **심리:** `Moderately Bullish` - 전반적으로 매수 우위의 시장 분위기입니다.")
            else:
                st.write("- **심리:** `Bearish/Hedging` - 풋 옵션 수요가 높습니다. 하락에 대한 공포 혹은 강력한 헤지 수요가 확인됩니다.")

        # 3. 전략적 제언
        max_call_strike = calls_oi.iloc[calls_oi['openInterest'].idxmax()]['strike']
        max_put_strike = puts_oi.iloc[puts_oi['openInterest'].idxmax()]['strike']
        
        st.info(f"""
        **🎯 Strategic Engineering Insight (전략적 제언):**  
        현재 {oi_ticker}의 수급 구조상 **${max_call_strike}** 부근에 대규모 콜 매도 벽(Call Wall)이 형성되어 상단을 제한하고 있으며, 
        하단은 **${max_put_strike}** 부근의 풋 매수 지지선(Put Support)이 방어하고 있습니다. 
        단기적으로 시장은 최대 고통가인 **${max_pain}** 부근으로 수렴하려는 성향을 보일 것이므로, 해당 가격대와 현재가의 괴리를 이용한 스프레드 전략이 유효할 수 있습니다.
        """)
    else:
        st.info(f"◈ {oi_ticker}의 파생 데이터 매트릭스를 구성할 수 없습니다.")

# ============================================================
# [10] Node Inspector - 개별 종목 상세 차트
# ============================================================
st.markdown("---")
st.markdown("### 🔍 Node Inspector (노드 상세 검사기) — Strategic Signal Visualization")

col_node1, col_node2 = st.columns([2, 1])
chart_ticker = col_node1.selectbox(
    "상세 분석할 노드를 선택하세요:",
    selected_tickers,
    index=default_ticker_index, # VCT 1순위 자동 선택
    key="chart_select"
)
timeframe = col_node2.selectbox(
    "타임프레임 선택:",
    options=["Daily (일봉)", "Weekly (주봉)", "Monthly (월봉)", "Yearly (년봉)"],
    index=0
)

if chart_ticker and chart_ticker in data_dict:
    # ------------------------------------------------------------
    # [10.1] 기업 정보 로드 (캐시 및 분석 데이터 우선 활용)
    # ------------------------------------------------------------
    @st.cache_data(ttl=3600)
    def get_exchange_rate():
        try:
            # 환율 정보는 안정적인 티커에서 추출
            ticker = yf.Ticker("USDKRW=X")
            hist = ticker.history(period="1d")
            return hist['Close'].iloc[-1]
        except:
            return 1380.0  # 최근 평균 환율로 백업
            
    exchange_rate = get_exchange_rate()
    
    # [수정] API 호출 대신 이미 확보된 데이터와 캐시를 우선 활용하여 N/A 방지
    def get_robust_company_info(ticker, analyzed_df):
        info = {'ticker': ticker}
        
        # 1순위: 이미 로드된 분석 데이터 프레임에서 확인
        if not analyzed_df.empty and ticker in analyzed_df['Node (자산명)'].values:
            row = analyzed_df[analyzed_df['Node (자산명)'] == ticker].iloc[0]
            info['shortName'] = ticker
            info['sector'] = row.get('Sector', 'N/A')
            info['industry'] = row.get('Industry', 'N/A')
            # 시총 텍스트($1.2B 등)가 아닌 원형 데이터를 찾기 위해 노력
            info['marketCap'] = row.get('Market Cap (시가총액)', 0) 
            # 만약 시총이 텍스트라면 숫자로 역산 시도 (또는 캐시 DB 조회)
            if isinstance(info['marketCap'], str):
                 # 텍스트로 저장된 경우 캐시 DB에서 직접 가져오기
                 import sqlite3
                 try:
                     conn = sqlite3.connect("metadata_cache.sqlite")
                     cur = conn.cursor()
                     cur.execute("SELECT name, sector, industry, market_cap FROM metadata WHERE ticker = ?", (ticker,))
                     db_row = cur.fetchone()
                     if db_row:
                         info['shortName'], info['sector'], info['industry'], info['marketCap'] = db_row
                     conn.close()
                 except: pass

        # 2순위: 데이터가 부족하면 yfinance fast_info 시도 (더 빠르고 안정적)
        if not info.get('marketCap') or info.get('marketCap') == 0:
            try:
                s = yf.Ticker(ticker)
                info['marketCap'] = s.fast_info.get('marketCap', 0)
                if not info.get('sector') or info.get('sector') == 'N/A':
                    info['sector'] = s.info.get('sector', 'N/A')
                    info['industry'] = s.info.get('industry', 'N/A')
                    info['shortName'] = s.info.get('shortName', ticker)
            except: pass
            
        return info
            
    info = get_robust_company_info(chart_ticker, analyzed_df)
    
    # 시총 환산 및 가공
    m_cap_val = info.get('marketCap', 0)
    # m_cap_val이 0이거나 데이터가 없을 때 analyzed_df의 텍스트라도 사용
    if not m_cap_val and not analyzed_df.empty:
        # 이미 텍스트로 가공된 시총 정보를 그대로 사용
        mc_display = analyzed_df[analyzed_df['Node (자산명)'] == chart_ticker].iloc[0].get('Market Cap (시가총액)', 'N/A')
        mc_krw_formatted = "N/A"
    else:
        market_cap_usd = float(m_cap_val)
        market_cap_krw = market_cap_usd * exchange_rate
        mc_display = f"${market_cap_usd / 1e9:.2f}B" if market_cap_usd >= 1e9 else (f"${market_cap_usd / 1e6:.1f}M" if market_cap_usd >= 1e6 else "N/A")
        mc_krw_formatted = f"{market_cap_krw / 1e12:.2f}조 원" if market_cap_krw >= 1e12 else (f"{market_cap_krw / 1e8:.1f}억 원" if market_cap_krw >= 1e8 else "N/A")

    # 기업 프로필 렌더링
    st.markdown(f"""
    <div style='background-color: #161B22; padding: 20px; border-radius: 10px; border: 1px solid #30363D; margin-bottom: 20px;'>
        <h3 style='color:#58A6FF; margin:0;'>🏢 {info.get('shortName', chart_ticker)} ({chart_ticker})</h3>
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;'>
            <div style='display: flex; flex-direction: column;'>
                <span style='color:#8B949E; font-size:0.8rem;'>Sector (섹터)</span>
                <span style='color:#C9D1D9; font-weight:bold;'>{engine.SECTOR_MAP.get(info.get('sector'), info.get('sector', 'N/A'))}</span>
            </div>
            <div style='display: flex; flex-direction: column;'>
                <span style='color:#8B949E; font-size:0.8rem;'>Industry (산업)</span>
                <span style='color:#C9D1D9; font-weight:bold;'>{info.get('industry', 'N/A')}</span>
            </div>
            <div style='display: flex; flex-direction: column;'>
                <span style='color:#8B949E; font-size:0.8rem;'>Market Cap (시가총액 - USD/KRW)</span>
                <span style='color:#D2A8FF; font-weight:bold;'>{mc_display} / {mc_krw_formatted}</span>
                <span style='color:#484F58; font-size:0.7rem;'>Rate: ₩{exchange_rate:,.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 원본 데이터 복사
    df_chart = data_dict[chart_ticker].copy()
    
    # 타임프레임 변경 (Resampling)
    if "Weekly" in timeframe:
        df_chart = df_chart.resample('W').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
    elif "Monthly" in timeframe:
        df_chart = df_chart.resample('ME').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
    elif "Yearly" in timeframe:
        df_chart = df_chart.resample('YE').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()

    # 기술적 지표 재계산 (주기에 맞춰서)
    df_chart = engine.compute_technical_indicators(df_chart)
    
    # 표시 범위 설정
    display_rows = 120 if "Daily" in timeframe else (52 if "Weekly" in timeframe else 24)
    df_chart = df_chart.tail(display_rows)

    # Plotly 서브플롯 생성
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.55, 0.20, 0.25],
        subplot_titles=[
            f"{chart_ticker} — Price Action & Bollinger Bands",
            "RSI (상대강도지수)",
            "MACD (이동평균 수렴확산)"
        ]
    )

    # [차트 1] 캔들스틱 + 이동평균선 + 볼린저 밴드 (상단)
    fig.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'], high=df_chart['High'],
        low=df_chart['Low'], close=df_chart['Close'],
        name='Price'
    ), row=1, col=1)

    # 이동평균선들 (Moving Averages)
    ma_colors = {
        'MA_5': '#FF80AB',   # 분홍 (단기)
        'MA_20': '#FFEB3B',  # 노랑 (심리선/BB중심)
        'MA_60': '#00E676',  # 녹색 (수급선)
        'MA_120': '#29B6F6', # 하늘 (경기선)
        'MA_200': '#AB47BC', # 보라 (대세선)
        'MA_240': '#9E9E9E'  # 회색 (장기대세선)
    }
    
    for ma_key, color in ma_colors.items():
        if ma_key in df_chart.columns:
            fig.add_trace(go.Scatter(
                x=df_chart.index, y=df_chart[ma_key],
                mode='lines', name=f'{ma_key.replace("_", " ")}',
                line=dict(color=color, width=1.2 if ma_key != 'MA_20' else 2)
            ), row=1, col=1)

    # 볼린저 밴드 상단선 (투명도 조절)
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart['BB_Upper'],
        mode='lines', name='BB Upper',
        line=dict(color='rgba(255,255,255,0.15)', width=0.8, dash='dot')
    ), row=1, col=1)

    # 볼린저 밴드 하단선
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart['BB_Lower'],
        mode='lines', name='BB Lower',
        line=dict(color='rgba(255,255,255,0.15)', width=0.8, dash='dot'),
        fill='tonexty',
        fillcolor='rgba(0, 191, 165, 0.03)'
    ), row=1, col=1)

    # [차트 2] RSI (중단)
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart['RSI'],
        mode='lines', name='RSI (상대강도지수)',
        line=dict(color='#AB47BC', width=2)
    ), row=2, col=1)

    # RSI 기준선
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,82,82,0.5)", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,191,165,0.5)", line_width=1, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(255,255,255,0.2)", line_width=1, row=2, col=1)

    # [차트 3] MACD (하단)
    colors = ['#00BFA5' if v >= 0 else '#FF5252' for v in df_chart['MACD_Hist'].fillna(0)]
    fig.add_trace(go.Bar(
        x=df_chart.index, y=df_chart['MACD_Hist'],
        name='MACD Hist',
        marker_color=colors,
        opacity=0.6
    ), row=3, col=1)

    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart['MACD'],
        mode='lines', name='MACD',
        line=dict(color='#29B6F6', width=2)
    ), row=3, col=1)

    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart['MACD_Signal'],
        mode='lines', name='Signal',
        line=dict(color='#FF9800', width=1.5, dash='dot')
    ), row=3, col=1)

    # 전체 레이아웃 설정 (인터랙티브 기능 강화)
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='rgba(14, 17, 23, 0.9)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=1200,
        showlegend=True,
        # [핵심] X축 통합 호버 모드 설정: 마우스 위치의 X값을 기준으로 모든 지표 툴팁 통합
        hovermode='x unified',
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=10)
        ),
        font=dict(family="Courier New, monospace", size=11, color="#C9D1D9"),
        xaxis_rangeslider_visible=False,
        xaxis3_rangeslider_visible=False,
    )

    # X축 가이드선, 범위 및 다이내믹 틱 설정
    fig.update_xaxes(
        showspikes=True, 
        spikemode='across', 
        spikesnap='cursor', 
        spikethickness=1, 
        spikedash='dot',
        spikecolor='#8B949E',
        # [수정] 데이터가 있는 구간만 보이도록 범위 재설정
        range=[df_chart.index[0], df_chart.index[-1]],
        # [수정] 일봉 분석에 최적화된 다이내믹 날짜 포맷 (연도 중복 표시 해결)
        tickformatstops=[
            dict(dtickrange=[None, 1000 * 60 * 60 * 24], value="%H:%M"),             # 1일 미만
            dict(dtickrange=[1000 * 60 * 60 * 24, 1000 * 60 * 60 * 24 * 7], value="%b %d"), # 1주일 미만: 월 일
            dict(dtickrange=[1000 * 60 * 60 * 24 * 7, 1000 * 60 * 60 * 24 * 30 * 6], value="%b %d, %y"), # 6개월 미만: 월 일, 년
            dict(dtickrange=[1000 * 60 * 60 * 24 * 30 * 6, None], value="%b %Y")    # 그 이상: 월 년
        ],
        hoverformat="%Y-%m-%d (%a)", # 호버 시 요일까지 상세 표기
        type='date',
        nticks=15, # 가로축 라벨 개수를 적절히 유지하여 시인성 확보
        gridcolor='#30363D' # 격자선 색상 조정
    )

    # 모든 서브플롯의 X축을 동기화 (Zoom/Pan 연동)
    fig.update_layout(xaxis=dict(anchor='y', matches='x3'), xaxis2=dict(anchor='y2', matches='x3'))

    # Y축 라벨 및 호버 포맷
    fig.update_yaxes(title_text="Price (가격, $)", row=1, col=1, tickformat="$,.2f")
    fig.update_yaxes(title_text="RSI (상대강도지수)", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD (이동평균 수렴확산)", row=3, col=1)

    # [최종] 마우스 휠 줌 및 인터랙티브 설정
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        config={
            'scrollZoom': True, 
            'displayModeBar': True, 
            'displaylogo': False,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'] # 분석용 그리기 도구 추가
        }
    )

# ============================================================
# [11] Market Heatmap — 나스닥100 / 러셀2000 히트맵
# ============================================================
# Finviz 스타일의 인터랙티브 트리맵 히트맵입니다.
# 섹터별로 그룹핑되고, 면적은 시가총액 비례, 색상은 일일 수익률(%) 기반입니다.
# 마우스 휠로 확대/축소, 드래그로 이동이 가능합니다.
# ============================================================
st.markdown("---")
st.markdown("### 🗺️ Market Heatmap (시장 히트맵) — Sector-Weighted Visualization")
st.markdown("*섹터별 시가총액 비례 면적 | 일일 수익률(%) 기반 색상 매핑 | 마우스 휠로 확대·축소 가능*")

import plotly.express as px
import plotly.io as pio
import streamlit.components.v1 as components

# ----- 히트맵 생성 함수 (재사용 가능) -----
def render_zoomable_heatmap(heatmap_data, title_text, tab_key):
    """
    Plotly Treemap을 HTML로 렌더링하고, JavaScript로 마우스 휠 줌 기능을 구현합니다.
    
    :param heatmap_data: engine.fetch_heatmap_data()의 반환값 (리스트)
    :param title_text: 차트 제목 문자열
    :param tab_key: 탭 구분용 고유 키
    """
    if not heatmap_data:
        st.warning(f"◈ {title_text} 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해 주세요.")
        return
    
    # 데이터프레임 변환
    df_hm = pd.DataFrame(heatmap_data)
    
    # 시총을 읽기 쉬운 텍스트로 변환 (호버 툴팁용)
    df_hm['market_cap_text'] = df_hm['market_cap'].apply(
        lambda x: f"${x/1e9:.1f}B" if x >= 1e9 else f"${x/1e6:.0f}M"
    )
    
    # 수익률 기반 색상 텍스트 (호버 툴팁용)
    df_hm['change_text'] = df_hm['daily_change_pct'].apply(
        lambda x: f"+{x:.2f}%" if x >= 0 else f"{x:.2f}%"
    )
    
    # 히트맵 셀 안에 표시할 텍스트 (티커 + 수익률)
    df_hm['display_text'] = df_hm.apply(
        lambda row: f"{row['ticker']}<br>{'+' if row['daily_change_pct'] >= 0 else ''}{row['daily_change_pct']:.2f}%",
        axis=1
    )
    
    # ===== Plotly Treemap 생성 =====
    fig_hm = px.treemap(
        df_hm,
        path=['sector', 'ticker'],          # 1단계: 섹터, 2단계: 종목
        values='market_cap',                 # 면적 = 시가총액 비례
        color='daily_change_pct',            # 색상 = 일일 수익률
        color_continuous_scale=[              # Finviz 스타일 빨강-회색-초록 그라데이션
            [0.0, '#B71C1C'],    # -5% 이하: 진한 빨강
            [0.15, '#D32F2F'],   # -3~-5%: 빨강
            [0.30, '#EF5350'],   # -1~-3%: 연한 빨강
            [0.45, '#424242'],   # -1~0%: 어두운 회색
            [0.55, '#424242'],   # 0~+1%: 어두운 회색
            [0.70, '#66BB6A'],   # +1~+3%: 연한 초록
            [0.85, '#388E3C'],   # +3~+5%: 초록
            [1.0, '#1B5E20'],    # +5% 이상: 진한 초록
        ],
        color_continuous_midpoint=0,         # 0%를 색상 중앙(회색)으로 설정
        range_color=[-5, 5],                 # 색상 범위: -5% ~ +5%
        custom_data=['name', 'price', 'market_cap_text', 'change_text'],
        title=None,
    )
    
    # 셀 내부 텍스트 포맷 설정
    fig_hm.update_traces(
        texttemplate='<b>%{label}</b><br>%{customdata[3]}',
        textfont=dict(size=11, color='#FFFFFF'),
        hovertemplate=(
            '<b>%{label}</b> (%{customdata[0]})<br>'
            '현재가: $%{customdata[1]}<br>'
            '시가총액: %{customdata[2]}<br>'
            '일일 수익률: %{customdata[3]}'
            '<extra></extra>'
        ),
        marker=dict(
            cornerradius=3,  # 셀 모서리 약간 둥글게
        )
    )
    
    # 레이아웃 설정
    fig_hm.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(14, 17, 23, 1)',
        plot_bgcolor='rgba(14, 17, 23, 1)',
        margin=dict(t=10, l=5, r=5, b=5),
        height=700,
        font=dict(family="Courier New, monospace", size=11, color="#C9D1D9"),
        coloraxis_colorbar=dict(
            title="수익률(%)",
            thickness=15,
            len=0.6,
            yanchor="middle",
            y=0.5,
            ticksuffix="%",
            tickfont=dict(size=10),
        ),
    )
    
    # ===== HTML + JavaScript로 마우스 휠 줌 구현 =====
    # Plotly 차트를 HTML 문자열로 변환합니다
    chart_html = pio.to_html(
        fig_hm, 
        include_plotlyjs='cdn',  # Plotly.js를 CDN에서 로드
        full_html=False,         # <html><body> 태그 없이 차트만
        config={
            'displayModeBar': True,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'displaylogo': False
        }
    )
    
    # 줌 가능한 컨테이너 HTML 생성
    # CSS transform: scale()을 사용하여 부드러운 줌 효과를 구현합니다
    zoom_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            /* 전체 배경을 대시보드와 동일한 다크 테마로 맞춤 */
            body {{
                margin: 0;
                padding: 0;
                background-color: #0E1117;
                overflow: hidden;
            }}
            
            /* 줌 컨테이너: 마우스 이벤트를 캡처하는 영역 */
            #zoom-container-{tab_key} {{
                width: 100%;
                height: 700px;
                overflow: hidden;
                cursor: grab;
                position: relative;
                border: 1px solid #30363D;
                border-radius: 8px;
                background-color: #0E1117;
            }}
            
            /* 줌 적용 대상: CSS transform으로 확대/축소 */
            #zoom-content-{tab_key} {{
                transform-origin: center center;
                transition: transform 0.1s ease-out;
                width: 100%;
                height: 100%;
            }}
            
            /* 드래그 중일 때 커서 모양 변경 */
            #zoom-container-{tab_key}.dragging {{
                cursor: grabbing;
            }}
            
            /* 줌 레벨 표시 배지 */
            #zoom-badge-{tab_key} {{
                position: absolute;
                top: 12px;
                right: 12px;
                background: rgba(22, 27, 34, 0.9);
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 4px 10px;
                color: #8B949E;
                font-size: 12px;
                font-family: 'Courier New', monospace;
                z-index: 100;
                pointer-events: none;
                user-select: none;
            }}
            
            /* 리셋 버튼 */
            #reset-btn-{tab_key} {{
                position: absolute;
                top: 12px;
                left: 12px;
                background: rgba(22, 27, 34, 0.9);
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 4px 10px;
                color: #00BFA5;
                font-size: 12px;
                font-family: 'Courier New', monospace;
                cursor: pointer;
                z-index: 100;
                transition: background 0.2s;
            }}
            #reset-btn-{tab_key}:hover {{
                background: rgba(0, 191, 165, 0.15);
            }}
        </style>
    </head>
    <body>
        <!-- 줌 가능한 히트맵 컨테이너 -->
        <div id="zoom-container-{tab_key}">
            <!-- 줌 레벨 표시 -->
            <div id="zoom-badge-{tab_key}">🔍 100%</div>
            <!-- 리셋 버튼 -->
            <div id="reset-btn-{tab_key}" onclick="resetZoom_{tab_key}()">⟲ Reset</div>
            <!-- Plotly 차트 본체 -->
            <div id="zoom-content-{tab_key}">
                {chart_html}
            </div>
        </div>
        
        <script>
        (function() {{
            // ===== 줌 상태 변수 =====
            let scale = 1;          // 현재 줌 배율 (1 = 100%)
            let translateX = 0;     // X축 이동량 (px)
            let translateY = 0;     // Y축 이동량 (px)
            const MIN_SCALE = 0.5;  // 최소 줌 (50%)
            const MAX_SCALE = 5;    // 최대 줌 (500%)
            const ZOOM_SPEED = 0.1; // 휠 한 틱당 줌 변화량
            
            // ===== DOM 요소 참조 =====
            const container = document.getElementById('zoom-container-{tab_key}');
            const content = document.getElementById('zoom-content-{tab_key}');
            const badge = document.getElementById('zoom-badge-{tab_key}');
            
            // ===== 트랜스폼 적용 함수 =====
            function applyTransform() {{
                content.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
                badge.textContent = `🔍 ${{Math.round(scale * 100)}}%`;
            }}
            
            // ===== 마우스 휠 줌 이벤트 =====
            // Finviz처럼 마우스 위치를 기준으로 줌인/줌아웃합니다
            container.addEventListener('wheel', function(e) {{
                e.preventDefault();  // 페이지 스크롤 방지
                
                // 마우스 포인터의 컨테이너 내 상대 위치 계산
                const rect = container.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                // 줌 방향 결정 (휠 위로 = 확대, 아래로 = 축소)
                const delta = e.deltaY > 0 ? -ZOOM_SPEED : ZOOM_SPEED;
                const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale + delta));
                
                if (newScale !== scale) {{
                    // 마우스 위치를 기준점으로 줌 (이 부분이 핵심!)
                    // 줌 전후에 마우스가 가리키는 콘텐츠 지점이 동일하게 유지됩니다
                    const ratio = newScale / scale;
                    translateX = mouseX - ratio * (mouseX - translateX);
                    translateY = mouseY - ratio * (mouseY - translateY);
                    scale = newScale;
                    applyTransform();
                }}
            }}, {{ passive: false }});
            
            // ===== 드래그로 패닝(이동) =====
            let isDragging = false;
            let startX, startY;
            
            container.addEventListener('mousedown', function(e) {{
                // 줌 배율이 1보다 클 때만 드래그 활성화
                if (scale > 1) {{
                    isDragging = true;
                    startX = e.clientX - translateX;
                    startY = e.clientY - translateY;
                    container.classList.add('dragging');
                }}
            }});
            
            document.addEventListener('mousemove', function(e) {{
                if (isDragging) {{
                    translateX = e.clientX - startX;
                    translateY = e.clientY - startY;
                    applyTransform();
                }}
            }});
            
            document.addEventListener('mouseup', function() {{
                isDragging = false;
                container.classList.remove('dragging');
            }});
            
            // ===== 리셋 함수 (전역 노출) =====
            window.resetZoom_{tab_key} = function() {{
                scale = 1;
                translateX = 0;
                translateY = 0;
                applyTransform();
            }};
        }})();
        </script>
    </body>
    </html>
    """
    
    # Streamlit HTML 컴포넌트로 렌더링
    # 높이는 차트(700) + 여유(30) = 730px
    components.html(zoom_html, height=730, scrolling=False)


# ----- 히트맵 데이터 로드 (캐시 적용) -----
@st.cache_data(ttl=3600, show_spinner=False)
def load_heatmap_data_cached(index_name):
    """
    히트맵 데이터를 캐시하여 반복 로딩을 방지합니다.
    TTL = 3600초 (1시간) 후 자동 갱신
    
    :param index_name: 'nasdaq100' 또는 'russell2000'
    :return: 히트맵 데이터 리스트
    """
    if index_name == 'nasdaq100':
        tickers = engine.get_nasdaq100_tickers()
    else:
        tickers = engine.get_russell2000_top_tickers()
    
    return engine.fetch_heatmap_data(tickers)


# ----- 히트맵 탭 UI -----
tab_ndx, tab_rut = st.tabs(["📊 NASDAQ 100 (나스닥 100)", "📊 Russell 2000 (러셀 2000)"])

with tab_ndx:
    st.markdown("""
    > **NASDAQ 100**: 나스닥 거래소에 상장된 비금융 대형주 100개로 구성됩니다.  
    > 빅테크(AAPL, MSFT, NVDA, AMZN 등)가 지수의 대부분을 차지합니다.
    """)
    with st.spinner("◈ NASDAQ 100 히트맵 데이터 동기화 중... (최초 로딩 시 1~2분 소요)"):
        ndx_data = load_heatmap_data_cached('nasdaq100')
    
    if ndx_data:
        # 간단한 요약 KPI
        ndx_df = pd.DataFrame(ndx_data)
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        
        gainers = len(ndx_df[ndx_df['daily_change_pct'] > 0])
        losers = len(ndx_df[ndx_df['daily_change_pct'] < 0])
        avg_change = ndx_df['daily_change_pct'].mean()
        top_gainer = ndx_df.loc[ndx_df['daily_change_pct'].idxmax()]
        
        kpi_col1.metric("상승 종목 (Advancers)", f"{gainers}개")
        kpi_col2.metric("하락 종목 (Decliners)", f"{losers}개")
        kpi_col3.metric("평균 수익률 (Avg Change)", f"{avg_change:+.2f}%")
        kpi_col4.metric(f"최고 상승 (Top Gainer)", f"{top_gainer['ticker']} ({top_gainer['daily_change_pct']:+.2f}%)")
        
        render_zoomable_heatmap(ndx_data, "NASDAQ 100", "ndx")
    else:
        st.info("◈ NASDAQ 100 데이터를 로드할 수 없습니다.")

with tab_rut:
    st.markdown("""
    > **Russell 2000**: 미국 소형주 2000개로 구성된 지수입니다.  
    > 여기서는 IWM ETF 기준 상위 120개 대표 종목을 표시합니다.
    """)
    with st.spinner("◈ Russell 2000 히트맵 데이터 동기화 중... (최초 로딩 시 1~2분 소요)"):
        rut_data = load_heatmap_data_cached('russell2000')
    
    if rut_data:
        rut_df = pd.DataFrame(rut_data)
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        
        gainers = len(rut_df[rut_df['daily_change_pct'] > 0])
        losers = len(rut_df[rut_df['daily_change_pct'] < 0])
        avg_change = rut_df['daily_change_pct'].mean()
        top_gainer = rut_df.loc[rut_df['daily_change_pct'].idxmax()]
        
        kpi_col1.metric("상승 종목 (Advancers)", f"{gainers}개")
        kpi_col2.metric("하락 종목 (Decliners)", f"{losers}개")
        kpi_col3.metric("평균 수익률 (Avg Change)", f"{avg_change:+.2f}%")
        kpi_col4.metric(f"최고 상승 (Top Gainer)", f"{top_gainer['ticker']} ({top_gainer['daily_change_pct']:+.2f}%)")
        
        render_zoomable_heatmap(rut_data, "Russell 2000", "rut")
    else:
        st.info("◈ Russell 2000 데이터를 로드할 수 없습니다.")

# ============================================================
# [12] 하단 시스템 정보
# ============================================================
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#484F58; font-size:0.75rem;'>"
    "◈ QV&F Analytics Matrix v2.1 | Data Source (데이터 출처): yfinance API | "
    "Greeks (그릭스): Black-Scholes Approximation (블랙숄즈 근사) | "
    "Heatmap: Sector-Weighted Treemap (섹터 가중 트리맵) | "
    f"Last Pipeline Sync: {now} (Bilingual System Active)"
    "</p>",
    unsafe_allow_html=True
)
