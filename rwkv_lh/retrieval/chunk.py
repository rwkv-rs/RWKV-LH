"""Exact-offset deterministic chunks for immutable clean snapshots."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    start_char: int
    end_char: int
    text: str


def chunk_text(
    text: str,
    *,
    max_chars: int = 6000,
    overlap_chars: int = 400,
    max_chunks: int = 32,
) -> tuple[TextChunk, ...]:
    """Split text at exact source offsets while keeping bounds hard."""

    source = str(text or "")
    if not source:
        return ()
    if max_chars < 256 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("invalid chunk bounds")
    chunks: list[TextChunk] = []
    start = 0
    while start < len(source) and len(chunks) < max_chunks:
        hard_end = min(len(source), start + max_chars)
        end = hard_end
        if hard_end < len(source):
            floor = start + max_chars // 2
            boundaries = [
                source.rfind("\n\n", floor, hard_end),
                source.rfind("\n", floor, hard_end),
                source.rfind("。", floor, hard_end),
                source.rfind(". ", floor, hard_end),
                source.rfind(" ", floor, hard_end),
            ]
            selected = max(boundaries)
            if selected >= floor:
                end = selected + (2 if source[selected:selected + 2] in {"\n\n", ". "} else 1)
        if end <= start:
            end = hard_end
        chunks.append(TextChunk(len(chunks), start, end, source[start:end]))
        if end >= len(source):
            break
        start = max(start + 1, end - overlap_chars)
    return tuple(chunks)


__all__ = ["TextChunk", "chunk_text"]
