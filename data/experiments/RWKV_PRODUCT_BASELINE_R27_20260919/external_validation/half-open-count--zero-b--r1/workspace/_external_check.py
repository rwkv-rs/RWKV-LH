from ranges import count_inside
assert count_inside(([2, 2, 4, 5], 2, 5)) == 3
assert count_inside(([4], 4, 4)) == 0
assert count_inside(([], 0, 10)) == 0
assert count_inside(([-2, -1, 0, 0, 1], -1, 1)) == 3
try:
    count_inside(([], 2, 1))
except ValueError:
    pass
else:
    raise AssertionError("ValueError required")
print("all checks passed")
