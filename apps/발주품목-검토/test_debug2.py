import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan

data_dict = process_procurement_data()

with open("src/procurement_engine.py", "r") as f:
    code = f.read()

code = code.replace(
    'if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:\n            remaining -= (13 * plt_total)',
    'if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:\n            print(f"BEFORE mc={mc} remaining={remaining} plt_total={plt_total}")\n            remaining -= (13 * plt_total)\n            print(f"AFTER remaining={remaining}")'
)
with open("src/procurement_engine.py", "w") as f:
    f.write(code)

plan_df = generate_procurement_plan(data_dict)
