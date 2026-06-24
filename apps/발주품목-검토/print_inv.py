import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import clean_number

data_dict = process_procurement_data()
inv_df = data_dict["inv_df"]

for mc in ["3HGR0003", "3HGR0004"]:
    ir = inv_df[inv_df["자재코드(물류)"] == mc]
    if not ir.empty:
        ii = ir.index[0]
        remaining = clean_number(ir.at[ii,"잔여재고 수량"]) if "잔여재고 수량" in inv_df.columns else clean_number(ir.at[ii,"가용재고(낱개)"])
        print(f"{mc}: original remaining={remaining}")
