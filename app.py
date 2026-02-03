import streamlit as st
import pandas as pd
import io
from datetime import datetime
from calculator import load_relation_data, get_stock_and_fx_data, calculate_tax_logic

# 세션 설정
if 'calculated_df' not in st.session_state:
    st.session_state.calculated_df = None
if 'result_summary' not in st.session_state:
    st.session_state.result_summary = {}

st.set_page_config(page_title="해외주식 증여세 계산기", layout="wide")
st.title("📈 해외주식 증여세 평균시세 계산기")

# --- 사이드바 ---
st.sidebar.header("입력 정보")
ticker = st.sidebar.text_input("종목 티커", value="NVDA").upper()
stock_count = st.sidebar.number_input("주식 수량", value=10)
gift_date = st.sidebar.date_input("수증일", value=datetime.now())

rel_df = load_relation_data()
relationship = st.sidebar.selectbox("증여자와의 관계", options=rel_df['rel_nm'].tolist())

# --- 계산 버튼 클릭 시 ---
if st.sidebar.button("계산하기"):
    with st.spinner('데이터 분석 중...'):
        # 로직 레이어 호출
        df, start_str, end_str = get_stock_and_fx_data(ticker, gift_date)
        avg_val = df['KRW_Value'].mean()
        total_amt = avg_val * stock_count
        deduction, tax_base, tax = calculate_tax_logic(total_amt, relationship)

        # 결과 저장
        st.session_state.calculated_df = df
        st.session_state.result_summary = {
            'ticker': ticker, 'avg_val': avg_val, 'total_amount': total_amt,
            'deduction': deduction, 'tax_base': tax_base, 'tax': tax,
            'gift_date': gift_date, 'start_date': start_str, 'end_date': end_str,
            'stock_count': stock_count
        }

# --- 결과 화면 출력 (View) ---
if st.session_state.calculated_df is not None:
    res = st.session_state.result_summary
    df = st.session_state.calculated_df

    # 요약 지표
    col1, col2 = st.columns(2)
    col1.metric("최종 평균 가액 (1주당)", f"{res['avg_val']:,.2f} 원")
    col2.metric("분석 기간", f"{res['start_date']} ~ {res['end_date']}")
    
    st.divider()
    st.subheader("💰 예상 증여세 산출 결과")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 증여가액", f"{res['total_amount']:,.0f} 원")
    c2.metric("공제 금액", f"{res['deduction']:,.0f} 원")
    c3.metric("예상 납부세액", f"{res['tax']:,.0f} 원")
    
    st.line_chart(df['KRW_Value'])

    # 엑셀 다운로드 (생략 - 기존 로직 유지)
    # ... (생략된 엑셀 코드) ...
else:
    st.info("왼쪽에서 정보를 입력하고 '계산하기'를 눌러주세요.")