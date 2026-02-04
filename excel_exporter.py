import pandas as pd
import io

def generate_excel_report(res_list, summary, is_incomplete_any, report_date):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. 전체 요약 시트
        summary_rows = []
        for r in res_list:
            summary_rows.append({
                '항목(종목)': r['ticker'], 
                '내역(수량/내용)': f"{r['count']:,}", 
                '평균가액(1주)': f"{r['avg_val']:,.0f}", 
                '소계(원화)': f"{r['item_total']:,.0f}"
            })
            
        summary_rows.append({'항목(종목)': '', '내역(수량/내용)': '', '평균가액(1주)': '', '소계(원화)': ''})
        
        status_note = "확정 데이터" if not is_incomplete_any else f"임시 데이터 (확정 가능일: {report_date})"
        summary_rows.append({'항목(종목)': '데이터 출처', '내역(수량/내용)': "Yahoo Finance (yfinance API)"})
        summary_rows.append({'항목(종목)': '산출 기준', '내역(수량/내용)': "상증세법상 수증일 전후 2개월 종가 평균"})
        summary_rows.append({'항목(종목)': '휴장일 처리', '내역(수량/내용)': "주가/환율 미공표일(휴장일 등)은 계산에서 제외"})
        summary_rows.append({'항목(종목)': '데이터 확정 여부', '내역(수량/내용)': status_note})
        summary_rows.append({'항목(종목)': '총 증여가액 합계', '내역(수량/내용)': f"{summary['total_amt']:,.0f} 원"})
        summary_rows.append({'항목(종목)': '예상 납부세액', '내역(수량/내용)': f"{summary['tax']:,.0f} 원"})

        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='전체요약', index=False)
        
        # 2. 종목별 상세 시트
        for r in res_list:
            df_export = r['df'].copy()
            
            # [추가] 컬럼명 한글 변환 매핑
            column_mapping = {
                'Stock_Price': '주가(현지통화)',
                'FX_Rate': '적용환율',
                'KRW_Value': '원화 환산가액'
            }
            df_export = df_export.rename(columns=column_mapping)
            
            # 인덱스 설정 및 날짜 포맷팅
            df_export.index.name = '일자'
            df_export = df_export.reset_index()
            
            if pd.api.types.is_datetime64_any_dtype(df_export['일자']):
                df_export['일자'] = df_export['일자'].dt.strftime('%Y-%m-%d')
                
            df_export.to_excel(writer, sheet_name=f"{r['ticker']}_상세", index=False)

        # 3. 컬럼 폭 조절
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if cell.value:
                            val_str = str(cell.value)
                            length = sum(2 if ord(char) > 128 else 1 for char in val_str)
                            max_length = max(max_length, length)
                    except: pass
                worksheet.column_dimensions[column].width = max_length + 2
                
    return output.getvalue()