import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan
import src.procurement_engine as pe

data_dict = process_procurement_data()

original_round = pe._round_to_unit
def _debug_round(*args, **kwargs):
    return original_round(*args, **kwargs)
pe._round_to_unit = _debug_round

def hook_plan(data_dict):
    # I will modify procurement_engine inside
    pass

# Read the file and inject a print
with open("src/procurement_engine.py", "r") as f:
    code = f.read()
code = code.replace(
    'if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:',
    'if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:\n            print(f"Condition True! mc={mc}, vendor={vendor_name}, plt_total={plt_total}")'
)
with open("src/procurement_engine.py", "w") as f:
    f.write(code)

plan_df = pe.generate_procurement_plan(data_dict)
