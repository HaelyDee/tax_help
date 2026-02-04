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
        df, start_str, end_str, is_incomplete, reportable_date = get_stock_and_fx_data(ticker, gift_date)
        avg_val = df['KRW_Value'].mean()
        total_amt = avg_val * stock_count
        deduction, tax_base, tax = calculate_tax_logic(total_amt, relationship)

        # 결과 저장
        st.session_state.calculated_df = df
        st.session_state.result_summary = {
            'ticker': ticker, 'avg_val': avg_val, 'total_amount': total_amt,
            'deduction': deduction, 'tax_base': tax_base, 'tax': tax,
            'gift_date': gift_date, 'start_date': start_str, 'end_date': end_str,
            'stock_count': stock_count,
            'is_incomplete': is_incomplete,
            'reportable_date': reportable_date
        }

# --- 결과 화면 출력 (View) ---
if st.session_state.calculated_df is not None:
    res = st.session_state.result_summary
    df = st.session_state.calculated_df

    # [추가] 데이터가 불완전할 경우 경고창 띄우기
    if res.get('is_incomplete', False):
        st.warning(f"""
            ⚠️ **주의: 아직 평가기간(수증일 전후 2개월)이 종료되지 않았습니다.**
            
            현재 결과는 오늘까지의 데이터를 바탕으로 계산된 임시 수치이며, 세법상 정확한 계산 결과가 아닙니다.
            정확한 신고용 데이터는 **{res['reportable_date']}**부터 조회가 가능합니다.
        """)

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

    # 엑셀 다운로드
    st.divider()
    st.subheader("📋 증빙 자료 준비")

    # 엑셀 파일 생성 로직 (In-memory)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1) 상세 데이터 시트
        excel_df = df.copy()
        excel_df.index.name = '일자'
        excel_df = excel_df.reset_index()
        
        # 엑셀에서 보기 좋게 날짜 형식 변환
        excel_df['일자'] = excel_df['일자'].dt.strftime('%Y-%m-%d')
        excel_df.to_excel(writer, sheet_name='증여세_산출근거', index=False)
        
        # 2) 요약 리포트 시트
        # incomplete 상태에 따른 비고란 추가
        status_note = "확정 데이터" if not res.get('is_incomplete', False) else f"임시 데이터 (확정 가능일: {res.get('reportable_date')})"
        
        summary_data = {
            '항목': [
                '종목명', '수량', '평균가액(1주)', '총 증여가액', 
                '공제액', '과세표준', '예상세액', '데이터 출처', '산출 기준'
            ],
            '내역': [
                res['ticker'], 
                f"{res['stock_count']:,}", 
                f"{res['avg_val']:,.0f}", 
                f"{res['total_amount']:,.0f}", 
                f"{res['deduction']:,.0f}",
                f"{res['tax_base']:,.0f}",
                f"{res['tax']:,.0f}",
                "Yahoo Finance (yfinance API)",
                "상증세법상 수증일 전후 2개월 종가 평균"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='요약리포트', index=False)

    # 다운로드 버튼
    st.download_button(
        label="📄 국세청 제출용 증빙자료(Excel) 다운로드",
        data=output.getvalue(),
        file_name=f"증여세_증빙_{res['ticker']}_{res['gift_date']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()
    # 도움말/출처 섹션
    with st.expander("ℹ️ 데이터 출처 및 산출 기준 안내"):
        st.markdown(f"""
        * **주가 정보**: Yahoo Finance ({res['ticker']} 종가 기준)
        * **환율 정보**: Yahoo Finance (USDKRW=X 종가 기준)
        * **산출 방식**: 상속세 및 증여세법 제63조 및 동법 시행령 제52조에 의거, 평가기준일(수증일) 전후 각 2개월 동안 공표된 매일의 거래소 최종 시세가액(종가)의 평균액으로 계산합니다.
        * **환율 적용**: 매일의 종가 환율을 해당 날짜의 주가에 직접 곱하여 원화 환산 가액을 산출한 뒤, 그 전체 합계의 평균을 구합니다.
        """)

    st.divider()
    st.subheader("🎢 주가 추이")
    st.line_chart(df['KRW_Value'])

else:
    st.info("왼쪽에서 정보를 입력하고 '계산하기'를 눌러주세요.")