import pandas as pd
from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan
import src.procurement_engine as pe

data_dict = process_procurement_data()

# Monkey patch to see what's happening
original_round = pe._round_to_unit
def _debug_round(*args, **kwargs):
    print(f"DEBUG round called with: {args}, {kwargs}")
    return original_round(*args, **kwargs)
pe._round_to_unit = _debug_round

plan_df = pe.generate_procurement_plan(data_dict)
