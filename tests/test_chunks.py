from __future__ import annotations

import pytest

from rwkv_lh.chunks import (
    ChunkingError,
    LaneTokenBudget,
    pack_reduce_fan_in,
    slice_text_from_byte_cursor,
    split_text_source,
    verify_exact_coverage,
)
from rwkv_lh.model_io import canonical_json
from rwkv_lh.token_budget import get_token_count


def test_lane_budget_uses_all_16k_reserves() -> None:
    budget = LaneTokenBudget(
        max_model_tokens=16384,
        bos_tokens=1,
        safety_tokens=512,
        max_output_tokens=1200,
        fixed_prefix_tokens=1800,
        event_metadata_tokens=400,
        boundary_carry_tokens=600,
    )
    budget.validate()
    assert budget.input_budget == 14671
    assert budget.raw_chunk_budget == 11871


def test_token_chunks_cover_utf8_source_exactly() -> None:
    text = ("第一行 RWKV state\n" * 50) + ("x" * 500) + "\n最后一行"
    chunks = split_text_source(
        "input.txt",
        text,
        raw_chunk_tokens=80,
        overlap_tokens=8,
    )
    assert len(chunks) > 2
    verify_exact_coverage(
        [item.descriptor for item in chunks],
        len(text.encode("utf-8")),
    )
    assert "".join(item.core_text for item in chunks) == text
    assert all(get_token_count(item.core_text) <= 80 for item in chunks)
    assert chunks[0].descriptor.previous_chunk_id is None
    assert chunks[-1].descriptor.next_chunk_id is None
    assert all(
        left.descriptor.next_chunk_id == right.descriptor.chunk_id
        and right.descriptor.previous_chunk_id == left.descriptor.chunk_id
        for left, right in zip(chunks, chunks[1:])
    )


def test_coverage_ledger_rejects_gap_and_duplicate() -> None:
    chunks = split_text_source("input.txt", "abcdef" * 30, raw_chunk_tokens=5)
    descriptors = [item.descriptor for item in chunks]
    damaged = [descriptors[0], *descriptors[2:]]
    with pytest.raises(ChunkingError, match="gap"):
        verify_exact_coverage(damaged, len(("abcdef" * 30).encode()))
    with pytest.raises(ChunkingError, match="duplicate"):
        verify_exact_coverage(
            [descriptors[0], descriptors[0], *descriptors[1:]],
            len(("abcdef" * 30).encode()),
        )


def test_reduce_packing_is_stable_and_never_truncates() -> None:
    results = [
        {"result_id": "R3", "source_ref": "b", "core_start": 0, "value": "c" * 30},
        {"result_id": "R2", "source_ref": "a", "core_start": 20, "value": "b" * 30},
        {"result_id": "R1", "source_ref": "a", "core_start": 0, "value": "a" * 30},
    ]
    one = pack_reduce_fan_in(results, token_budget=60)
    two = pack_reduce_fan_in(list(reversed(results)), token_budget=60)
    assert one == two
    flattened = [item for group in one for item in group]
    assert [item["result_id"] for item in flattened] == ["R1", "R2", "R3"]
    assert sorted(canonical_json(item) for item in flattened) == sorted(
        canonical_json(item) for item in results
    )


def test_reduce_rejects_single_oversized_result() -> None:
    with pytest.raises(ChunkingError, match="exceeds"):
        pack_reduce_fan_in(
            [{"result_id": "R1", "source_ref": "a", "value": "x" * 10000}],
            token_budget=5,
        )


def test_token_cursor_uses_exact_utf8_byte_continuation() -> None:
    text = "你好 RWKV\n" * 200
    first = slice_text_from_byte_cursor(
        "source.txt",
        text,
        start_byte=0,
        max_tokens=40,
    )
    second = slice_text_from_byte_cursor(
        "source.txt",
        text,
        start_byte=first.descriptor.core_end,
        max_tokens=40,
    )
    assert get_token_count(first.text) <= 40
    assert first.descriptor.core_end == second.descriptor.core_start
    encoded = text.encode("utf-8")
    assert encoded[: first.descriptor.core_end].decode("utf-8") == first.text
    with pytest.raises(ChunkingError, match="UTF-8 boundary"):
        slice_text_from_byte_cursor(
            "source.txt",
            text,
            start_byte=1,
            max_tokens=40,
        )


def test_token_cursor_at_exact_eof_is_a_successful_empty_observation() -> None:
    text = "你好 RWKV\n"
    source_size = len(text.encode("utf-8"))
    eof = slice_text_from_byte_cursor(
        "source.txt",
        text,
        start_byte=source_size,
        max_tokens=40,
    )

    assert eof.text == ""
    assert eof.core_text == ""
    assert eof.descriptor.core_start == source_size
    assert eof.descriptor.core_end == source_size
    assert eof.descriptor.token_start == eof.descriptor.token_end
