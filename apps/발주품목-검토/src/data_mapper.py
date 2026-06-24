import pandas as pd
import numpy as np
import warnings
from src.google_sheets import get_sheet_data
from config.settings import MASTER_PO_SPREADSHEET_ID, SHEET_RANGES

# 시트별 헤더 인덱스 (0-based)
HEADER_INDEX_META = {
    "자재요청서": 1,
    "단가테이블": 1,
    "재고현황": 6,
    "공급업체": 2,
    "PO_LIST": 4,
    "자재코드": 1,
    "예상시점": 2,
}

def load_and_clean_sheet(spreadsheet_id, range_name, header_index):
    """지정된 헤더 인덱스에 따라 데이터를 로드하고 규격화 및 정제하는 단일 범용 함수"""
    values = get_sheet_data(spreadsheet_id, range_name)
    if not values or len(values) <= header_index:
        return pd.DataFrame()
    
    headers = values[header_index]
    data = values[header_index + 1:]
    
    max_cols = len(headers)
    cleaned_data = []
    for row in data:
        if len(row) < max_cols:
            row = row + [''] * (max_cols - len(row))
        elif len(row) > max_cols:
            row = row[:max_cols]
        cleaned_data.append(row)
        
    df = pd.DataFrame(cleaned_data, columns=headers)
    
    # 중복 헤더 이름 방지
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        if str(dup).strip() == "": continue
        cols[cols[cols == dup].index.values.tolist()] = [f"{dup}_{i}" if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols    
    
    # '자재코드' 열 정제
    for col in df.columns:
        if "자재코드" in str(col):
            df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)
            
    return df

def process_procurement_data():
    """타겟 시트를 로드하고 Dictionary로 반환"""
    
    req_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["자재요청서"], HEADER_INDEX_META["자재요청서"])
    price_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["단가테이블"], HEADER_INDEX_META["단가테이블"])
    inv_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["재고현황"], HEADER_INDEX_META["재고현황"])
    vendor_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["공급업체"], HEADER_INDEX_META["공급업체"])
    mat_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["자재코드"], HEADER_INDEX_META["자재코드"])
    forecast_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["예상시점"], HEADER_INDEX_META["예상시점"])
    po_df = load_and_clean_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["PO_LIST"], HEADER_INDEX_META["PO_LIST"])
    
    # full_req_df: 불출 완료 건 포함 전체 자재요청서 (30/60/90일 평균 산출용)
    full_req_df = req_df.copy() if not req_df.empty else pd.DataFrame()
    if not full_req_df.empty and '자재코드' in full_req_df.columns:
        full_req_df = full_req_df.dropna(subset=['자재코드'])
    
    # Trigger A: 불출 여부가 빈칸인 현장 요청만
    trigger_a_df = pd.DataFrame()
    if not req_df.empty:
        if '불출 여부' in req_df.columns:
            req_df['불출 여부'] = req_df['불출 여부'].astype(str).str.strip().replace(['nan', 'None'], '')
            trigger_a_df = req_df[req_df['불출 여부'] == '']
            if '자재코드' in trigger_a_df.columns:
                trigger_a_df = trigger_a_df.dropna(subset=['자재코드'])
        else:
            trigger_a_df = req_df
    
    # Trigger B: 재고소진 모니터링 대상 'O'
    trigger_b_df = pd.DataFrame()
    if not mat_df.empty:
        mon_col = [c for c in mat_df.columns if "재고소진" in str(c) and "모니터링" in str(c)]
        if mon_col:
            trigger_b_df = mat_df[mat_df[mon_col[0]].astype(str).str.strip().str.upper() == 'O']

    return {
        "trigger_a_df": trigger_a_df,
        "trigger_b_df": trigger_b_df,
        "full_req_df": full_req_df,
        "price_df": price_df,
        "inv_df": inv_df,
        "vendor_df": vendor_df,
        "forecast_df": forecast_df,
        "po_df": po_df,
    }

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    data_dict = process_procurement_data()
    print(f"Trigger A (현장요청): {len(data_dict['trigger_a_df'])}건")
    print(f"Trigger B (모니터링대상): {len(data_dict['trigger_b_df'])}건")
    print(f"Full 자재요청서: {len(data_dict['full_req_df'])}건")
    print(f"PO List: {len(data_dict['po_df'])}건")
    print(f"재고소진예상시점: {len(data_dict['forecast_df'])}건")