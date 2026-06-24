import sys
sys.path.append('/Users/kimjaewoook/ai/laundrygo/apps/발주품목검토')
from src.data_mapper import process_procurement_data

data = process_procurement_data()
print("INV COLUMNS:")
print(data['inv_df'].columns.tolist())
print("PRICE COLUMNS:")
print(data['price_df'].columns.tolist())
