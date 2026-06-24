import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan
import src.procurement_engine as pe

data_dict = process_procurement_data()

with open("src/procurement_engine.py", "r") as f:
    code = f.read()

code = code.replace(
    'remaining -= (13 * plt_total)',
    'print(f"B: {mc} {remaining} {plt_total}"); remaining -= (13 * plt_total); print(f"A: {mc} {remaining}")'
)
with open("src/procurement_engine.py", "w") as f:
    f.write(code)

plan_df = generate_procurement_plan(data_dict)
