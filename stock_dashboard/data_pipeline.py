import yfinance as yf
import pandas as pd
import numpy as np

# 사용자 분들을 위한 자세한 한글 주석을 포함합니다.

# 1. 관심 종목 리스트 설정 (Universe)
# 미국 주식 시장을 주도하는 대표적인 빅테크 및 AI 인프라 관련 종목들입니다.
DEFAULT_UNIVERSE = [
    'AAPL', 'ACHR', 'AMD', 'AMZN', 'ARM', 'ASTS', 'AVGO', 'CRWD', 
    'ELV', 'GOOGL', 'HIMS', 'HOOD', 'INTC', 'IONQ', 'IREN', 'JOBY', 
    'LAES', 'MARA', 'META', 'MSFT', 'NVDA', 'ORCL', 'PANW', 'PL', 
    'PLTR', 'QXO', 'RBLX', 'RDDT', 'RDW', 'RGTI', 'RKLB', 'RXRX', 
    'SMCI', 'TEM', 'TSLA', 'TSLL', 'UFO', 'ZETA'
]

def fetch_stock_data(tickers, period='3mo'):
    """
    야후 파이낸스(yfinance) API를 사용하여 주어진 종목 리스트의 
    과거 주가 및 거래량 데이터를 수집하는 함수입니다.
    
    :param tickers: 데이터를 수집할 종목 코드 리스트 (예: ['AAPL', 'TSLA'])
    :param period: 가져올 데이터의 기간 (기본값: '3mo' -> 최근 3개월 분량)
    :return: 종목 코드를 키(Key)로, 데이터프레임(DataFrame)을 값(Value)으로 갖는 딕셔너리
    """
    data_dict = {}
    for ticker in tickers:
        try:
            # yfinance 라이브러리를 통해 특정 종목의 티커(Ticker) 객체 생성
            stock = yf.Ticker(ticker)
            # 설정한 기간(period) 동안의 역사적 주가 데이터 다운로드
            df = stock.history(period=period)
            
            # 데이터가 정상적으로 수집되어 비어있지 않은 경우에만 딕셔너리에 저장합니다.
            if not df.empty:
                data_dict[ticker] = df
        except Exception as e:
            # 에러 발생 시 사용자에게 친절하게 터미널에 알려줍니다.
            print(f"[{ticker}] 데이터 수집 중 오류 발생: {e}")
            
    return data_dict

def analyze_momentum_and_volume(data_dict):
    """
    수집된 주식 데이터를 바탕으로 각 종목의 '최근 1개월 모멘텀'과 
    '거래량 급증 여부'를 분석하는 핵심 필터링 함수입니다.
    
    :param data_dict: fetch_stock_data 함수에서 수집하여 반환한 데이터 딕셔너리
    :return: 종목별 분석 결과가 요약된 데이터프레임 (Pandas DataFrame)
    """
    results = []
    
    for ticker, df in data_dict.items():
        # 분석을 위해서는 최소 20일(약 1개월)치의 데이터가 필요합니다.
        # 데이터가 부족한 상장 초기 종목 등은 건너뜁니다.
        if len(df) < 20:
            continue
            
        # [지표 1] 20일 이동평균선(SMA: Simple Moving Average) 계산
        # 최근 20일 동안의 종가(Close) 평균을 구하여 추세를 파악합니다.
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        # [지표 2] 20일 평균 거래량 계산
        # 거래량이 최근에 얼마나 늘었는지 비교할 기준점이 됩니다.
        df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
        
        # 가장 최근일(오늘 혹은 전일 장마감)의 종가와 20일 이동평균 값을 가져옵니다.
        current_close = df['Close'].iloc[-1]
        sma_20 = df['SMA_20'].iloc[-1]
        
        # [모멘텀 분석] 최근 1개월(20 거래일 전) 대비 현재가 등락률(%) 계산
        price_20d_ago = df['Close'].iloc[-20]
        momentum_1m = ((current_close - price_20d_ago) / price_20d_ago) * 100
        
        # [거래량 분석] 단기 수급이 몰렸는지 확인합니다.
        # 최근 3일간의 평균 거래량이 20일 평균 거래량의 1.5배 이상인지 판별(True/False)
        recent_3d_vol_avg = df['Volume'].iloc[-3:].mean()
        current_vol_sma20 = df['Vol_SMA_20'].iloc[-1]
        volume_spike = recent_3d_vol_avg > (current_vol_sma20 * 1.5)
        
        # [추세 판별] 현재가가 20일 이동평균선 위에 위치하고, 1개월 수익률이 +인 경우 상승 추세로 봅니다.
        uptrend = (current_close > sma_20) and (momentum_1m > 0)
        
        # 계산된 결과를 리스트에 딕셔너리 형태로 차곡차곡 저장합니다.
        results.append({
            'Ticker': ticker,
            'Current Price': round(current_close, 2),
            'Momentum 1M (%)': round(momentum_1m, 2),
            'Uptrend': uptrend,
            'Volume Spike': volume_spike,
            'Recent Vol / SMA20': round(recent_3d_vol_avg / current_vol_sma20, 2) if current_vol_sma20 > 0 else 0
        })
        
    # 리스트 데이터를 표 형태(DataFrame)로 변환하여 반환합니다.
    return pd.DataFrame(results)

def get_options_data(ticker):
    """
    가장 가까운 만기일의 실시간 옵션 체인(Option Chain)을 불러와서 
    콜/풋 거래량을 확인하고 Put/Call Ratio를 계산하는 함수입니다.
    
    :param ticker: 옵션 데이터를 조회할 종목 코드 (예: 'TSLA')
    :return: 만기일, 콜 거래량, 풋 거래량, P/C Ratio 등을 포함한 딕셔너리
    """
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options # 해당 종목에 상장된 모든 옵션 만기일 리스트
        
        # 옵션 상장이 안 된 주식인 경우 None 반환
        if not expirations:
            return None 
            
        # 가장 빠른 만기일(보통 위클리 옵션이나 당월물) 선택
        nearest_expiry = expirations[0]
        opt_chain = stock.option_chain(nearest_expiry)
        
        # 선택된 만기일에 거래된 Call(상승 베팅)과 Put(하락 베팅)의 총 거래량 합산
        total_call_vol = opt_chain.calls['volume'].sum()
        total_put_vol = opt_chain.puts['volume'].sum()
        
        # 야후 파이낸스 특성상 데이터가 누락되어 NaN(Not a Number)일 수 있으므로 0으로 보정
        total_call_vol = 0 if np.isnan(total_call_vol) else total_call_vol
        total_put_vol = 0 if np.isnan(total_put_vol) else total_put_vol
        
        # Put/Call Ratio 계산. (분모가 0이 되어 프로그램이 뻗는 현상 방지)
        pc_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0
        
        return {
            'Expiry': nearest_expiry,
            'Call Volume': total_call_vol,
            'Put Volume': total_put_vol,
            'P/C Ratio': round(pc_ratio, 2)
        }
    except Exception as e:
        # 데이터가 없거나 통신 장애가 발생해도 전체 프로그램이 종료되지 않게 예외 처리
        print(f"[{ticker}] 옵션 데이터 로드 오류: {e}")
        return None

def find_bull_call_spread_candidates(analyzed_df):
    """
    이전 함수(analyze_momentum_and_volume)에서 1차로 필터링된 주식들 중에서,
    실제 옵션 데이터의 수급(Call 거래 우위)을 확인하여 강세 콜 스프레드(Bull Call Spread) 
    전략에 적합한 최종 타점 종목을 찾아냅니다.
    
    [조건 요약] 상승 추세(Uptrend) + 거래량 급증(Volume Spike) + Call 거래량 > Put 거래량
    """
    # 1. 상승 추세이면서 거래량 급증 조건이 True인 종목들만 먼저 추려냅니다. (데이터베이스 필터링과 유사)
    candidates = analyzed_df[(analyzed_df['Uptrend'] == True) & (analyzed_df['Volume Spike'] == True)].copy()
    
    option_results = []
    # 2. 1차 필터를 통과한 우량 후보 종목들의 옵션 데이터만 순차적으로 수집합니다.
    #    (전체 종목 옵션을 다 조회하면 시간이 너무 오래 걸리기 때문입니다.)
    for ticker in candidates['Ticker']:
        opt_data = get_options_data(ticker)
        
        if opt_data: # 옵션 데이터가 정상적으로 수집된 경우
            # [핵심 로직] 상승을 기대하는 Call 거래량이 하락을 대비하는 Put 거래량보다 많은지 판별
            is_bull_setup = opt_data['Call Volume'] > opt_data['Put Volume']
            
            option_results.append({
                'Ticker': ticker,
                'Expiry': opt_data['Expiry'],
                'Call Vol': opt_data['Call Volume'],
                'Put Vol': opt_data['Put Volume'],
                'P/C Ratio': opt_data['P/C Ratio'],
                'Bull Setup': is_bull_setup
            })
            
    opt_df = pd.DataFrame(option_results)
    
    # 만약 옵션 데이터가 하나라도 정상적으로 있다면
    if not opt_df.empty:
        # 주식 데이터 분석본(candidates)과 옵션 데이터 분석본(opt_df)을 종목(Ticker)을 기준으로 합칩니다. (SQL의 JOIN 개념)
        final_df = pd.merge(candidates, opt_df, on='Ticker')
        
        # 마지막으로 콜 거래량이 더 많았던 (Bull Setup == True) 종목만 최종 반환합니다.
        return final_df[final_df['Bull Setup'] == True]
    else:
        # 만족하는 데이터가 아예 없다면 빈 데이터프레임을 돌려줍니다.
        return pd.DataFrame()
