with open("src/procurement_engine.py", "r") as f:
    code = f.read()

# Restore original remaining calculation
code = code.replace(
    'if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:\n            remaining -= (13 * plt_total)',
    ''
)

# Introduce effective_remaining
old_calc = "po_qty = (req_qty + lt_demand + safety) - remaining - pend"
new_calc = """effective_remaining = remaining
            if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:
                effective_remaining -= (13 * plt_total)
            po_qty = (req_qty + lt_demand + safety) - effective_remaining - pend"""

code = code.replace(old_calc, new_calc)

with open("src/procurement_engine.py", "w") as f:
    f.write(code)

print("Fixed!")
