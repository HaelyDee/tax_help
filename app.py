import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pandas as pd
import io

# --- CSV 로드 로직 ---
@st.cache_data # 데이터를 매번 새로 읽지 않도록 스팀릿 캐싱 기능을 사용하면 더 빠릅니다.
def load_relation_data():
    return pd.read_csv('relation_data.csv', encoding='cp949') #증여액 공제를 위한 가족관계별 공제금액 데이터

# 계산 결과 저장을 위한 세션 설정
if 'calculated_df' not in st.session_state:
    st.session_state.calculated_df = None
if 'result_summary' not in st.session_state:
    st.session_state.result_summary = {}

# --- 페이지 설정 ---
st.set_page_config(page_title="해외주식 증여세 계산기", layout="wide")

st.title("📈 해외주식 증여세 평균시세 계산기")
st.markdown("""
수증일 전후 2개월(총 4개월)의 주가와 환율을 자동으로 수집하여 평균 가액을 계산합니다.
""")

# --- 사이드바: 입력창 ---
st.sidebar.header("입력 정보")
ticker = st.sidebar.text_input("종목 티커 (예: NVDA, TSLA)", value="NVDA").upper()
stock_count = st.sidebar.number_input("주식 수량", value=10)
gift_date = st.sidebar.date_input("수증일 (증여받은 날)", value="today")
rel_df = load_relation_data()
relationship = st.sidebar.selectbox(
    "증여자와의 관계(수증자는 증여자의..)",
    options=rel_df['rel_nm'].tolist() # CSV에 있는 이름들을 자동으로 가져옴
)

# --- 데이터 생성 ---
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
        avg_val = df['KRW_Value'].mean() * stock_count

    ### 세율 추가 ###
    def calculate_tax(amount, relationship_name):
        # CSV 데이터 불러오기
        rel_df = load_relation_data()
        
        # 2. 선택된 관계명(rel_nm)에 해당하는 공제금액(ddt_amt) 찾기
        # 일치하는 행이 없을 경우를 대비해 기본값 0 설정
        try:
            deduction = rel_df.loc[rel_df['rel_nm'] == relationship_name, 'ddt_amt'].values[0]
        except IndexError:
            deduction = 0
        
        # 3. 과세표준 계산
        tax_base = max(0, amount - deduction)
        
        # 4. 세율 및 누진공제 적용
        if tax_base <= 100_000_000:
            tax = tax_base * 0.1
        elif tax_base <= 500_000_000:
            tax = tax_base * 0.2 - 10_000_000
        elif tax_base <= 1_000_000_000:
            tax = tax_base * 0.3 - 60_000_000
        elif tax_base <= 3_000_000_000:
            tax = tax_base * 0.4 - 160_000_000
        else:
            tax = tax_base * 0.5 - 460_000_000
            
        return deduction, tax_base, tax
        
        # 결과를 세션 상태에 저장 (이게 핵심!)
        st.session_state.calculated_df = df
        st.session_state.result_summary = {
            'ticker': ticker,
            'avg_val': avg_val,
            'total_amount': stock_count,
            'deduction': deduction,
            'tax': tax,
            'gift_date': gift_date
        }

    # 결과 출력 로직 (계산 버튼 클릭 여부와 상관없이 데이터가 있으면 항상 표시)
    if st.session_state.calculated_df is not None:
        res = st.session_state.result_summary
        df = st.session_state.calculated_df

        # 상단 요약 카드
        col1, col2 = st.columns(2)
        col1.metric("최종 평균 가액", f"{avg_val:,.2f} 원")
        col2.metric("분석 기간", f"{start_date} ~ {end_date}")
        
        total_amount = avg_val
        deduction, tax_base, tax = calculate_tax(total_amount, relationship)

        st.divider() # 구분선
        st.subheader("💰 예상 증여세 산출 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("총 증여가액", f"{total_amount:,.0f} 원")
        c2.metric("공제 금액", f"{deduction:,.0f} 원")
        c3.metric("예상 납부세액", f"{tax:,.0f} 원", delta_color="inverse")

        st.caption(f"※ 과세표준: {tax_base:,.0f} 원 (산출세액은 신고세액공제 등이 제외된 단순 참고용입니다.)")
        
        st.divider() # 구분선
        # 데이터 차트
        st.subheader(f"{ticker} 원화 환산 주가 추이")
        st.line_chart(df['KRW_Value'])
        
        # 데이터 테이블
        st.subheader("상세 데이터 내역")
        st.dataframe(df.style.format("{:,.2f}"))

        # 5. 엑셀 파일 생성 로직
        # 메모리 상에서 엑셀 파일을 만듭니다.
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1) 인덱스(날짜)를 일반 열로 변환하고 이름을 '일자'로 변경
            excel_df = df.copy()
            excel_df.index.name = '일자'
            excel_df = excel_df.reset_index()
            
            # 2) '일자' 컬럼의 형식을 YYYY-MM-DD 문자열로 변환 (엑셀에서 깔끔하게 보이게 함)
            excel_df['일자'] = excel_df['일자'].dt.strftime('%Y-%m-%d')
            
            # 3) 엑셀로 저장 (index=False를 꼭 넣어주세요)
            excel_df.to_excel(writer, sheet_name='증여세_산출근거', index=False)
            
            # 요약 정보도 별도 시트에 넣고 싶다면 추가 가능
            summary_data = {
                '항목': ['종목명', '수량', '평균가액', '총 증여가액', '공제액', '예상세액'],
                '내역': [ticker, stock_count, f"{avg_val:,.0f}", f"{total_amount:,.0f}", f"{deduction:,.0f}", f"{tax:,.0f}"]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='요약리포트', index=False)

        excel_data = output.getvalue()

        # 6. 다운로드 버튼 배치
        st.download_button(
            label="📄 국세청 제출용 증빙자료(Excel) 다운로드",
            data=output.getvalue(),
            file_name=f"증여세_증빙_{res['ticker']}_{res['gift_date']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("왼쪽 사이드바에서 정보를 입력하고 '계산하기' 버튼을 눌러주세요.")