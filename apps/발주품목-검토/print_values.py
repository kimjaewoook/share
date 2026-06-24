import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import clean_number

data_dict = process_procurement_data()
price_df = data_dict["price_df"]

for mc in ["3HGR0003", "3HGR0004"]:
    pr = price_df[price_df["자재코드(물류)"] == mc]
    if not pr.empty:
        pi = pr.index[0]
        box_qty = clean_number(pr.at[pi, "박스입수량"])
        plt_boxes = clean_number(pr.at[pi, "PLT당 적재 박스수"])
        plt_total = box_qty * plt_boxes
        print(f"{mc}: box_qty={box_qty}, plt_boxes={plt_boxes}, plt_total={plt_total}")
