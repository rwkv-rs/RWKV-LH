from totals import totals
assert totals([(' oak ', 3), ('oak', -1), ('', 9)]) == {'oak': 2}
assert totals([]) == {}
assert totals([('A', 1), ('a', 2), ('A', 3)]) == {'A': 4, 'a': 2}
assert totals([(' x y ', 7)]) == {'x y': 7}
print("all checks passed")
