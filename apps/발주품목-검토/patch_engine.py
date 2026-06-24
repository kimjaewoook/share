with open("src/procurement_engine.py", "r") as f:
    code = f.read()

# 1. Modify _round_to_unit
old_round = """def _round_to_unit(po_qty, box_qty, plt_total):
    \"\"\"H2: 박스 단위 올림 → 파렛트의 50% 이상이면 파렛트 단위로 올림\"\"\"
    if po_qty <= 0:
        return 0
    # 1차: 박스 단위 올림"""

new_round = """def _round_to_unit(po_qty, box_qty, plt_total, is_everone=False):
    \"\"\"H2: 박스 단위 올림 → 파렛트의 50% 이상이면 파렛트 단위로 올림\"\"\"
    if po_qty <= 0:
        return 0
        
    if is_everone and plt_total > 0:
        po_qty = __import__('math').ceil(po_qty / plt_total) * plt_total
        if (po_qty / plt_total) % 2 != 0:
            po_qty += plt_total
        return po_qty
        
    # 1차: 박스 단위 올림"""
code = code.replace(old_round, new_round)

# 2. Modify generate_procurement_plan
old_remaining = """        if not ir.empty:
            ii = ir.index[0]
            a8w = clean_number(ir.at[ii,"1일 평균\\n(최근 8주)"])
            remaining = clean_number(ir.at[ii,"잔여재고 수량"]) if "잔여재고 수량" in inv_df.columns else clean_number(ir.at[ii,"가용재고(낱개)"])

        sa_data = seasonal_avgs.get(mc, {})"""

new_remaining = """        if not ir.empty:
            ii = ir.index[0]
            a8w = clean_number(ir.at[ii,"1일 평균\\n(최근 8주)"])
            remaining = clean_number(ir.at[ii,"잔여재고 수량"]) if "잔여재고 수량" in inv_df.columns else clean_number(ir.at[ii,"가용재고(낱개)"])

        if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:
            remaining -= (13 * plt_total)

        sa_data = seasonal_avgs.get(mc, {})"""
code = code.replace(old_remaining, new_remaining)

# 3. Modify po_qty call
old_call = """                po_qty = _round_to_unit(po_qty, box_qty, plt_total)
                plan["vendor_po_qty"] = po_qty"""

new_call = """                po_qty = _round_to_unit(po_qty, box_qty, plt_total, is_everone=("에버원" in vendor_name))
                plan["vendor_po_qty"] = po_qty"""
code = code.replace(old_call, new_call)

with open("src/procurement_engine.py", "w") as f:
    f.write(code)

print("Patch successful.")
