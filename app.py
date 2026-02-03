import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="해외주식 증여세 계산기", layout="wide")

st.title("📈 해외주식 증여세 평균시세 계산기")
st.markdown("""
수증일 전후 2개월(총 4개월)의 주가와 환율을 자동으로 수집하여 평균 가액을 계산합니다.
""")

# --- 사이드바: 입력창 ---
st.sidebar.header("입력 정보")
ticker = st.sidebar.text_input("종목 티커 (예: NVDA, TSLA)", value="NVDA").upper()
gift_date = st.sidebar.date_input("수증일 (증여받은 날)", datetime(2024, 1, 15))

if st.sidebar.button("계산하기"):
    # 1. 날짜 계산
    start_date = (gift_date - timedelta(days=65)).strftime("%Y-%m-%d")
    end_date = (gift_date + timedelta(days=65)).strftime("%Y-%m-%d")
    
    with st.spinner('데이터를 가져오는 중입니다...'):
        # 2. 데이터 다운로드
        stock_data = yf.download(ticker, start=start_date, end=end_date)['Close']
        fx_data = yf.download("USDKRW=X", start=start_date, end=end_date)['Close']

        # 3. 데이터 전처리
        df = pd.DataFrame({
            'Stock_Price': stock_data.iloc[:, 0] if isinstance(stock_data, pd.DataFrame) else stock_data,
            'FX_Rate': fx_data.iloc[:, 0] if isinstance(fx_data, pd.DataFrame) else fx_data
        })
        
        all_days = pd.date_range(start=start_date, end=end_date)
        df = df.reindex(all_days).ffill()
        df['KRW_Value'] = df['Stock_Price'] * df['FX_Rate']
        
        # 4. 결과 출력
        avg_val = df['KRW_Value'].mean()
        
        # 상단 요약 카드
        col1, col2 = st.columns(2)
        col1.metric("최종 평균 가액", f"{avg_val:,.2f} 원")
        col2.metric("분석 기간", f"{start_date} ~ {end_date}")
        
        # 데이터 차트
        st.subheader(f"{ticker} 원화 환산 주가 추이")
        st.line_chart(df['KRW_Value'])
        
        # 데이터 테이블
        st.subheader("상세 데이터 내역")
        st.dataframe(df.style.format("{:,.2f}"))
else:
    st.info("왼쪽 사이드바에서 정보를 입력하고 '계산하기' 버튼을 눌러주세요.")