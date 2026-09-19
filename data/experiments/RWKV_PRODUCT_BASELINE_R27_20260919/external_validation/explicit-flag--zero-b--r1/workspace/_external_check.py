from flags import enabled
assert enabled('true') == True
assert enabled('false') == False
assert enabled(' NO ') == False
assert enabled(' YES ') == True
assert enabled('0') == False
assert enabled('1') == True
assert enabled('False') == False
try:
    enabled('unknown')
except ValueError:
    pass
else:
    raise AssertionError("ValueError required")
print("all checks passed")
