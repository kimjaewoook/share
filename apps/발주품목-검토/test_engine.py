import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan

data_dict = process_procurement_data()
plan_df = generate_procurement_plan(data_dict)

for _, row in plan_df[plan_df["mat_code"].isin(["3HGR0002", "3HGR0003", "3HGR0004"])].iterrows():
    print(f"MC: {row['mat_code']}, vendor: {row['vendor']}, remaining_stock: {row['remaining_stock']}, vendor_po_qty: {row['vendor_po_qty']}")
