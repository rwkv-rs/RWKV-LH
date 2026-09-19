from flags import enabled
assert enabled('true') == True
assert enabled('false') == False
assert enabled(' NO ') == False
print("all checks passed")
