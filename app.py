import streamlit as st
import pandas as pd
import io
from datetime import datetime
from calculator import load_relation_data, get_stock_and_fx_data, calculate_tax_logic
from excel_exporter import generate_excel_report

# 1. 페이지 설정 (세션 값을 동적으로 참조하도록 수정)
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = "expanded" # 초기값은 펼침

st.set_page_config(
    page_title="해외주식 증여세 계산기",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state # 세션 상태 반영
)

# ... (중간 생략: 3. 사이드바 입력 영역까지 동일)




# 세션 상태 초기화 (자바의 생성자 역할)
if 'all_results' not in st.session_state:
    st.session_state.all_results = []
if 'summary_info' not in st.session_state:
    st.session_state.summary_info = {}

# 2. 초기 안내 화면 (데이터가 없을 때만 표시)
if not st.session_state.all_results:
    st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h2 style="color: #FF4B4B;">⬅️ 왼쪽 메뉴를 열어주세요!</h2>
            <p style="font-size: 1.2rem;">
                화면 왼쪽 상단의 <b>'>>'</b> 모양 화살표를 누르시면<br>
                종목과 수량을 입력할 수 있는 메뉴가 나타납니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.warning("👈 좌측 상단 화살표를 눌러 데이터를 입력해야 계산이 시작됩니다.")

st.title("📈 해외주식 증여세 신고용 평균시세 계산기")

# 3. 사이드바 입력 영역
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

# 4. 계산 버튼 클릭 시 로직
if st.sidebar.button("계산하기"):
    # 계산 시작 전 사이드바 상태를 '닫힘'으로 변경 (모바일 대응)
    st.session_state.sidebar_state = "collapsed"
    
    all_results = []
    total_gift_amount_sum = 0
    
    with st.spinner('여러 종목의 데이터를 수집 중입니다...'):
        for stock in stock_inputs:
            # calculator.py 호출
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
            
        # 세금 계산 로직 호출
        deduction, tax_base, tax = calculate_tax_logic(total_gift_amount_sum, relationship)
        
        # 세션에 최종 결과 저장 (변수명 통일)
        st.session_state.all_results = all_results
        st.session_state.summary_info = {
            'total_amt': total_gift_amount_sum,
            'deduction': deduction,
            'tax_base': tax_base,
            'tax': tax,
            'gift_date': gift_date,
            'start_date': start_str,
            'end_date': end_str,
            'rel_nm': relationship
        }
        st.rerun() # 계산 후 즉시 화면 갱신(최상단의 set_page_config를 다시 읽어 사이드바를 닫음)

# 5. 결과 화면 출력 영역
if st.session_state.all_results:
    res_list = st.session_state.all_results
    summary = st.session_state.summary_info

    # 미완성 기간 체크
    is_incomplete_any = any(r.get('is_incomplete', False) for r in res_list)
    if is_incomplete_any:
        report_date = res_list[0].get('reportable_date')
        st.warning(f"⚠️ **주의: 아직 증여 신고를 위한 평가기간이 종료되지 않았습니다.** (확정일: {report_date})")

    st.success("✅ 계산이 완료되었습니다! 아래에서 결과를 확인하세요.")
    
    # 상단 요약 지표
    st.header("💰 전체 증여세 통합 산출 결과")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 합계 가액", f"{summary.get('total_amt', 0):,.0f} 원")
    c2.metric(f"{summary.get('rel_nm', 0)} 증여 공제 금액", f"{summary.get('deduction', 0):,.0f} 원")
    c3.metric("예상 납부세액", f"{summary.get('tax', 0):,.0f} 원")

    # 데이터 출처 안내
    with st.expander("ℹ️ 데이터 출처 및 산출 기준 안내"):
        st.markdown("""
        * **주가/환율 정보**: Yahoo Finance
        * **산출 방식**: 상증세법 제63조에 의거 수증일 전후 각 2개월(총 4개월) 종가 평균액 계산
        * **휴장일 처리**: 주가와 환율 데이터가 모두 존재하는 날의 가액만 산술평균에 포함
        """)

    # 엑셀 다운로드 섹션
    st.divider()
    st.subheader("📋 증빙 자료 준비")
    
    # excel_exporter 호출
    excel_data = generate_excel_report(
        res_list,
        summary,
        is_incomplete_any,
        res_list[0].get('reportable_date')
    )

    st.download_button(
        label="📄 국세청 제출용 증빙자료(Excel) 다운로드",
        data=excel_data,
        file_name=f"증여세_통합_증빙_{summary['gift_date']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.link_button(
    "➡️ 국세청 증여세 신고 페이지 바로가기",
    "https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&tmIdx=41&tm2lIdx=4107000000&tm3lIdx=4107010000",
    type="secondary" # 강조하고 싶으면 primary, 아니면 secondary
    )

    # 종목별 상세 탭
    st.divider()
    st.subheader("🎢 참고 : 종목별 시세 차트")
    tabs = st.tabs([f"📊 {r['ticker']}" for r in res_list])
    for i, tab in enumerate(tabs):
        with tab:
            r = res_list[i]
            st.write(f"**{r['ticker']}** - {r['count']}주")
            st.metric("1주당 평균 가액", f"{r['avg_val']:,.2f} 원")
            st.line_chart(r['df']['KRW_Value'])

