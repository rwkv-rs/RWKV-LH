def unique_labels(values):
    return sorted(set(v.strip().lower() for v in values if v.strip()))
