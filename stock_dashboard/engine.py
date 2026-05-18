# ============================================================
# engine.py - 데이터 수집 및 분석 엔진
# ============================================================
# 이 파일은 yfinance API를 통해 데이터를 수집하고,
# RSI, MACD, 볼린저 밴드, IV Rank, Greeks 등을 계산하는
# 백엔드(뒷단) 로직을 담당합니다.
# ============================================================

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm  # Black-Scholes 모델 계산용
import sqlite3
import json
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
import streamlit as st

# 버전 관리 (동기화 확인용)
VERSION = "V7.0_SPEED_UP_OPTIMIZED"

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """S&P 500 구성 종목 리스트를 위키피디아에서 가져옵니다."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        return pd.read_html(url)[0]['Symbol'].tolist()
    except:
        return []

# -------------------------------------------------------
# 0. 메타데이터 캐시 시스템 (SQLite)
# -------------------------------------------------------
# yfinance의 .info 호출은 매우 느립니다. (종목당 약 1~2초)
# 섹터, 회사명 등 변하지 않는 정보는 SQLite DB에 저장하여 속도를 100배 이상 높입니다.
# -------------------------------------------------------

DB_PATH = "metadata_cache.sqlite"

def init_db():
    """SQLite 데이터베이스 및 테이블 초기화 (스키마 변경 대응을 위해 테이블 재생성 로직 포함)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # [긴급 조치] 기존 테이블에 industry 컬럼이 없을 경우를 대비해 테이블 재생성
    # 캐시 데이터이므로 삭제 후 재생성이 가장 확실한 해결책입니다.
    try:
        cursor.execute("SELECT industry FROM stock_metadata LIMIT 1")
    except:
        # industry 컬럼이 없으면 테이블 삭제
        cursor.execute("DROP TABLE IF EXISTS stock_metadata")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_metadata (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            last_updated TIMESTAMP
        )
    ''')
    
    # [특수 대응] 주요 종목 수동 데이터 재삽입
    manual_data = [
        ('AG', 'First Majestic Silver Corp.', 'Basic Materials', 'Silver', 2500000000),
        ('TSLA', 'Tesla, Inc.', 'Consumer Cyclical', 'Auto Manufacturers', 500000000000),
        ('NVDA', 'NVIDIA Corporation', 'Technology', 'Semiconductors', 2000000000000)
    ]
    for ticker, name, sector, industry, mcap in manual_data:
        cursor.execute('''
            INSERT OR REPLACE INTO stock_metadata (ticker, name, sector, industry, market_cap, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticker, name, sector, industry, mcap, datetime.now().isoformat()))
        
    conn.commit()
    conn.close()

def get_cached_metadata(tickers):
    """DB에서 캐시된 메타데이터 조회"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    # 안전한 조회를 위해 컬럼 명시
    query = f"SELECT ticker, name, sector, industry, market_cap FROM stock_metadata WHERE ticker IN ({','.join(['?']*len(tickers))})"
    df = pd.read_sql_query(query, conn, params=tickers)
    conn.close()
    return df

def update_metadata_cache(metadata_list):
    """새로운 메타데이터를 DB에 저장 또는 업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    for m in metadata_list:
        # m 딕셔너리에 industry가 없을 경우를 대비한 get 처리
        cursor.execute('''
            INSERT OR REPLACE INTO stock_metadata (ticker, name, sector, industry, market_cap, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (m['ticker'], m['name'], m['sector'], m.get('industry', 'N/A'), m['market_cap'], now))
    conn.commit()
    conn.close()

# -------------------------------------------------------
# 0-1. Fear & Greed Index 엔진
# -------------------------------------------------------
def get_fear_and_greed_index():
    """
    CNN Business의 Fear & Greed Index를 가져오되, 
    실패 시 VIX(변동성 지수)를 활용한 자체 공포 지수(Proxy)로 자동 전환합니다.
    """
    try:
        # 1. CNN 공식 데이터 엔드포인트 시도
        url = "https://production.dataviz.cnn.io/index/feargreed/static/feargreed"
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            fgi = data.get('fgi', {})
            current = fgi.get('now', {})
            if current.get('value'):
                return {
                    'value': round(current['value']),
                    'rating': current.get('valueText', 'Neutral'),
                    'source': 'CNN Business'
                }
    except Exception as e:
        print(f"[Engine] CNN F&G 로드 실패 ({e}). 백업 엔진(VIX Proxy) 가동.")

    try:
        # 2. 백업: VIX 지수를 활용한 공포 지수 역산 (20-30 범위 기준)
        # VIX가 높을수록 Extreme Fear(0), 낮을수록 Extreme Greed(100)로 환산
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        # VIX 10(Greed) ~ 40(Fear) 범위를 0~100으로 스케일링
        proxy_val = max(0, min(100, 100 - ((vix - 10) / (40 - 10) * 100)))
        
        rating = "Neutral"
        if proxy_val <= 25: rating = "Extreme Fear"
        elif proxy_val <= 45: rating = "Fear"
        elif proxy_val <= 55: rating = "Neutral"
        elif proxy_val <= 75: rating = "Greed"
        else: rating = "Extreme Greed"
        
        return {
            'value': round(proxy_val),
            'rating': rating,
            'source': 'VIX Proxy (System Generated)'
        }
    except:
        return {'value': 50, 'rating': 'Neutral', 'source': 'Default'}

# -------------------------------------------------------
# 1. 관심 종목 리스트 (Universe / Node List)
# -------------------------------------------------------
# Yahoo Finance "Most Active(거래량 상위)" Top 100 종목을 실시간으로 가져옵니다.
# 만약 인터넷이 안 되거나 API 오류가 나면, 미리 준비해 둔 기본 리스트를 사용합니다.
# -------------------------------------------------------

# [폴백용 기본 리스트] API 실패 시 사용할 하드코딩된 종목 리스트
_FALLBACK_UNIVERSE = [
    'AAPL', 'ACHR', 'AMD', 'AMZN', 'ARM', 'ASTS', 'AVGO', 'CRWD',
    'ELV', 'GOOGL', 'HIMS', 'HOOD', 'INTC', 'IONQ', 'IREN', 'JOBY',
    'LAES', 'MARA', 'META', 'MSFT', 'NVDA', 'ORCL', 'PANW', 'PL',
    'PLTR', 'QXO', 'RBLX', 'RDDT', 'RDW', 'RGTI', 'RKLB', 'RXRX',
    'SMCI', 'TEM', 'TSLA', 'TSLL', 'UFO', 'ZETA'
]

# 섹터 및 산업 한글 번역 매핑
SECTOR_MAP = {
    'Technology': '기술주 (Technology)',
    'Healthcare': '헬스케어 (Healthcare)',
    'Financial Services': '금융 서비스 (Financial Services)',
    'Consumer Cyclical': '경기 소비재 (Consumer Cyclical)',
    'Industrials': '산업재 (Industrials)',
    'Communication Services': '통신 서비스 (Communication Services)',
    'Consumer Defensive': '필수 소비재 (Consumer Defensive)',
    'Energy': '에너지 (Energy)',
    'Real Estate': '부동산 (Real Estate)',
    'Basic Materials': '기초 소재 (Basic Materials)',
    'Utilities': '유틸리티 (Utilities)'
}

# 시가총액 정보를 저장할 전역 딕셔너리 (캐시 역할)
_MARKET_CAP_MAP = {}

def fetch_most_active_tickers(count=100):
    """
    Yahoo Finance의 'Most Active' 스크리너에서 종목과 시총 정보를 가져옵니다.
    """
    global _MARKET_CAP_MAP
    all_tickers = []
    
    try:
        from urllib.request import Request, urlopen
        import json

        def get_screener_data(scr_id, limit):
            url = (
                f"https://query1.finance.yahoo.com/v1/finance/screener/"
                f"predefined/saved?formatted=false&lang=en-US&region=US"
                f"&scrIds={scr_id}&count={limit}"
            )
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read())
            quotes = data['finance']['result'][0]['quotes']
            
            # 시총 정보 맵에 저장
            for q in quotes:
                if 'symbol' in q:
                    _MARKET_CAP_MAP[q['symbol']] = q.get('marketCap', 0)
            
            return [q['symbol'] for q in quotes if 'symbol' in q]

        # 1. Most Active 우선 수집
        all_tickers.extend(get_screener_data('most_actives', count))
        
        # 2. 개수가 부족하면 Day Gainers에서 보충
        if len(all_tickers) < count:
            gainers = get_screener_data('day_gainers', count - len(all_tickers) + 10)
            for t in gainers:
                if t not in all_tickers:
                    all_tickers.append(t)
                if len(all_tickers) >= count: break

        all_tickers = all_tickers[:count]
        
        if all_tickers:
            print(f"[Engine] Yahoo Finance 실시간 종목 {len(all_tickers)}개 로드 완료!")
            return all_tickers
        else:
            return _FALLBACK_UNIVERSE

    except Exception as e:
        print(f"[Engine] 종목 목록 로드 실패 ({e}). 폴백 리스트를 사용합니다.")
        return _FALLBACK_UNIVERSE


# 프로그램 시작 시 자동으로 Most Active 기반 리스트를 가져옵니다.
DEFAULT_UNIVERSE = fetch_most_active_tickers(count=100)


# -------------------------------------------------------
# 2. 주가 데이터 수집 함수
# -------------------------------------------------------
def fetch_stock_data(tickers, period='1y'):
    """
    yfinance API로 종목별 과거 주가 데이터를 수집합니다.
    IV Rank 계산을 위해 기본 기간을 1년(1y)으로 설정합니다.

    :param tickers: 종목 코드 리스트 (예: ['AAPL', 'TSLA'])
    :param period: 데이터 기간 (기본값: '1y' = 최근 1년)
    :return: {종목코드: DataFrame} 형태의 딕셔너리
    """
    data_dict = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if not df.empty:
                data_dict[ticker] = df
        except Exception as e:
            print(f"[{ticker}] 데이터 수집 오류: {e}")
    return data_dict


# -------------------------------------------------------
# 3. 기술적 지표 계산 함수 (RSI, MACD, 볼린저 밴드)
# -------------------------------------------------------
def compute_technical_indicators(df):
    """
    주가 데이터프레임에 RSI, MACD, 볼린저 밴드 지표를 추가합니다.

    - RSI (Relative Strength Index): 과매수/과매도를 판단 (70 이상=과매수, 30 이하=과매도)
    - MACD: 추세 반전 시그널을 포착 (MACD선이 시그널선을 상향 돌파하면 매수 신호)
    - 볼린저 밴드: 가격의 변동성 범위를 시각화 (밴드가 좁아지면 큰 움직임 임박)
    """
    close = df['Close']

    # === RSI (14일 기준) ===
    # 전일 대비 가격 변화량 계산
    delta = close.diff()
    # 상승분만 추출 (하락일은 0)
    gain = delta.where(delta > 0, 0.0)
    # 하락분만 추출 (상승일은 0, 절대값 처리)
    loss = (-delta.where(delta < 0, 0.0))
    # 14일 지수이동평균(EMA)으로 평균 상승폭/하락폭 계산
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    # RS = 평균상승폭 / 평균하락폭, RSI = 100 - (100 / (1 + RS))
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # === MACD (12일 EMA - 26일 EMA) ===
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    # 시그널선: MACD의 9일 EMA
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    # 히스토그램: MACD - 시그널 (양수면 상승 모멘텀)
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # 1. 이동평균선 (Moving Averages)
    df['MA_5'] = df['Close'].rolling(window=5).mean()
    df['MA_20'] = df['Close'].rolling(window=20).mean() # 볼린저 밴드 중심선과 동일
    df['MA_60'] = df['Close'].rolling(window=60).mean()
    df['MA_120'] = df['Close'].rolling(window=120).mean()
    df['MA_200'] = df['Close'].rolling(window=200).mean()
    df['MA_240'] = df['Close'].rolling(window=240).mean()

    # 2. 볼린저 밴드 (Bollinger Bands - 20일, 2표준편차)
    df['BB_Mid'] = df['MA_20']
    std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (std * 2)
    df['BB_Lower'] = df['BB_Mid'] - (std * 2)
    # 밴드 폭 (Bandwidth): 밴드가 얼마나 넓은지 수치화
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Mid']

    # === 기본 모멘텀/거래량 지표 ===
    df['SMA_20'] = close.rolling(window=20).mean()
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()

    return df


# -------------------------------------------------------
# 4. 역사적 변동성(HV) 기반 IV Rank / IV Percentile 계산
# -------------------------------------------------------
def compute_iv_rank_percentile(df, current_iv=None):
    """
    과거 1년간의 역사적 변동성(HV)을 기반으로 IV Rank와 IV Percentile을 근사 계산합니다.

    - IV Rank = (현재IV - 1년최저IV) / (1년최고IV - 1년최저IV) × 100
      → 0%에 가까울수록 프리미엄이 저렴한 상태
    - IV Percentile = 현재IV보다 낮았던 날의 비율
      → 예: 80%이면 과거 1년 중 80%의 날보다 현재IV가 높다는 뜻

    :param df: 1년치 주가 데이터프레임
    :param current_iv: 옵션에서 가져온 실제 IV (없으면 HV로 대체)
    """
    # 일간 수익률의 표준편차 × √252로 연간 변동성 환산
    # 20일 롤링 윈도우로 매일의 HV 계산
    daily_returns = df['Close'].pct_change()
    hv_series = daily_returns.rolling(window=20).std() * np.sqrt(252)
    hv_series = hv_series.dropna()

    if len(hv_series) < 50:
        return None, None

    # 실제 IV가 없으면 가장 최근 HV를 현재 IV로 사용
    current = current_iv if current_iv else hv_series.iloc[-1]
    hv_min = hv_series.min()
    hv_max = hv_series.max()

    # IV Rank 계산
    if hv_max - hv_min > 0:
        iv_rank = ((current - hv_min) / (hv_max - hv_min)) * 100
    else:
        iv_rank = 50.0

    # IV Percentile 계산
    iv_percentile = (hv_series < current).sum() / len(hv_series) * 100

    return round(iv_rank, 1), round(iv_percentile, 1)


# -------------------------------------------------------
# 5. 옵션 체인 + 미결제약정(OI) + Max Pain 계산
# -------------------------------------------------------
def get_options_chain_with_oi(ticker):
    """
    가장 가까운 만기일의 옵션 체인에서 행사가별 Call/Put OI를 수집하고,
    Max Pain(최대 고통 가격)을 계산합니다.

    Max Pain이란?
    → 옵션 매도자(마켓메이커)가 가장 적은 손실을 보는 가격.
    → 만기일에 주가가 Max Pain 근처로 수렴하는 경향이 있음.
    """
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return None

        nearest_expiry = expirations[0]
        opt_chain = stock.option_chain(nearest_expiry)
        calls = opt_chain.calls
        puts = opt_chain.puts

        # NaN 값을 0으로 치환
        calls = calls.fillna(0)
        puts = puts.fillna(0)

        # 총 거래량 및 P/C Ratio 계산
        total_call_vol = calls['volume'].sum()
        total_put_vol = puts['volume'].sum()
        pc_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0

        # 총 OI(미결제약정) 합산
        total_call_oi = calls['openInterest'].sum()
        total_put_oi = puts['openInterest'].sum()

        # === Max Pain 계산 ===
        # 각 행사가에서 모든 콜/풋 보유자가 입는 총 손실을 계산하여
        # 그 합이 최대가 되는(= 매도자 손실이 최소인) 가격을 찾음
        strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
        max_pain_price = strikes[0] if strikes else 0
        min_total_pain = float('inf')

        for s in strikes:
            # 각 행사가(s)에서의 콜 보유자 손실: max(0, s - 행사가) × OI
            call_pain = calls.apply(
                lambda r: max(0, s - r['strike']) * r['openInterest'], axis=1
            ).sum()
            # 각 행사가(s)에서의 풋 보유자 손실: max(0, 행사가 - s) × OI
            put_pain = puts.apply(
                lambda r: max(0, r['strike'] - s) * r['openInterest'], axis=1
            ).sum()
            total_pain = call_pain + put_pain

            if total_pain < min_total_pain:
                min_total_pain = total_pain
                max_pain_price = s

        # 현재 주가 가져오기
        current_price = stock.history(period='1d')['Close'].iloc[-1] if not stock.history(period='1d').empty else 0

        # 평균 IV 계산 (ATM 근처 옵션에서 추출)
        atm_calls = calls[abs(calls['strike'] - current_price) < current_price * 0.05]
        avg_iv = atm_calls['impliedVolatility'].mean() if not atm_calls.empty else None

        return {
            'expiry': nearest_expiry,
            'calls': calls[['strike', 'openInterest', 'volume', 'impliedVolatility']],
            'puts': puts[['strike', 'openInterest', 'volume', 'impliedVolatility']],
            'total_call_vol': total_call_vol,
            'total_put_vol': total_put_vol,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'pc_ratio': round(pc_ratio, 2),
            'max_pain': max_pain_price,
            'current_price': round(current_price, 2),
            'avg_iv': avg_iv
        }
    except Exception as e:
        print(f"[{ticker}] 옵션 데이터 오류: {e}")
        return None


# -------------------------------------------------------
# 6. Black-Scholes 모델 기반 Greeks 근사 계산
# -------------------------------------------------------
def compute_greeks_bsm(S, K, T, r, sigma):
    """
    Black-Scholes 모델로 콜옵션의 Delta와 Gamma를 계산합니다.

    :param S: 현재 기초자산 가격 (주가)
    :param K: 행사가 (Strike Price)
    :param T: 만기까지 남은 시간 (연 단위, 예: 30일 = 30/365)
    :param r: 무위험 이자율 (예: 0.05 = 5%)
    :param sigma: 내재변동성 (IV)
    :return: (Delta, Gamma) 튜플
    """
    if T <= 0 or sigma <= 0:
        return 0, 0

    # d1, d2 계산 (Black-Scholes 핵심 공식)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # Delta: 기초자산 가격이 1달러 변할 때 옵션 가격의 변화량
    delta = norm.cdf(d1)
    # Gamma: Delta의 변화율 (가격 민감도의 민감도)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

    return round(delta, 4), round(gamma, 6)


# -------------------------------------------------------
# 7. 종합 분석 함수 (모든 지표를 합쳐서 결과 테이블 생성)
# -------------------------------------------------------
def run_full_analysis(data_dict):
    """
    수집된 모든 종목의 데이터를 분석하여 하나의 결과 테이블로 만듭니다.
    """
    results = []

    for ticker, df in data_dict.items():
        if len(df) < 30:
            continue

        # 기술적 지표 계산
        df = compute_technical_indicators(df)
        latest = df.iloc[-1]
        current_close = latest['Close']

        # 20일 전 대비 모멘텀 (%)
        price_20d_ago = df['Close'].iloc[-20] if len(df) >= 20 else df['Close'].iloc[0]
        momentum_1m = ((current_close - price_20d_ago) / price_20d_ago) * 100

        # 거래량 급증 여부 (최근 3일 평균 vs 20일 평균)
        recent_3d_vol = df['Volume'].iloc[-3:].mean()
        vol_sma20 = latest['Vol_SMA_20']
        vol_ratio = recent_3d_vol / vol_sma20 if vol_sma20 > 0 else 1.0
        volume_surge = vol_ratio > 1.5

        # 추세 판별
        positive_drift = (current_close > latest['SMA_20']) and (momentum_1m > 0)

        # IV Rank / Percentile 계산
        iv_rank, iv_pct = compute_iv_rank_percentile(df)

        # 볼린저 밴드 수축 여부 (최근 60일 중 하위 25%)
        bb_width_series = df['BB_Width'].dropna().tail(60)
        bb_contracted = False
        if len(bb_width_series) > 20:
            bb_pct_rank = (bb_width_series < latest['BB_Width']).sum() / len(bb_width_series) * 100
            bb_contracted = bb_pct_rank < 25

        # MACD 교차 감지 (최근 3일 내 히스토그램 부호 전환)
        macd_hist_recent = df['MACD_Hist'].dropna().tail(5)
        macd_cross = False
        if len(macd_hist_recent) >= 3:
            macd_cross = (macd_hist_recent.iloc[-3] < 0) and (macd_hist_recent.iloc[-1] > 0)

        # [추가] 섹터 및 산업 정보 미리 가져오기 (N/A 방지)
        sector, industry = 'N/A', 'N/A'
        import sqlite3
        try:
            conn = sqlite3.connect("metadata_cache.sqlite")
            cur = conn.cursor()
            cur.execute("SELECT sector, industry FROM metadata WHERE ticker = ?", (ticker,))
            db_row = cur.fetchone()
            if db_row:
                sector, industry = db_row
            conn.close()
        except: pass

        results.append({
            'Node (자산명)': ticker,
            'Sector': sector,
            'Industry': industry,
            'Price (현재가)': round(current_close, 2),
            'Market Cap (시가총액)': _MARKET_CAP_MAP.get(ticker, 0),
            'Momentum (1개월 모멘텀)': round(momentum_1m, 2),
            'RSI (상대강도)': round(latest['RSI'], 1) if pd.notna(latest['RSI']) else 50,
            'IV Rank (변동성 순위)': iv_rank,
            'Vol Ratio (거래 배수)': round(vol_ratio, 2),
            'Positive Drift (상승 추세 지속)': positive_drift,
            'Volume Surge (거래량 급증)': volume_surge,
            'BB Contract (변동성 수축)': bb_contracted,
            'MACD Cross (추세 전환)': macd_cross,
        })

    return pd.DataFrame(results)


# -------------------------------------------------------
# 8. VCT (Variance Contraction Target) 자동 분류
# -------------------------------------------------------
def classify_vct_targets(analyzed_df):
    """
    Variance Contraction Target (변동성 수축 후 확대 예상 타깃)을 자동 분류합니다.
    """
    if analyzed_df.empty:
        return pd.DataFrame()

    mask = (
        (analyzed_df['IV Rank (변동성 순위)'].notna()) &
        (analyzed_df['IV Rank (변동성 순위)'] < 25) &
        (analyzed_df['RSI (상대강도)'].notna()) &
        (analyzed_df['RSI (상대강도)'] >= 30) &
        (analyzed_df['RSI (상대강도)'] <= 55) &
        (analyzed_df['MACD Cross (추세 전환)'] == True) &
        (analyzed_df['BB Contract (변동성 수축)'] == True)
    )
    return analyzed_df[mask].copy()


def classify_vct_relaxed(analyzed_df):
    """
    완화된 VCT 필터 (2개 이상의 시그널 충족 시 타깃으로 분류)
    """
    if analyzed_df.empty:
        return pd.DataFrame()

    df = analyzed_df.copy()
    # 각 조건 충족 여부를 점수화
    df['VCT_Score'] = 0
    if 'IV Rank (변동성 순위)' in df.columns:
        df.loc[(df['IV Rank (변동성 순위)'].notna()) & (df['IV Rank (변동성 순위)'] < 35), 'VCT_Score'] += 1
    if 'RSI (상대강도)' in df.columns:
        df.loc[(df['RSI (상대강도)'].notna()) & (df['RSI (상대강도)'] >= 25) & (df['RSI (상대강도)'] <= 65), 'VCT_Score'] += 1
    if 'MACD Cross (추세 전환)' in df.columns:
        df.loc[df['MACD Cross (추세 전환)'] == True, 'VCT_Score'] += 1
    if 'BB Contract (변동성 수축)' in df.columns:
        df.loc[df['BB Contract (변동성 수축)'] == True, 'VCT_Score'] += 1

    return df[df['VCT_Score'] >= 2].sort_values('VCT_Score', ascending=False)


# -------------------------------------------------------
# 9. 해석 리포트 자동 생성
# -------------------------------------------------------
def generate_analysis_report(row):
    """
    개별 VCT 종목에 대한 상세 해석 리포트를 마크다운 텍스트로 생성합니다.
    """
    ticker = row['Node (자산명)']
    report_lines = [f"### 📋 {ticker} — Comprehensive Node Analysis (종합 노드 분석 리포트)\n"]

    try:
        stock = yf.Ticker(ticker)
        
        # 1. 기업 기본 정보
        info = stock.info
        raw_sector = info.get('sector', 'N/A')
        sector = SECTOR_MAP.get(raw_sector, raw_sector)
        industry = info.get('industry', 'N/A')
        summary = info.get('longBusinessSummary', '')
        summary_short = summary.split('.')[0] + '.' if summary else '회사 설명 정보가 없습니다.'

        report_lines.append("#### 🏢 Corporate Profile (기업 프로필)")
        report_lines.append(f"- **Sector/Industry (섹터/산업):** {sector} / {industry}")
        report_lines.append(f"- **Description (기업 개요):** {summary_short}")
        
        # 시가총액 이중 표기 추가
        try:
            m_cap_usd = info.get('marketCap', 0)
            rate_ticker = yf.Ticker("USDKRW=X")
            ex_rate = rate_ticker.history(period="1d")['Close'].iloc[-1]
            m_cap_krw = m_cap_usd * ex_rate
            
            mc_usd_f = f"${m_cap_usd / 1e9:.2f}B" if m_cap_usd > 0 else "N/A"
            mc_krw_f = f"{m_cap_krw / 1e12:.2f}조 원" if m_cap_krw > 0 else "N/A"
            
            report_lines.append(f"- **Market Cap (시가총액):** <span style='color:#D2A8FF; font-weight:bold;'>{mc_usd_f} / {mc_krw_f}</span> (₩{ex_rate:,.2f})")
            
            # 지수 편입 정보 (체급 파악)
            sp500 = get_sp500_tickers()
            ndx100 = get_nasdaq100_tickers()
            memberships = []
            if ticker in sp500: memberships.append("S&P 500")
            if ticker in ndx100: memberships.append("NASDAQ 100")
            
            if memberships:
                member_str = ", ".join(memberships)
                report_lines.append(f"- **Index Membership (지수 편입):** <span style='color:#58A6FF; font-weight:bold;'>{member_str}</span>\n")
            else:
                report_lines.append(f"- **Index Membership (지수 편입):** Mid/Small Cap (기타 지수)\n")
        except:
            report_lines.append("- **Market Cap (시가총액):** N/A\n")

        # 2. 어닝 분석 (최근 결과 및 향후 일정)
        report_lines.append("#### 📊 Earnings Intelligence (어닝 분석)")
        try:
            # 2-1. 확정된 최근 실적 찾기 (Reported EPS가 있는 최상단 행)
            earnings_dates = stock.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                # Reported EPS가 실존하는 데이터만 필터링
                confirmed_earnings = earnings_dates[earnings_dates['Reported EPS'].notna()]
                
                if not confirmed_earnings.empty:
                    latest_earning = confirmed_earnings.iloc[0] # 가장 최근 확정 실적
                    eps_est = latest_earning.get('EPS Estimate')
                    eps_act = latest_earning.get('Reported EPS')
                    surprise = latest_earning.get('Surprise(%)')
                    
                    # 어닝 서프라이즈 색상 및 텍스트 구성
                    surprise_str = "N/A"
                    if pd.notna(surprise):
                        color = "#00E676" if surprise > 0 else "#FF5252"
                        # 예상치 대비 실제치를 함께 보여주어 비율의 왜곡(기저효과)을 설명
                        surprise_str = f"<span style='color:{color}; font-weight:bold;'>{surprise:+.2f}% ({'Surprise' if surprise > 0 else 'Shock'})</span>"
                    
                    # 어닝 상세 (예상 vs 실제)
                    report_lines.append(f"- **Last Earnings Result (최근 실적):** {surprise_str}")
                    report_lines.append(f"  - (예상: `${eps_est:.2f}` / 실제: `${eps_act:.2f}`)")
                    
                    # 어닝 당일 주가 변동 (NaN 방지 및 정밀화)
                    earning_day = confirmed_earnings.index[0]
                    # 어닝 전후 데이터를 넉넉히 가져와서 정확한 영업일 매칭
                    hist = stock.history(start=earning_day - pd.Timedelta(days=5), end=earning_day + pd.Timedelta(days=5))
                    price_change_str = "N/A"
                    if len(hist) >= 2:
                        try:
                            # 어닝 날짜와 가장 가까운 인덱스 찾기
                            day_idx = hist.index.get_indexer([earning_day], method='nearest')[0]
                            if day_idx > 0:
                                p_change = ((hist['Close'].iloc[day_idx] - hist['Close'].iloc[day_idx-1]) / hist['Close'].iloc[day_idx-1]) * 100
                                p_color = "#00E676" if p_change > 0 else "#FF5252"
                                price_change_str = f"<span style='color:{p_color}; font-weight:bold;'>{p_change:+.2f}%</span>"
                        except: pass
                    report_lines.append(f"- **Price Action on Earnings (어닝 날 주가 변동):** {price_change_str}")

            # 2-2. 다음 어닝 일정 (미발표 데이터)
            next_date = "N/A"
            calendar = stock.calendar
            if calendar is not None and 'Earnings Date' in calendar:
                dates = calendar['Earnings Date']
                if isinstance(dates, list) and dates:
                    next_date = dates[0].strftime('%Y-%m-%d')
                elif hasattr(dates, 'strftime'):
                    next_date = dates.strftime('%Y-%m-%d')
            report_lines.append(f"- **Next Earnings Date (다음 실적 발표):** {next_date}\n")
            
        except Exception as e:
            report_lines.append(f"- 어닝 정보 분석 중 오류: {e}\n")

        # 3. 최근 뉴스 및 심리 체크
        report_lines.append("#### 📰 Recent Catalyst (최근 주요 뉴스 및 전문 분석 요약)")
        try:
            news = stock.news
            if news:
                item = news[0]
                content = item.get('content', {})
                title = content.get('title', 'N/A')
                summary_raw = content.get('summary', title)
                link = content.get('canonicalUrl', {}).get('url', '#') if isinstance(content.get('canonicalUrl'), dict) else content.get('canonicalUrl', '#')
                
                # 감성 분석 키워드
                bullish_words = ['up', 'buy', 'growth', 'positive', 'beat', 'gain', 'surge', 'higher', 'outperform', 'raise', 'upgrade']
                bearish_words = ['down', 'sell', 'drop', 'negative', 'miss', 'loss', 'plunge', 'lower', 'underperform', 'cut', 'downgrade']
                
                t_lower = (title + summary_raw).lower()
                sentiment_label = "Neutral (중립)"
                if any(w in t_lower for w in bullish_words): 
                    sentiment_label = "<span style='color:#00E676; font-weight:bold;'>Bullish (호재성) 📈</span>"
                elif any(w in t_lower for w in bearish_words): 
                    sentiment_label = "<span style='color:#FF5252; font-weight:bold;'>Bearish (악재성) 📉</span>"
                
                report_lines.append(f"- **Latest Issue (최신 이슈):** [{title}]({link})")
                report_lines.append(f"- **Sentiment Check (심리 체크):** {sentiment_label}\n")
            else:
                report_lines.append("- 현재 탐지된 최신 뉴스가 없습니다.\n")
        except:
            report_lines.append("- 뉴스 분석 실패\n")

    except Exception as e:
        report_lines.append(f"> ⚠ 데이터 로드 오류: {e}\n")

    # 4. 기술적 변동성 분석 (HTML 색상 적용)
    report_lines.append("#### 📈 Technical Variance Analysis (기술적 변동성 분석)")
    
    # IV Rank
    iv_rank = row.get('IV Rank (변동성 순위)')
    if iv_rank is not None:
        color = "#00E676" if iv_rank < 50 else "#FF5252"
        desc = "프리미엄 저평가 구간" if iv_rank < 25 else ("평균 이하 구간" if iv_rank < 50 else "변동성 과열 구간")
        report_lines.append(f"- **IV Rank (변동성 순위): <span style='color:{color}; font-weight:bold;'>{iv_rank}%</span>** → {desc}")

    # RSI
    rsi = row.get('RSI (상대강도)')
    if rsi is not None:
        color = "#00E676" if rsi <= 55 else "#FF5252"
        desc = "과매도 반등" if rsi < 30 else ("상승 모멘텀 형성" if rsi <= 55 else "과매수/강세 구간")
        report_lines.append(f"- **RSI (상대강도지수): <span style='color:{color}; font-weight:bold;'>{rsi}</span>** → {desc}")

    # 시그널 기호 색상화
    signals = [
        ('MACD Cross (추세 전환)', '✳', '단기 추세 상방 전환 (골든크로스)'),
        ('BB Contract (변동성 수축)', '◉', '에너지 응축 (변동성 폭발 전조)'),
        ('Positive Drift (상승 추세 지속)', '↗', '이평선 상향 안정적 우상향'),
        ('Volume Surge (거래량 급증)', '⚡', '수급 급증 및 모멘텀 유입')
    ]
    for key, icon, text in signals:
        if row.get(key):
            report_lines.append(f"- **{key}: <span style='color:#00E676; font-weight:bold;'>{icon}</span>** → {text}")

    return "\n".join(report_lines)


# -------------------------------------------------------
# 10. 히트맵(Heatmap) 데이터 수집 함수
# -------------------------------------------------------
# Finviz 스타일의 시장 히트맵을 그리기 위해 필요한 데이터를 수집합니다.
# 나스닥100, 러셀2000 구성종목의 섹터/시총/일일수익률 정보를 가져옵니다.
# -------------------------------------------------------

def get_nasdaq100_tickers():
    """
    나스닥 100 지수 구성종목 리스트를 반환합니다.
    위키피디아에서 실시간 크롤링을 시도하고, 실패 시 하드코딩된 리스트를 사용합니다.
    
    :return: 나스닥100 구성종목 티커 리스트 (예: ['AAPL', 'MSFT', ...])
    """
    try:
        # 위키피디아 나스닥100 페이지에서 구성종목 테이블을 크롤링합니다
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        
        # 테이블 중 'Ticker' 또는 'Symbol' 컬럼이 있는 것을 찾습니다
        for table in tables:
            cols_lower = [str(c).lower() for c in table.columns]
            if 'ticker' in cols_lower:
                col_idx = cols_lower.index('ticker')
                tickers = table.iloc[:, col_idx].tolist()
                # 티커 문자열 정리 (공백 제거, 빈 값 제외)
                tickers = [str(t).strip() for t in tickers if pd.notna(t) and str(t).strip()]
                if len(tickers) > 50:  # 최소 50개 이상이어야 유효한 테이블
                    print(f"[Engine] 위키피디아에서 나스닥100 종목 {len(tickers)}개 로드 완료!")
                    return tickers
            elif 'symbol' in cols_lower:
                col_idx = cols_lower.index('symbol')
                tickers = table.iloc[:, col_idx].tolist()
                tickers = [str(t).strip() for t in tickers if pd.notna(t) and str(t).strip()]
                if len(tickers) > 50:
                    print(f"[Engine] 위키피디아에서 나스닥100 종목 {len(tickers)}개 로드 완료!")
                    return tickers
    except Exception as e:
        print(f"[Engine] 나스닥100 크롤링 실패 ({e}). 폴백 리스트 사용.")

    # [폴백] 위키피디아 접근 실패 시 하드코딩된 나스닥100 대표 종목 리스트
    return [
        'AAPL', 'ABNB', 'ADBE', 'ADI', 'ADP', 'ADSK', 'AEP', 'AMAT', 'AMD', 'AMGN',
        'AMZN', 'ANSS', 'APP', 'ARM', 'ASML', 'AVGO', 'AXON', 'AZN', 'BIIB', 'BKNG',
        'BKR', 'CCEP', 'CDNS', 'CDW', 'CEG', 'CHTR', 'CMCSA', 'COIN', 'COST', 'CPRT',
        'CRWD', 'CSCO', 'CSGP', 'CTAS', 'CTSH', 'DASH', 'DDOG', 'DLTR', 'DXCM', 'EA',
        'EXC', 'FANG', 'FAST', 'FTNT', 'GEHC', 'GFS', 'GILD', 'GOOG', 'GOOGL', 'HON',
        'IDXX', 'ILMN', 'INTC', 'INTU', 'ISRG', 'KDP', 'KHC', 'KLAC', 'LIN', 'LRCX',
        'LULU', 'MAR', 'MCHP', 'MDB', 'MDLZ', 'MELI', 'META', 'MNST', 'MRVL', 'MSFT',
        'MU', 'NFLX', 'NVDA', 'NXPI', 'ODFL', 'ON', 'ORLY', 'PANW', 'PAYX', 'PCAR',
        'PDD', 'PEP', 'PLTR', 'PYPL', 'QCOM', 'REGN', 'ROP', 'ROST', 'SBUX', 'SMCI',
        'SNPS', 'TEAM', 'TMUS', 'TSLA', 'TTD', 'TTWO', 'TXN', 'VRSK', 'VRTX', 'WBD',
        'WDAY', 'XEL', 'ZS'
    ]


def get_russell2000_top_tickers():
    """
    러셀 2000 지수의 대표 종목 리스트를 반환합니다.
    러셀2000은 종목이 2000개로 매우 많아 전부 로드하면 느리므로,
    iShares Russell 2000 ETF (IWM) 기준 상위 보유종목 약 120개를 대표로 사용합니다.
    
    :return: 러셀2000 대표 종목 티커 리스트
    """
    # 러셀2000 ETF(IWM)의 주요 구성종목 (시총 상위 약 120개)
    # 소형주 중심이므로 빅테크와는 다른 종목들이 포함됩니다
    return [
        'SMCI', 'INSM', 'FN', 'CORT', 'ITCI', 'KTOS', 'DUOL', 'EXLS',
        'FLR', 'SFM', 'LNTH', 'ACIW', 'PIPR', 'PCVX', 'MATX', 'CALM',
        'ONTO', 'CBT', 'IBKR', 'NOVT', 'AIT', 'CSWI', 'AVAV', 'EXPO',
        'PLXS', 'MLI', 'MMSI', 'OMCL', 'CVLT', 'RMBS', 'ALKS', 'GPI',
        'ENSG', 'POWL', 'VCEL', 'BOOT', 'RXRX', 'PRGS', 'KRYS', 'IIPR',
        'ROAD', 'SPSC', 'TNET', 'SITM', 'HLIT', 'CRVL', 'HLNE', 'ATGE',
        'COOP', 'UFPI', 'CRS', 'ACLS', 'IPAR', 'GKOS', 'NUVB', 'RDNT',
        'BGC', 'LBRT', 'RKLB', 'ARCB', 'DOCS', 'AXSM', 'STEP', 'MARA',
        'RIOT', 'HQY', 'JBT', 'QLYS', 'APAM', 'FELE', 'WDFC', 'BRKR',
        'NEOG', 'BL', 'LSCC', 'FSS', 'SIG', 'OII', 'ACAD', 'JOBY',
        'AGIO', 'OLED', 'CGNX', 'VRNS', 'FTDR', 'MGNI', 'HIMS', 'IONQ',
        'UPST', 'ASAN', 'BILL', 'SOUN', 'AFRM', 'HOOD', 'SOFI', 'CHWY',
        'CELH', 'NVST', 'DKNG', 'PLTK', 'CARG', 'SPT', 'TDW', 'FLNC',
        'FORM', 'GERN', 'CRSP', 'VERX', 'ALRM', 'RELY', 'ANET', 'TENB',
        'TASK', 'RAMP', 'EVTC', 'CWAN', 'PAGP', 'WK', 'CWK', 'KNF'
    ]


def fetch_heatmap_data(tickers):
    """
    히트맵 데이터를 고속으로 수집합니다. (SQLite 캐시 연동)
    
    최적화 전략:
    1. 주가 데이터: yf.download로 전체 티커 일괄 수집 (이미 빠름)
    2. 메타데이터 (섹터, 이름, 시총): 
       - 먼저 SQLite DB에서 기존 캐시를 가져옴.
       - 캐시에 없는 티커만 골라서 yf.Ticker().info를 호출 (최소화).
       - 새로 얻은 정보는 다시 DB에 저장.
    """
    results = []
    try:
        # 1. 주가 데이터 일괄 수집 (최근 5일)
        price_data = yf.download(tickers, period='5d', group_by='ticker', threads=True, progress=False)
        
        # 2. 캐시된 메타데이터 조회
        cached_df = get_cached_metadata(tickers)
        cached_tickers = cached_df['ticker'].tolist()
        
        # 3. 캐시에 없는 티커 확인
        missing_tickers = [t for t in tickers if t not in cached_tickers]
        
        # 4. 누락된 티커만 API 호출하여 메타데이터 수집
        new_metadata = []
        if missing_tickers:
            print(f"[Heatmap] 캐시 누락 {len(missing_tickers)}개 업데이트 중...")
            for t in missing_tickers:
                try:
                    s = yf.Ticker(t)
                    info = s.info
                    new_metadata.append({
                        'ticker': t,
                        'name': info.get('shortName', t),
                        'sector': info.get('sector', 'Other'),
                        'market_cap': info.get('marketCap', 0)
                    })
                except: continue
            
            # 새 메타데이터 캐시 저장
            if new_metadata:
                update_metadata_cache(new_metadata)
        
        # 5. 최종 메타데이터 확보 (캐시 + 신규)
        full_metadata_df = get_cached_metadata(tickers)
        metadata_map = full_metadata_df.set_index('ticker').to_dict('index')
        
        # 6. 주가와 메타데이터 결합
        for ticker in tickers:
            try:
                # 주가 수익률 계산
                if len(tickers) == 1: ticker_df = price_data
                else:
                    if ticker not in price_data.columns.get_level_values(0): continue
                    ticker_df = price_data[ticker]
                
                closes = ticker_df['Close'].dropna()
                if len(closes) < 2: continue
                
                daily_change = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
                
                # 메타데이터 맵에서 정보 추출
                m = metadata_map.get(ticker, {})
                if not m or m.get('market_cap', 0) <= 0: continue
                
                results.append({
                    'ticker': ticker,
                    'name': m.get('name', ticker),
                    'sector': SECTOR_MAP.get(m.get('sector'), m.get('sector', 'Other')),
                    'market_cap': m.get('market_cap'),
                    'daily_change_pct': round(daily_change, 2),
                    'price': round(closes.iloc[-1], 2)
                })
            except: continue
            
    except Exception as e:
        print(f"[Heatmap] 고속 엔진 오류: {e}")
    
    return results
