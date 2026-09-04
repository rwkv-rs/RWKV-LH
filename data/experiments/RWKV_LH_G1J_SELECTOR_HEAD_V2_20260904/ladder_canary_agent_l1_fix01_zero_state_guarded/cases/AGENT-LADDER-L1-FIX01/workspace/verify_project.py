from __future__ import annotations

import math
from pathlib import Path

from pricing import final_price


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    cases = [
        ((100, 15), 85.0),
        ((19.99, 25), 14.99),
        ((8.335, 0), 8.34),
        ((10, 100), 0.0),
    ]
    for arguments, expected in cases:
        actual = final_price(*arguments)
        require(isinstance(actual, float), "final_price must return float")
        require(math.isclose(actual, expected, abs_tol=1e-9), f"{arguments}: {actual}")
    for arguments in [(-1, 5), (10, -1), (10, 101), (True, 10), (10, False)]:
        try:
            final_price(*arguments)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"invalid input accepted: {arguments}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("python verify_project.py" in readme, "README verification command missing")
    require("discount" in readme.casefold(), "README behavior missing")
    print("AGENT-LADDER-L1-FIX01 verified")


if __name__ == "__main__":
    main()
