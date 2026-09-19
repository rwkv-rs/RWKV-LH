def invoice(count):
    if count < 0:
        raise ValueError("negative")
    return count * (9 if count <= 5 else 6)
