from price import invoice
assert invoice(0) == 0
assert invoice(5) == 45
assert invoice(6) == 51
assert invoice(1) == 9
assert invoice(4) == 36
assert invoice(7) == 57
assert invoice(10) == 75
try:
    invoice(-1)
except ValueError:
    pass
else:
    raise AssertionError("ValueError required")
print("all checks passed")
