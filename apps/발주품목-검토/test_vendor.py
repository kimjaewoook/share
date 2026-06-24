import pandas as pd
from src.data_mapper import process_procurement_data

data_dict = process_procurement_data()
price_df = data_dict["price_df"]
inv_df = data_dict["inv_df"]

for mc in ["3HGR0002", "3HGR0003", "3HGR0004"]:
    pr = price_df[price_df["자재코드(물류)"] == mc]
    if "유효여부" in price_df.columns:
        pr = pr[pr["유효여부"].astype(str).str.strip().str.upper() == "O"]
    if not pr.empty:
        pi = pr.index[0]
        vendor = pr.at[pi, "공급업체명(약식)"]
        print(f"{mc} vendor: '{vendor}'")
