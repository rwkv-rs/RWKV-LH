"""RWKV's trie tokenizer, packaged locally for exact context accounting."""

from __future__ import annotations

import ast
from pathlib import Path


class Trie:
    __slots__ = ("character", "children", "values", "parent")

    def __init__(self, parent: "Trie | None" = None, character: int | None = None):
        self.character = character
        self.children: list[Trie | None] = [None] * 256
        self.values: set[tuple[bytes, int]] = set()
        self.parent = parent

    def add(self, key: bytes, index: int = 0, value: tuple[bytes, int] | None = None) -> "Trie":
        if index == len(key):
            if value is None:
                raise ValueError("token trie value is required")
            self.values.add(value)
            return self
        character = key[index]
        child = self.children[character]
        if child is None:
            child = Trie(parent=self, character=character)
            self.children[character] = child
        return child.add(key, index + 1, value)

    def find_longest(self, key: bytes, index: int) -> tuple[int, set[tuple[bytes, int]]]:
        node = self
        best_index = index
        best_values: set[tuple[bytes, int]] | None = None
        while index < len(key):
            child = node.children[key[index]]
            if child is None:
                break
            node = child
            index += 1
            if node.values:
                best_index = index
                best_values = node.values
        if best_values is None:
            raise ValueError(f"vocabulary cannot encode byte at offset {best_index}")
        return best_index, best_values


class RWKVTokenizer:
    """Official RWKV vocabulary semantics with deterministic local loading."""

    def __init__(self, file_name: str | Path | None = None):
        vocab_path = (
            Path(file_name)
            if file_name is not None
            else Path(__file__).resolve().parent / "data" / "rwkv_vocab_v20230424.txt"
        )
        if not vocab_path.is_file():
            raise FileNotFoundError(f"RWKV vocabulary not found: {vocab_path}")

        self.idx2token: dict[int, bytes] = {}
        for line in vocab_path.read_text(encoding="utf-8").splitlines():
            first_space = line.index(" ")
            last_space = line.rindex(" ")
            index = int(line[:first_space])
            token = ast.literal_eval(line[first_space:last_space])
            token = token.encode("utf-8") if isinstance(token, str) else token
            if not isinstance(token, bytes) or len(token) != int(line[last_space:]):
                raise ValueError(f"invalid RWKV vocabulary row: {index}")
            self.idx2token[index] = token

        self.token2idx = {token: index for index, token in self.idx2token.items()}
        self.root = Trie()
        for token, index in self.token2idx.items():
            self.root.add(token, value=(token, index))

    def encode_bytes(self, source: bytes) -> list[int]:
        index = 0
        tokens: list[int] = []
        while index < len(source):
            index, values = self.root.find_longest(source, index)
            _, token_id = next(iter(values))
            tokens.append(token_id)
        return tokens

    def decode_bytes(self, tokens: list[int]) -> bytes:
        return b"".join(self.idx2token[token] for token in tokens)

    def encode(self, source: str) -> list[int]:
        return self.encode_bytes(source.encode("utf-8"))

    def decode(self, tokens: list[int]) -> str:
        return self.decode_bytes(tokens).decode("utf-8", errors="replace")

__all__ = ["RWKVTokenizer", "Trie"]
