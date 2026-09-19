def count_inside(args):
    values, low, high = args
    return len({v for v in values if low <= v <= high})
