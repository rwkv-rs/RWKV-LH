import hashlib
import math
import re
from collections import Counter
from collections.abc import Callable

SparseBatch = tuple[list[list[int]], list[list[float]]]

_WORD_PATTERN = re.compile(r"[a-zA-Z0-9]+")


def chinese_tokens(text: str) -> list[str]:
    lowered = text.lower()
    han_runs: list[list[str]] = []
    current: list[str] = []
    tokens = _WORD_PATTERN.findall(lowered)
    for character in lowered:
        if "\u4e00" <= character <= "\u9fff":
            current.append(character)
        elif current:
            han_runs.append(current)
            current = []
    if current:
        han_runs.append(current)
    for run in han_runs:
        tokens.extend(run)
        tokens.extend("".join(run[index : index + 2]) for index in range(len(run) - 1))
    return tokens


def token_index(token: str) -> int:
    digest = hashlib.blake2s(token.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big", signed=False)


def encode_sparse_texts(texts: list[str]) -> SparseBatch:
    all_indices: list[list[int]] = []
    all_values: list[list[float]] = []
    for text in texts:
        counts = Counter(chinese_tokens(text))
        weighted = sorted(
            (token_index(token), 1.0 + math.log(min(count, 8))) for token, count in counts.items()
        )
        all_indices.append([index for index, _ in weighted])
        all_values.append([value for _, value in weighted])
    return all_indices, all_values


def sparse_encoder() -> Callable[[list[str]], SparseBatch]:
    return encode_sparse_texts
