import yfinance as yf
import pandas as pd
from datetime import timedelta

def load_relation_data():
    """가족관계 공제 데이터 로드"""
    return pd.read_csv('relation_data.csv', encoding='cp949')

def get_stock_and_fx_data(ticker, gift_date):
    """주가 및 환율 데이터 수집 및 전처리"""
    start_date = (gift_date - timedelta(days=65)).strftime("%Y-%m-%d")
    end_date = (gift_date + timedelta(days=65)).strftime("%Y-%m-%d")
    
    # 데이터 다운로드
    stock_data = yf.download(ticker, start=start_date, end=end_date)['Close']
    fx_data = yf.download("USDKRW=X", start=start_date, end=end_date)['Close']

    # 데이터프레임 병합 및 보간(ffill)
    df = pd.DataFrame({
        'Stock_Price': stock_data.iloc[:, 0] if isinstance(stock_data, pd.DataFrame) else stock_data,
        'FX_Rate': fx_data.iloc[:, 0] if isinstance(fx_data, pd.DataFrame) else fx_data
    })
    
    all_days = pd.date_range(start=start_date, end=end_date)
    df = df.reindex(all_days).ffill()
    df['KRW_Value'] = df['Stock_Price'] * df['FX_Rate']
    
    return df, start_date, end_date

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