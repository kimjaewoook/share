import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan
import src.procurement_engine as pe

data_dict = process_procurement_data()

with open("src/procurement_engine.py", "r") as f:
    code = f.read()

inject_str = """        if mc in ["3HGR0003", "3HGR0004"]:
            print(f"CHECKING mc={mc} vendor_name='{vendor_name}'")
        if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:"""
code = code.replace(
    'if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:',
    inject_str
)
with open("src/procurement_engine.py", "w") as f:
    f.write(code)

plan_df = pe.generate_procurement_plan(data_dict)
