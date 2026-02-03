import yfinance as yf
from datetime import datetime, timedelta

# 1. 설정 (테스트용: 엔비디아)
ticker_symbol = "NVDA" 
gift_date = "2024-01-15" # 수증일 가정

# 2. 날짜 계산 (수증일 전후 2개월)
base_date = datetime.strptime(gift_date, "%Y-%m-%d")
start_date = (base_date - timedelta(days=65)).strftime("%Y-%m-%d")
end_date = (base_date + timedelta(days=65)).strftime("%Y-%m-%d")

# 3. 데이터 불러오기
print(f"{ticker_symbol} 데이터를 {start_date}부터 {end_date}까지 불러옵니다...")
df = yf.download(ticker_symbol, start=start_date, end=end_date)

# 4. 결과 확인
if not df.empty:
    print("\n--- 데이터 가져오기 성공! ---")
    print(df.head()) # 앞부분 5줄 출력
else:
    print("\n--- 데이터를 가져오지 못했습니다. Ticker나 날짜를 확인하세요. ---")