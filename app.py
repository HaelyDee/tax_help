import streamlit as st
import pandas as pd
import io
from datetime import datetime
from calculator import load_relation_data, get_stock_and_fx_data, calculate_tax_logic
from excel_exporter import generate_excel_report

# 세션 설정
if 'calculated_df' not in st.session_state:
    st.session_state.calculated_df = None
if 'result_summary' not in st.session_state:
    st.session_state.result_summary = {}

st.set_page_config(
    page_title="해외주식 증여세 계산기",
    page_icon="📈", # 브라우저 탭에 아이콘 추가
    layout="wide",
    initial_sidebar_state="expanded" # 모바일에서도 사이드바를 펼친 채 시작
)

if not st.session_state.all_results:
    st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h2 style="color: #FF4B4B;">⬅️ 왼쪽 메뉴를 열어주세요!</h2>
            <p style="font-size: 1.2rem;">
                화면 왼쪽 상단의 <b>'>'</b> 모양 화살표를 누르시면<br>
                종목과 수량을 입력할 수 있는 메뉴가 나타납니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.info("데이터 분석 기간: 수증일 전후 2개월 (총 4개월)")

st.title("📈 해외주식 증여세 신고용 평균시세 계산기")

# --- 사이드바 ---
st.sidebar.header("입력 정보")
num_stocks = st.sidebar.number_input("계산할 종목 수 (최대 5개)", min_value=1, max_value=5, value=1)

stock_inputs = []
for i in range(num_stocks):
    st.sidebar.subheader(f"종목 {i+1}")
    col_t, col_c = st.sidebar.columns([2, 1])
    t = col_t.text_input(f"티커", value="NVDA", key=f"ticker_{i}").upper()
    c = col_c.number_input(f"수량", min_value=1, value=10, key=f"count_{i}")
    stock_inputs.append({'ticker': t, 'count': c})

st.sidebar.divider()
gift_date = st.sidebar.date_input("수증일 (증여받은 날)", value=datetime.now())

rel_df = load_relation_data()
relationship = st.sidebar.selectbox("증여자와의 관계", options=rel_df['rel_nm'].tolist())

# --- 계산 버튼 클릭 시 ---
if st.sidebar.button("계산하기"):
    all_results = []
    total_gift_amount_sum = 0
    with st.spinner('여러 종목의 데이터를 수집 중입니다...'):
        for stock in stock_inputs:
            # calculator.py의 함수 호출
            df, start_str, end_str, is_incomplete, reportable_date = get_stock_and_fx_data(stock['ticker'], gift_date)
            
            avg_val = df['KRW_Value'].mean()
            item_total = avg_val * stock['count']
            total_gift_amount_sum += item_total
            
            all_results.append({
                'ticker': stock['ticker'],
                'count': stock['count'],
                'avg_val': avg_val,
                'item_total': item_total,
                'df': df,
                'is_incomplete': is_incomplete,
                'reportable_date': reportable_date
            })
            
        # 전체 합계에 대한 세금 계산
        deduction, tax_base, tax = calculate_tax_logic(total_gift_amount_sum, relationship)
        
        # 세션 저장
        st.session_state.all_results = all_results
        st.session_state.summary_info = {
            'total_amt': total_gift_amount_sum,
            'deduction': deduction,
            'tax_base': tax_base,
            'tax': tax,
            'gift_date': gift_date,
            'start_date': start_str,
            'end_date': end_str
        }

# --- 결과 화면 출력 (View) ---
if 'all_results' in st.session_state:
    res_list = st.session_state.all_results
    summary = st.session_state.summary_info

    # [수정] 리스트 내의 항목 중 하나라도 is_incomplete가 True인지 확인
    is_incomplete_any = any(r.get('is_incomplete', False) for r in res_list)
    
    if is_incomplete_any:
        # 모든 종목이 동일한 수증일을 공유하므로, 첫 번째 종목의 신고 가능일을 대표로 표시
        report_date = res_list[0].get('reportable_date')
        
        st.warning(f"""
            ⚠️ **주의: 아직 평가기간(전후 2개월)이 종료되지 않은 종목이 포함되어 있습니다.**
            
            현재 결과는 오늘까지의 데이터를 바탕으로 계산된 임시 수치이며, 세법상 정확한 계산 결과가 아닙니다.
            정확한 신고용 데이터는 **{report_date}**부터 조회가 가능합니다.
        """)

# 1. 상단 요약 (전체 종목 합산)
    st.header("💰 전체 증여세 통합 산출 결과")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 합계 가액", f"{summary['total_amt']:,.0f} 원")
    c2.metric("공제 금액", f"{summary['deduction']:,.0f} 원")
    c3.metric("예상 납부세액", f"{summary['tax']:,.0f} 원")

    # 2. 종목별 상세 탭
    st.divider()
    tabs = st.tabs([f"📊 {r['ticker']}" for r in res_list])
    
    for i, tab in enumerate(tabs):
        with tab:
            r = res_list[i]
            st.write(f"**{r['ticker']}** - {r['count']}주")
            st.metric("1주당 평균 가액", f"{r['avg_val']:,.2f} 원")
            st.line_chart(r['df']['KRW_Value'])

    # 엑셀 다운로드
    st.divider()
    st.subheader("📋 증빙 자료 준비")

    if st.session_state.all_results:
        # 엑셀 생성 함수 호출 (필요한 데이터만 파라미터로 전달)
        excel_data = generate_excel_report(
            st.session_state.all_results,
            st.session_state.summary_info,
            is_incomplete_any,
            report_date
        )

    # 엑셀 내보내기
    st.download_button(
        label="📄 국세청 제출용 증빙자료(Excel) 다운로드",
        data=excel_data,
        file_name=f"증여세_통합_증빙_{summary['gift_date']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()
    # 도움말/출처 섹션
    with st.expander("ℹ️ 데이터 출처 및 산출 기준 안내"):
        st.markdown(f"""
        * **주가 정보**: Yahoo Finance (종목별 종가 기준)
        * **환율 정보**: Yahoo Finance (USDKRW=X 종가 기준)
        * **산출 방식**: 상속세 및 증여세법 제63조 및 동법 시행령 제52조에 의거, 평가기준일(수증일) 전후 각 2개월 동안 공표된 매일의 거래소 최종 시세가액(종가)의 평균액으로 계산합니다.
        * **휴장일 처리**: **해당 종목 주식시장의 휴장일 또는 국내 공휴일 등으로 인해 환율 정보가 없는 날은 세법상 '가격이 공표되지 않은 날'로 간주하여 계산 범위에서 제외합니다.** 즉, 주가와 환율 데이터가 모두 존재하는 날의 가액만을 산술평균합니다.
        * **환율 적용**: 매일의 종가 환율을 해당 날짜의 주가에 직접 곱하여 원화 환산 가액을 산출한 뒤, 그 전체 합계의 평균을 구합니다.
        """)

else:
    st.info("왼쪽에서 정보를 입력하고 '계산하기'를 눌러주세요.")