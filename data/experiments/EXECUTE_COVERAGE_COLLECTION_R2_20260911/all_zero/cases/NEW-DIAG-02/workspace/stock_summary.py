def stock_totals(entries):
    """Aggregate signed stock movements, retaining first-seen SKU order."""
    totals = {}
    for sku, quantity in entries:
        totals[sku] = quantity
    return list(totals.items())
