import pandas as pd
from src.data_mapper import process_procurement_data

data_dict = process_procurement_data()
price_df = data_dict["price_df"]

for mc in ["3HGR0003", "3HGR0004"]:
    pr = price_df[price_df["자재코드(물류)"] == mc]
    if not pr.empty:
        pi = pr.index[0]
        print(f"MC: {mc}, plt_boxes: {pr.at[pi, 'PLT당 적재 박스수']}")
