import re


_NON_CONTENT = re.compile(r"[^0-9a-zA-Z\u3400-\u4dbf\u4e00-\u9fff]+")


def is_repetitive_garbage(text: str) -> bool:
    """Detect long, near-periodic parser garbage without rejecting normal prose."""

    lines = [_NON_CONTENT.sub("", line) for line in text.splitlines()]
    candidate = max(lines, key=len, default="")
    if len(candidate) < 80:
        return False
    max_period = min(32, len(candidate) // 5)
    for period in range(2, max_period + 1):
        unit = candidate[:period]
        repetitions = len(candidate) // period
        repeated_length = repetitions * period
        if repetitions < 5 or repeated_length / len(candidate) < 0.9:
            continue
        repeated = unit * repetitions
        mismatches = sum(
            left != right
            for left, right in zip(candidate[:repeated_length], repeated)
        )
        if mismatches / repeated_length <= 0.03:
            return True
    return False
