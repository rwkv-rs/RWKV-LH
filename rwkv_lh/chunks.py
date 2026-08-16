"""Tokenizer-sized source chunks, exact coverage, and deterministic reduction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import canonical_digest, canonical_json
from rwkv_lh.schema import ChunkDescriptor
from rwkv_lh.token_budget import get_token_count


class ChunkingError(ValueError):
    pass


@dataclass(frozen=True)
class LaneTokenBudget:
    max_model_tokens: int
    bos_tokens: int
    safety_tokens: int
    max_output_tokens: int
    fixed_prefix_tokens: int
    event_metadata_tokens: int
    boundary_carry_tokens: int

    @property
    def input_budget(self) -> int:
        return (
            self.max_model_tokens
            - self.bos_tokens
            - self.safety_tokens
            - self.max_output_tokens
        )

    @property
    def raw_chunk_budget(self) -> int:
        return (
            self.input_budget
            - self.fixed_prefix_tokens
            - self.event_metadata_tokens
            - self.boundary_carry_tokens
        )

    def validate(self) -> None:
        if self.raw_chunk_budget < 1:
            raise ChunkingError(
                "lane metadata and output reserve leave no raw chunk token budget"
            )


@dataclass(frozen=True)
class ChunkSlice:
    descriptor: ChunkDescriptor
    text: str
    core_text: str


def slice_text_from_byte_cursor(
    source_ref: str,
    text: str,
    *,
    start_byte: int,
    max_tokens: int,
    media_type: str = "text/plain",
    split_strategy_version: str = "rwkv-token-cursor.v1",
) -> ChunkSlice:
    """Return one exact UTF-8/token-bounded slice from a byte cursor.

    The cursor is defined against the immutable source bytes. It must land on a
    UTF-8 boundary, and the returned ``core_end`` is the only valid lossless
    continuation cursor. No character-count approximation is involved.
    """

    source = str(text)
    source_bytes = source.encode("utf-8")
    cursor = int(start_byte)
    if not source_ref.strip():
        raise ChunkingError("source_ref must be non-empty")
    if cursor < 0 or cursor > len(source_bytes):
        raise ChunkingError("start_byte is outside the source")
    if max_tokens < 1:
        raise ChunkingError("max_tokens must be positive")
    try:
        prefix = source_bytes[:cursor].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ChunkingError("start_byte is not a UTF-8 boundary") from exc
    source_digest = _sha256_bytes(source_bytes)
    if not source_bytes and cursor == 0:
        descriptor = ChunkDescriptor(
            chunk_id=(
                "CH-CURSOR-"
                + hashlib.sha256(f"{source_digest}:0:0:{max_tokens}".encode()).hexdigest()[:16]
            ),
            source_ref=source_ref,
            source_sha256=source_digest,
            media_type=media_type,
            byte_start=0,
            byte_end=0,
            core_start=0,
            core_end=0,
            overlap_before=0,
            overlap_after=0,
            chunk_sha256=source_digest,
            split_strategy_version=split_strategy_version,
            complete_source=True,
            token_start=0,
            token_end=0,
        )
        return ChunkSlice(descriptor, "", "")
    if cursor == len(source_bytes):
        token_end = get_token_count(source)
        empty_digest = _sha256_bytes(b"")
        descriptor = ChunkDescriptor(
            chunk_id=(
                "CH-CURSOR-"
                + hashlib.sha256(
                    f"{source_digest}:{cursor}:{cursor}:{max_tokens}".encode()
                ).hexdigest()[:16]
            ),
            source_ref=source_ref,
            source_sha256=source_digest,
            media_type=media_type,
            byte_start=cursor,
            byte_end=cursor,
            core_start=cursor,
            core_end=cursor,
            overlap_before=0,
            overlap_after=0,
            chunk_sha256=empty_digest,
            split_strategy_version=split_strategy_version,
            complete_source=False,
            token_start=token_end,
            token_end=token_end,
        )
        return ChunkSlice(descriptor, "", "")
    char_start = len(prefix)
    char_end = _largest_end_for_tokens(source, char_start, int(max_tokens))
    end_byte = len(source[:char_end].encode("utf-8"))
    chunk_bytes = source_bytes[cursor:end_byte]
    chunk_id = (
        "CH-CURSOR-"
        + hashlib.sha256(
            f"{source_digest}:{cursor}:{end_byte}:{max_tokens}".encode()
        ).hexdigest()[:16]
    )
    descriptor = ChunkDescriptor(
        chunk_id=chunk_id,
        source_ref=source_ref,
        source_sha256=source_digest,
        media_type=media_type,
        byte_start=cursor,
        byte_end=end_byte,
        core_start=cursor,
        core_end=end_byte,
        overlap_before=0,
        overlap_after=0,
        chunk_sha256=_sha256_bytes(chunk_bytes),
        split_strategy_version=split_strategy_version,
        complete_source=cursor == 0 and end_byte == len(source_bytes),
        token_start=get_token_count(prefix),
        token_end=get_token_count(source[:char_end]),
    )
    chunk_text = source[char_start:char_end]
    return ChunkSlice(descriptor, chunk_text, chunk_text)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _largest_end_for_tokens(text: str, start: int, budget: int) -> int:
    low = start + 1
    high = len(text)
    best = start
    while low <= high:
        middle = (low + high) // 2
        tokens = get_token_count(text[start:middle])
        if tokens <= budget:
            best = middle
            low = middle + 1
        else:
            high = middle - 1
    if best == start:
        raise ChunkingError("one source character exceeds the raw chunk budget")
    return best


def _boundary_left(text: str, start: int, token_budget: int) -> int:
    if token_budget <= 0 or start <= 0:
        return start
    low = 0
    high = start
    best = start
    while low <= high:
        middle = (low + high) // 2
        if get_token_count(text[middle:start]) <= token_budget:
            best = middle
            high = middle - 1
        else:
            low = middle + 1
    return best


def _boundary_right(text: str, end: int, token_budget: int) -> int:
    if token_budget <= 0 or end >= len(text):
        return end
    return _largest_end_for_tokens(text, end, token_budget)


def split_text_source(
    source_ref: str,
    text: str,
    *,
    raw_chunk_tokens: int,
    overlap_tokens: int = 0,
    media_type: str = "text/plain",
    split_strategy_version: str = "rwkv-token-text.v1",
) -> list[ChunkSlice]:
    """Split UTF-8 text by real tokenizer capacity and exact byte core ranges."""

    source = str(text)
    if not source_ref.strip():
        raise ChunkingError("source_ref must be non-empty")
    if raw_chunk_tokens < 1 or overlap_tokens < 0:
        raise ChunkingError("chunk and overlap token budgets must be valid")
    source_bytes = source.encode("utf-8")
    source_digest = _sha256_bytes(source_bytes)
    if not source:
        return []
    core_char_ranges: list[tuple[int, int]] = []
    start = 0
    while start < len(source):
        end = _largest_end_for_tokens(source, start, raw_chunk_tokens)
        core_char_ranges.append((start, end))
        start = end

    pending: list[tuple[ChunkDescriptor, str, str]] = []
    for index, (core_char_start, core_char_end) in enumerate(core_char_ranges):
        char_start = _boundary_left(source, core_char_start, overlap_tokens)
        char_end = _boundary_right(source, core_char_end, overlap_tokens)
        byte_start = len(source[:char_start].encode("utf-8"))
        core_start = len(source[:core_char_start].encode("utf-8"))
        core_end = len(source[:core_char_end].encode("utf-8"))
        byte_end = len(source[:char_end].encode("utf-8"))
        chunk_bytes = source_bytes[byte_start:byte_end]
        chunk_id = (
            f"CH-{index + 1:06d}-"
            f"{hashlib.sha256(f'{source_digest}:{core_start}:{core_end}'.encode()).hexdigest()[:12]}"
        )
        descriptor = ChunkDescriptor(
            chunk_id=chunk_id,
            source_ref=source_ref,
            source_sha256=source_digest,
            media_type=media_type,
            byte_start=byte_start,
            byte_end=byte_end,
            core_start=core_start,
            core_end=core_end,
            overlap_before=core_start - byte_start,
            overlap_after=byte_end - core_end,
            chunk_sha256=_sha256_bytes(chunk_bytes),
            split_strategy_version=split_strategy_version,
            previous_chunk_id=None,
            next_chunk_id=None,
            complete_source=len(core_char_ranges) == 1,
            token_start=get_token_count(source[:core_char_start]),
            token_end=get_token_count(source[:core_char_end]),
        )
        pending.append(
            (
                descriptor,
                source[char_start:char_end],
                source[core_char_start:core_char_end],
            )
        )

    output: list[ChunkSlice] = []
    for index, (descriptor, chunk_text, core_text) in enumerate(pending):
        linked = ChunkDescriptor(
            **{
                **descriptor.to_dict(),
                "previous_chunk_id": (
                    pending[index - 1][0].chunk_id if index > 0 else None
                ),
                "next_chunk_id": (
                    pending[index + 1][0].chunk_id
                    if index + 1 < len(pending)
                    else None
                ),
            }
        )
        output.append(ChunkSlice(linked, chunk_text, core_text))
    verify_exact_coverage([item.descriptor for item in output], len(source_bytes))
    return output


def verify_exact_coverage(
    descriptors: Sequence[ChunkDescriptor],
    source_size_bytes: int,
) -> None:
    if source_size_bytes == 0:
        if descriptors and not (
            len(descriptors) == 1
            and descriptors[0].core_start == 0
            and descriptors[0].core_end == 0
            and descriptors[0].complete_source
        ):
            raise ChunkingError(
                "empty source permits only one explicit zero-range descriptor"
            )
        return
    if not descriptors:
        raise ChunkingError("non-empty source requires chunk descriptors")
    ordered = sorted(descriptors, key=lambda item: (item.core_start, item.core_end))
    expected = 0
    source_digest = ordered[0].source_sha256
    source_ref = ordered[0].source_ref
    seen: set[str] = set()
    for descriptor in ordered:
        if descriptor.chunk_id in seen:
            raise ChunkingError(f"duplicate chunk id: {descriptor.chunk_id}")
        seen.add(descriptor.chunk_id)
        if descriptor.source_sha256 != source_digest or descriptor.source_ref != source_ref:
            raise ChunkingError("coverage ledger mixes source identities")
        if descriptor.core_start != expected:
            relation = "gap" if descriptor.core_start > expected else "duplicate"
            raise ChunkingError(
                f"chunk core coverage has {relation} at byte {expected}"
            )
        expected = descriptor.core_end
    if expected != source_size_bytes:
        raise ChunkingError(
            f"chunk core coverage ends at {expected}, expected {source_size_bytes}"
        )


def pack_reduce_fan_in(
    results: Sequence[Mapping[str, Any]],
    *,
    token_budget: int,
) -> list[list[dict[str, Any]]]:
    """Pack stable ordered canonical results without truncating any result."""

    if token_budget < 1:
        raise ChunkingError("reduce token budget must be positive")
    ordered = sorted(
        (dict(item) for item in results),
        key=lambda item: (
            str(item.get("source_ref") or ""),
            int(item.get("core_start", 0) or 0),
            str(item.get("result_id") or item.get("chunk_id") or ""),
        ),
    )
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for item in ordered:
        if get_token_count(canonical_json(item)) > token_budget:
            raise ChunkingError("one canonical reduce result exceeds the reducer budget")
        candidate = [*current, item]
        if current and get_token_count(canonical_json(candidate)) > token_budget:
            groups.append(current)
            current = [item]
        else:
            current = candidate
    if current:
        groups.append(current)
    return groups


def reduce_input_digest(children: Sequence[Mapping[str, Any]]) -> str:
    return canonical_digest([dict(item) for item in children])


__all__ = [
    "ChunkSlice",
    "ChunkingError",
    "LaneTokenBudget",
    "pack_reduce_fan_in",
    "reduce_input_digest",
    "slice_text_from_byte_cursor",
    "split_text_source",
    "verify_exact_coverage",
]
