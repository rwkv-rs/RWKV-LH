"""CPU RWKV byte tokenization and target-only teacher forcing; no model import."""

import ast
from pathlib import Path


class Vocabulary:
    def __init__(self, path: Path):
        self.by_id, self.trie = {}, {}
        for line in path.read_text(encoding="utf-8").splitlines():
            token_id, rest = line.split(" ", 1)
            literal, size = rest.rsplit(" ", 1)
            token = ast.literal_eval(literal)
            token = token.encode("utf-8") if isinstance(token, str) else token
            index = int(token_id)
            if (not isinstance(token, bytes) or not token or len(token) != int(size)
                    or index <= 0 or index in self.by_id):
                raise ValueError("invalid RWKV vocabulary entry")
            self.by_id[index] = token
            node = self.trie
            for byte in token:
                node = node.setdefault(byte, {})
            node[None] = index

    def encode(self, text: str) -> list[int]:
        raw, start, result = text.encode("utf-8"), 0, []
        while start < len(raw):
            node, cursor, best = self.trie, start, None
            while cursor < len(raw) and raw[cursor] in node:
                node = node[raw[cursor]]
                cursor += 1
                if None in node:
                    best = cursor, node[None]
            if best is None:
                raise ValueError("vocabulary cannot encode input byte")
            start, index = best
            result.append(index)
        if b"".join(self.by_id[index] for index in result) != raw:
            raise ValueError("tokenization changed input bytes")
        return result


def encode_training(prompt: str, target: str, vocab: Vocabulary, max_tokens: int) -> dict:
    if not prompt or not target:
        raise ValueError("empty prompt or target")
    # Separate encoding preserves the inference-time prompt/answer boundary.
    prompt_ids, answer_ids = vocab.encode(prompt), vocab.encode(target)
    ids = prompt_ids + answer_ids + [0]
    if len(ids) > max_tokens:
        raise ValueError(f"sequence has {len(ids)} tokens, limit {max_tokens}; never truncate")
    return {"input_ids": ids, "labels": [-100] * len(prompt_ids) + answer_ids + [0],
            "prompt_tokens": len(prompt_ids), "target_tokens_with_eos": len(answer_ids) + 1}
