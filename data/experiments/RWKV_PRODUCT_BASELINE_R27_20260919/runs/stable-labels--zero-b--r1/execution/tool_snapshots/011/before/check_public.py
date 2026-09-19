from labels import unique_labels
assert unique_labels([' Beta ', 'Alpha', 'Beta', '']) == ['Beta', 'Alpha']
assert unique_labels(['oak', 'Oak']) == ['oak', 'Oak']
print("all checks passed")
