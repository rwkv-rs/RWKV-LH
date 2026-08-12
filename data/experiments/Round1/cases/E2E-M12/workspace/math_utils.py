def safe_divide(a, b):
    if b == 0:
        raise ValueError("Division by zero")
    return a / b


def median(values):
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 1:
        return sorted_values[n // 2]
    else:
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
