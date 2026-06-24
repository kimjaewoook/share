with open("src/procurement_engine.py", "r") as f:
    code = f.read()

# Fix _round_to_unit (ensure it's there)
if 'is_everone' not in code[:1000]:
    old_round = """def _round_to_unit(po_qty, box_qty, plt_total):
    \"\"\"H2: 박스 단위 올림 → 파렛트의 50% 이상이면 파렛트 단위로 올림\"\"\"
    if po_qty <= 0:
        return 0"""
    new_round = """def _round_to_unit(po_qty, box_qty, plt_total, is_everone=False):
    \"\"\"H2: 박스 단위 올림 → 파렛트의 50% 이상이면 파렛트 단위로 올림\"\"\"
    if po_qty <= 0:
        return 0
        
    if is_everone and plt_total > 0:
        import math
        po_qty = math.ceil(po_qty / plt_total) * plt_total
        if (po_qty / plt_total) % 2 != 0:
            po_qty += plt_total
        return po_qty"""
    code = code.replace(old_round, new_round)

# Fix the call
if 'is_everone=' not in code:
    code = code.replace(
        "po_qty = _round_to_unit(po_qty, box_qty, plt_total)",
        "po_qty = _round_to_unit(po_qty, box_qty, plt_total, is_everone=(\"에버원\" in vendor_name))"
    )

with open("src/procurement_engine.py", "w") as f:
    f.write(code)
