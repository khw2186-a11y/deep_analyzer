import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import data_pipeline as dp  # 우리가 직접 작성한 백엔드 로직 파일을 불러옵니다.

# --- [1] 웹 대시보드 페이지 기본 설정 ---
# 탭 이름, 아이콘, 그리고 레이아웃을 넓게(wide) 쓰도록 설정합니다.
st.set_page_config(
    page_title="미국 주도주 & 옵션 전략 대시보드",
    page_icon="📈",
    layout="wide"
)

# --- [2] 사이드바 (Sidebar) 설정 ---
# 화면 왼쪽 사이드바에 필터링 옵션 등을 넣습니다.
st.sidebar.header("⚙️ 옵션 및 필터 설정")
# 사용자가 직접 분석할 종목들을 넣고 뺄 수 있도록 멀티 셀렉트 박스 제공
selected_tickers = st.sidebar.multiselect(
    "분석할 관심 종목(Universe)을 선택하세요",
    options=dp.DEFAULT_UNIVERSE,  # data_pipeline.py에 정의된 기본 빅테크 리스트
    default=dp.DEFAULT_UNIVERSE   # 초기 화면에서 모두 선택되게 설정
)

# --- [3] 메인 대시보드 헤더 및 설명 ---
st.title("📈 미국 주도주 모멘텀 & Bull Call Spread 타점 분석")
st.markdown("""
환영합니다! 이 대시보드는 **빅테크 및 AI 인프라 관련 핵심 기업**을 중심으로, 최근 1개월 가격 모멘텀과 거래량 급증 여부를 파이썬 알고리즘으로 분석합니다.
또한, 실시간에 가까운 **옵션 시장 데이터**를 융합하여, **Call 거래량이 Put 거래량을 압도하는** 강력한 상승 돌파 타점(Bull Call Spread 진입에 유리한 지점)을 자동으로 추출해 줍니다.
""")

# 사용자가 사이드바에서 종목을 모두 지워버렸을 때의 예외 처리
if not selected_tickers:
    st.warning("⚠️ 사이드바에서 분석할 종목을 최소 한 개 이상 선택해 주세요.")
    st.stop() # 여기서 렌더링 중지

# --- [4] 데이터 로드 및 처리 ---
# @st.cache_data 데코레이터는 같은 함수를 호출할 때 야후 파이낸스에 매번 요청하지 않고,
# 캐시된(저장된) 데이터를 재사용하도록 하여 로딩 속도를 높이고 API 블락을 방지합니다. (ttl=3600은 1시간 유지)
@st.cache_data(ttl=3600) 
def load_and_analyze_data(tickers):
    # 1. 주가 데이터 수집 (백엔드 함수 호출)
    data_dict = dp.fetch_stock_data(tickers, period='3mo')
    # 2. 수집된 데이터를 바탕으로 이동평균 및 모멘텀 계산
    analyzed_df = dp.analyze_momentum_and_volume(data_dict)
    return data_dict, analyzed_df

# 로딩 중일 때 사용자에게 돌아가는 스피너(동그라미)와 메시지를 보여줍니다.
with st.spinner("야후 파이낸스에서 빅데이터를 실시간으로 불러와 분석하고 있습니다... 잠시만 기다려 주세요."):
    data_dict, analyzed_df = load_and_analyze_data(selected_tickers)

# --- [5] 상단 요약 지표 (Metrics) ---
st.divider() # 구분선
st.subheader("💡 1차 주식 데이터 분석 요약")

# 데이터가 존재할 경우 화면 상단에 3개의 주요 지표를 나란히 배치합니다.
if not analyzed_df.empty:
    col1, col2, col3 = st.columns(3) # 화면을 3등분
    
    # 1) 전체 선택 종목의 평균 1개월 수익률
    avg_momentum = analyzed_df['Momentum 1M (%)'].mean()
    col1.metric("선택 종목 평균 1개월 수익률", f"{avg_momentum:.2f}%")
    
    # 2) 상승 추세(20일 이동평균선 돌파 및 모멘텀 양수)에 있는 종목의 개수
    uptrend_count = len(analyzed_df[analyzed_df['Uptrend']])
    col2.metric("상승 추세 (20일선 위) 종목 수", f"{uptrend_count}개")
    
    # 3) 단기 거래량 급증 종목 개수
    spike_count = len(analyzed_df[analyzed_df['Volume Spike']])
    col3.metric("최근 3일 거래량 급증 종목 수", f"{spike_count}개")

# 전체 분석표 출력 (옵션 데이터 제외)
with st.expander("📊 전체 종목 1차 주식 분석 결과 자세히 보기 (클릭하여 펼치기)"):
    st.dataframe(analyzed_df, use_container_width=True)

st.divider()

# --- [6] Bull Call Spread 융합 타점 결과 (옵션 데이터 적용) ---
st.subheader("🔥 핵심! Bull Call Spread 추천 종목 (옵션 파생 수급 융합)")
st.info("""
**[알고리즘 3단계 필터 조건]**
1. 현재 주가가 20일 이동평균선 위에 위치하며 수익률이 양수임 (상승 추세 확립)
2. 최근 3일 평균 거래량이 20일 평균 거래량의 1.5배 이상 터짐 (강력한 매수세 유입 확인)
3. 가장 가까운 만기일 옵션 체인에서 Call 옵션 거래량이 Put 옵션 거래량보다 많음 (상승 베팅 우위)
""")

# 옵션 데이터는 실시간 API 요청 부하가 크므로, 1차 필터를 통과한 종목에 대해서만 실시간으로 돌립니다.
with st.spinner("1차 필터를 통과한 종목들의 실시간 옵션 체인(Option Chain)을 정밀 분석 중입니다..."):
    bull_candidates = dp.find_bull_call_spread_candidates(analyzed_df)

if not bull_candidates.empty:
    st.success("🎉 축하합니다! 알고리즘이 아래 종목들을 현재 '강세 콜 스프레드' 진입에 가장 이상적인 타점으로 분석했습니다.")
    
    # 데이터프레임 시각적으로 예쁘게 포맷팅 (색상 하이라이트 추가)
    styled_df = bull_candidates.style.highlight_max(subset=['Momentum 1M (%)', 'Call Vol'], color='rgba(76, 175, 80, 0.4)')\
                                     .format({'Current Price': '${:.2f}', 'P/C Ratio': '{:.2f}'})
    st.dataframe(styled_df, use_container_width=True)
    
    # 옵션 볼륨 시각화 (막대 그래프)
    st.markdown("#### ⚖️ 추천 종목별 옵션 파생 거래량 비교 (Call vs Put)")
    bar_fig = go.Figure()
    # 콜 거래량 막대기 (초록색)
    bar_fig.add_trace(go.Bar(x=bull_candidates['Ticker'], y=bull_candidates['Call Vol'], name='Call Volume (상승 베팅)', marker_color='#4caf50'))
    # 풋 거래량 막대기 (빨간색)
    bar_fig.add_trace(go.Bar(x=bull_candidates['Ticker'], y=bull_candidates['Put Vol'], name='Put Volume (하락 베팅)', marker_color='#f44336'))
    
    # 막대기를 옆으로 나란히 배치 (barmode='group')
    bar_fig.update_layout(barmode='group', template='plotly_dark', xaxis_title="종목 코드 (Ticker)", yaxis_title="거래량 (Volume)",
                          plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(bar_fig, use_container_width=True)

else:
    # 조건을 만족하는 종목이 없을 때의 예외 화면 처리
    st.warning("⚠️ 현재 주식 추세와 옵션 수급의 3가지 강력한 필터 조건을 모두 완벽히 만족하는 종목이 없습니다. 시장이 관망세에 있거나 변동성이 축소된 상태일 수 있습니다.")

st.divider()

# --- [7] 개별 종목 캔들스틱 차트 (Plotly) ---
st.subheader("📈 개별 종목 정밀 캔들스틱 차트 분석")
# 사용자 선택형 드롭다운 박스
chart_ticker = st.selectbox("정밀 차트를 확인하고 싶은 종목을 선택하세요:", selected_tickers)

if chart_ticker in data_dict:
    # 차트에는 너무 많은 데이터보다 최근 60 거래일(약 3개월)만 보여주어 가독성을 높입니다.
    df_chart = data_dict[chart_ticker].tail(60) 
    
    # Plotly 캔들스틱 차트 객체 생성 (시가, 고가, 저가, 종가 매핑)
    fig = go.Figure(data=[go.Candlestick(x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name='Price',
                    increasing_line_color='#ef5350', # 상승 캔들(미국은 보통 초록이나, 한국식 붉은색 계열)
                    decreasing_line_color='#26a69a')]) # 하락 캔들 (한국식 파란계열/청록)
    
    # [지표 추가] 20일 이동평균선(SMA 20)을 캔들스틱 위에 겹쳐서 그립니다.
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Close'].rolling(window=20).mean(), 
                             mode='lines', name='SMA 20 (20일 생명선)', line=dict(color='#ffeb3b', width=2)))
    
    # 차트 레이아웃(디자인) 세부 설정
    fig.update_layout(title=f"{chart_ticker} 주가 추이 및 20일 이동평균선 돌파 여부",
                      yaxis_title="주가 (USD)",
                      xaxis_rangeslider_visible=False, # 하단 슬라이더 제거하여 깔끔하게
                      template="plotly_dark", # 프리미엄 다크 모드 적용
                      plot_bgcolor='rgba(15, 23, 42, 0.8)',
                      paper_bgcolor='rgba(0,0,0,0)') 
    
    st.plotly_chart(fig, use_container_width=True)
