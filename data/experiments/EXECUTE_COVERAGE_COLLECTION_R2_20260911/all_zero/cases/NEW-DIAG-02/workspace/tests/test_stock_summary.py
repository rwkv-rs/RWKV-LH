from stock_summary import stock_totals

def test_empty():
    assert stock_totals([]) == []

def test_single_movement():
    assert stock_totals([("bolt", 4)]) == [("bolt", 4)]

def test_distinct_skus_keep_order():
    assert stock_totals([("nut", 2), ("bolt", 3)]) == [("nut", 2), ("bolt", 3)]

def test_repeated_sku_accumulates():
    assert stock_totals([("bolt", 5), ("nut", 2), ("bolt", -1)]) == [("bolt", 4), ("nut", 2)]
