remaining = 10140.0
plt_total = 2880.0
mc = "3HGR0004"
vendor_name = "에버원"

print("Before:", remaining)
if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:
    remaining -= (13 * plt_total)
print("After:", remaining)
