import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 설정
ticker_symbol = "NVDA"
fx_symbol = "USDKRW=X"
gift_date = "2026-02-02" # 수증일 가정

# 2. 날짜 계산 (수증일 전후 2개월)
base_date = datetime.strptime(gift_date, "%Y-%m-%d")
start_date = (base_date - timedelta(days=65)).strftime("%Y-%m-%d")
end_date = (base_date + timedelta(days=65)).strftime("%Y-%m-%d")

# 3. 데이터 다운로드 (구조를 단순화하기 위해 .Close 사용)
# 뒤에 .iloc[:, 0] 등을 붙여서 2중 컬럼 구조를 깨뜨려줍니다.
print(f"{ticker_symbol} 및 환율 데이터를 가져오는 중...")
stock_data = yf.download(ticker_symbol, start=start_date, end=end_date)['Close']
fx_data = yf.download(fx_symbol, start=start_date, end=end_date)['Close']

# 4. 데이터 통합 및 전처리
# 종목 데이터와 환율 데이터를 하나로 합칩니다.
df = pd.DataFrame({
    'Stock_Price': stock_data.iloc[:, 0] if isinstance(stock_data, pd.DataFrame) else stock_data,
    'FX_Rate': fx_data.iloc[:, 0] if isinstance(fx_data, pd.DataFrame) else fx_data
})

# 중요: 모든 날짜를 생성해서 비어있는 주말/휴일 데이터를 채웁니다 (세법 적용)
all_days = pd.date_range(start=start_date, end=end_date)
df = df.reindex(all_days)
df = df.ffill() # 앞의 데이터로 채우기 (Forward Fill)

# 5. 원화 환산 및 평균 계산
df['KRW_Value'] = df['Stock_Price'] * df['FX_Rate']
final_average = df['KRW_Value'].mean()

print("\n" + "="*30)
print(f"[{ticker_symbol} 증여세 신고용 기준가액]")
print(f"평균 시세: {final_average:,.2f} 원")
print("="*30)

# 결과 확인용 (상위 10개 행)
print("\n[상세 내역 샘플]")
print(df.head(10))