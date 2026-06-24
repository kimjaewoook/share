import pandas as pd
from datetime import datetime, timedelta

def clean_number(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0.0
    try: return float(str(val).replace(",", ""))
    except: return 0.0

def generate_procurement_plan(data_dict):
    trigger_a_df = data_dict.get("trigger_a_df", pd.DataFrame())
    trigger_b_df = data_dict.get("trigger_b_df", pd.DataFrame())
    inv_df = data_dict.get("inv_df", pd.DataFrame())
    vendor_df = data_dict.get("vendor_df", pd.DataFrame())
    price_df = data_dict.get("price_df", pd.DataFrame())

    plans = []
    processed_mat_codes = set()
    
    # 1. Process Trigger A (현장 요청)
    if not trigger_a_df.empty:
        for _, row in trigger_a_df.iterrows():
            mat_code = str(row.get("자재코드", "")).strip()
            if not mat_code: continue
            
            # TODO: Add logic here
            pass

    return pd.DataFrame(plans)
