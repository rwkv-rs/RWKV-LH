from typing import List, Tuple, Dict

def totals(rows: List[Tuple[str, int]]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for name, amount in rows:
        if not isinstance(name, str):
            continue
        stripped = name.strip()
        if not stripped:
            continue
        result[stripped] = result.get(stripped, 0) + amount
    return result
