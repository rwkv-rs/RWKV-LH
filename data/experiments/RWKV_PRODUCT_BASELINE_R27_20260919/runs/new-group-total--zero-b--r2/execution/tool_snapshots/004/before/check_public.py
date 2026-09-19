from totals import totals
assert totals([(' oak ', 3), ('oak', -1), ('', 9)]) == {'oak': 2}
assert totals([]) == {}
print("all checks passed")
