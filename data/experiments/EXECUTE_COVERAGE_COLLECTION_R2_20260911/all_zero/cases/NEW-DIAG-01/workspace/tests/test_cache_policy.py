from cache_policy import is_fresh

def test_before_expiry():
    assert is_fresh(100, 109, 10) is True

def test_after_expiry():
    assert is_fresh(100, 111, 10) is False

def test_exact_expiry():
    assert is_fresh(100, 110, 10) is False

def test_invalid_clock():
    try:
        is_fresh(100, 99, 10)
    except ValueError:
        return
    assert False, "backward clock must be rejected"
