def stock_totals(entries):
    """Aggregate signed stock movements, retaining first-seen SKU order."""
    totals = {}
    for sku, quantity in entries:
        totals[sku] = totals.get(sku, 0) + quantity
    return list(totals.items())
