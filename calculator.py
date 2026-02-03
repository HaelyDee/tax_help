import yfinance as yf
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime, date

def load_relation_data():
    """가족관계 공제 데이터 로드"""
    return pd.read_csv('relation_data.csv', encoding='cp949')

def get_stock_and_fx_data(ticker, gift_date):
    """주가 및 환율 데이터 수집 및 전처리"""
    # 1. 정확한 전후 2개월 날짜 계산
    # gift_date가 datetime.date 타입일 경우를 대비해 변환
    start_date = gift_date - relativedelta(months=2)
    end_date = gift_date + relativedelta(months=2)

    # [추가] 오늘 날짜와 비교하여 데이터 완성 여부 판단
    today = date.today()
    is_incomplete = end_date > today
    # 신고 가능일: 종료일 다음 날
    reportable_date = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

    # 2. 데이터 다운로드 
    # yfinance는 종료일(end)을 포함하지 않으므로 하루를 더해줍니다.
    stock_data = yf.download(ticker, start=start_date, end=end_date + timedelta(days=1))['Close']
    fx_data = yf.download("USDKRW=X", start=start_date, end=end_date + timedelta(days=1))['Close']

    # 3. 데이터프레임 병합
    df = pd.DataFrame({
        'Stock_Price': stock_data.iloc[:, 0] if isinstance(stock_data, pd.DataFrame) else stock_data,
        'FX_Rate': fx_data.iloc[:, 0] if isinstance(fx_data, pd.DataFrame) else fx_data
    })
    
    # 4. 휴장일 처리 (Forward Fill)
    # 실제 평가 기준은 '해당 기간 내 공표된 가격의 평균'입니다.
    # 거래가 없는 날(주말/공휴일)은 직전 거래일의 가격을 따르는 것이 실무적입니다.
    all_days = pd.date_range(start=start_date, end=end_date)
    df = df.reindex(all_days).ffill()
    
    # 만약 시작일 자체가 휴장일이라 ffill할 데이터가 없다면(NaN), bfill로 메꿔줍니다.
    df = df.bfill()
    
    df['KRW_Value'] = df['Stock_Price'] * df['FX_Rate']
    
    return df, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), is_incomplete, reportable_date

def calculate_tax_logic(amount, relationship_name):
    """세율 및 공제액 계산 로직"""
    rel_df = load_relation_data()
    try:
        deduction = rel_df.loc[rel_df['rel_nm'] == relationship_name, 'ddt_amt'].values[0]
    except (IndexError, KeyError):
        deduction = 0
    
    tax_base = max(0, amount - deduction)
    
    # 누진세율 적용
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