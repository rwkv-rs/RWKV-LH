from typing import List, Tuple, Dict

def totals(rows: List[Tuple[str, int]]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for name, amount in rows:
        name = name.strip()
        if name:
            result[name] = result.get(name, 0) + amount
    return result
