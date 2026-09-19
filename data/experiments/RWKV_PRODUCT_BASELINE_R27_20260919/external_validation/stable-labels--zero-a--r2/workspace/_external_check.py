from labels import unique_labels
assert unique_labels([' Beta ', 'Alpha', 'Beta', '']) == ['Beta', 'Alpha']
assert unique_labels(['oak', 'Oak']) == ['oak', 'Oak']
assert unique_labels([]) == []
assert unique_labels([' z ', 'a', 'z', 'A']) == ['z', 'a', 'A']
assert unique_labels([' a b ', 'a b', 'ab']) == ['a b', 'ab']
print("all checks passed")
