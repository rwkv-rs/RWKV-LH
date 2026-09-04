from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def final_price(price: int | float, discount_percent: int | float) -> float:
    """Return a currency amount rounded with ROUND_HALF_UP."""

    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise TypeError("price must be numeric")
    if isinstance(discount_percent, bool) or not isinstance(discount_percent, (int, float)):
        raise TypeError("discount_percent must be numeric")
    if price < 0:
        raise ValueError("price must be non-negative")
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    # BUG: the percentage scale is wrong and binary float enters the Decimal path.
    multiplier = Decimal("1") - Decimal(str(discount_percent / 10))
    amount = Decimal(str(price)) * multiplier
    return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
