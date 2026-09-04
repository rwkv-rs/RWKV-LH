from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
    RWKV7InitialStateProfiles,
)
from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings


class _FakeModel:
    def zero_state(self, batch_size: int):
        return [
            torch.zeros((2, 2, batch_size, 8)),
            torch.zeros((2, batch_size, 3, 2, 2)),
            torch.zeros((batch_size,), dtype=torch.int32),
        ]


class _PairTokenizer:
    pad_token_id = 0

    @staticmethod
    def encode(
        _text: str,
        *,
        truncation: bool,
        max_length: int,
        add_special_tokens: bool,
    ) -> list[int]:
        assert truncation is True
        assert max_length >= 8
        assert add_special_tokens is True
        return [1, 2]


class _PrefixTokenizer:
    pad_token_id = 0

    @staticmethod
    def encode(text: str, **_kwargs: object) -> list[int]:
        return [1, 2, 3, 4] if text == "prefix" else [1, 2, 3, 4, 5]


class _PairModel:
    def zero_state(self, _batch_size: int):
        raise AssertionError("extract_hidden_pair bypassed the profile-aware state path")

    @staticmethod
    def forward_all_hidden(tokens: torch.Tensor, state: object) -> torch.Tensor:
        assert state == ["profile-aware-state"]
        return torch.arange(
            tokens.shape[0] * tokens.shape[1] * 4,
            dtype=torch.float32,
        ).reshape(tokens.shape[0], tokens.shape[1], 4)


class _AdvanceTokenizer:
    @staticmethod
    def encode(_text: str, **kwargs: object) -> list[int]:
        assert kwargs["truncation"] is False
        return [1, 2, 3]


class _SuffixTokenizer:
    @staticmethod
    def encode(text: str, **kwargs: object) -> list[int]:
        assert kwargs["truncation"] is False
        assert kwargs["add_special_tokens"] is False
        values = {
            "prefixsuffix": [10, 11, 12, 13],
            "prefixbroken": [10, 11, 12, 13],
            "prefix": [10, 11],
            "suffix": [12, 13],
            "broken": [10, 99],
        }
        return values[text]


class _AdvanceModel:
    @staticmethod
    def zero_state(batch_size: int):
        return [
            torch.zeros((1, 1, batch_size, 2)),
            torch.zeros((1, batch_size, 1, 2, 2)),
            torch.zeros((batch_size,), dtype=torch.int32),
        ]

    @staticmethod
    def forward_all_hidden(tokens: torch.Tensor, state: list[torch.Tensor]) -> torch.Tensor:
        state[2].add_(tokens.shape[1])
        return torch.arange(
            tokens.shape[0] * tokens.shape[1] * 4,
            dtype=torch.float32,
        ).reshape(tokens.shape[0], tokens.shape[1], 4)


def test_tuned_wkv_state_is_copied_to_each_batch_row_without_touching_other_state() -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _FakeModel()
    extractor._initial_wkv_state = torch.arange(24, dtype=torch.float32).reshape(2, 3, 2, 2)
    state = extractor._new_state(4)
    assert torch.count_nonzero(state[0]) == 0
    assert torch.count_nonzero(state[2]) == 0
    assert tuple(state[1].shape) == (2, 4, 3, 2, 2)
    for batch_index in range(4):
        assert torch.equal(state[1][:, batch_index], extractor._initial_wkv_state)


def test_hidden_pair_uses_profile_aware_fresh_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _PairModel()
    extractor._tokenizer = _PairTokenizer()
    extractor._runtime = {}
    monkeypatch.setattr(extractor, "load", lambda: None)
    monkeypatch.setattr(extractor, "_load_base_identity", lambda: {})
    monkeypatch.setattr(
        extractor,
        "_new_state",
        lambda batch_size: ["profile-aware-state"] if batch_size == 1 else None,
    )
    original_full = torch.full
    original_tensor = torch.tensor

    def cpu_full(*args, **kwargs):
        kwargs.pop("device", None)
        return original_full(*args, **kwargs)

    def cpu_tensor(*args, **kwargs):
        kwargs.pop("device", None)
        return original_tensor(*args, **kwargs)

    monkeypatch.setattr(torch, "full", cpu_full)
    monkeypatch.setattr(torch, "tensor", cpu_tensor)

    last, mean, counts, identity = extractor.extract_hidden_pair(["request"])

    assert tuple(last.shape) == (1, 4)
    assert tuple(mean.shape) == (1, 4)
    assert counts == [2]
    assert identity["feature_protocols"]["last"].endswith("hidden-last.v1")


def test_hidden_prefix_and_full_means_share_one_profile_aware_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _PairModel()
    extractor._tokenizer = _PrefixTokenizer()
    extractor._runtime = {}
    monkeypatch.setattr(extractor, "load", lambda: None)
    monkeypatch.setattr(extractor, "_load_base_identity", lambda: {})
    monkeypatch.setattr(extractor, "_new_state", lambda _batch_size: ["profile-aware-state"])
    original_full = torch.full
    original_tensor = torch.tensor
    monkeypatch.setattr(torch, "full", lambda *args, **kwargs: original_full(*args, **{key: value for key, value in kwargs.items() if key != "device"}))
    monkeypatch.setattr(torch, "tensor", lambda *args, **kwargs: original_tensor(*args, **{key: value for key, value in kwargs.items() if key != "device"}))

    full, prefix, counts, prefix_counts, identity = extractor.extract_hidden_prefix_mean_pair(
        ["prefix-and-suffix"], ["prefix"]
    )

    assert tuple(full.shape) == tuple(prefix.shape) == (1, 4)
    assert counts == [5]
    assert prefix_counts == [4]
    assert identity["extraction"] == "one-forward-full-and-causal-prefix-token-mean"


def test_persistent_hidden_views_share_one_forward_and_preserve_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _AdvanceModel()
    extractor._tokenizer = _AdvanceTokenizer()
    extractor._runtime = {}
    monkeypatch.setattr(extractor, "load", lambda: None)
    monkeypatch.setattr(extractor, "_load_base_identity", lambda: {})
    original_tensor = torch.tensor
    monkeypatch.setattr(
        torch,
        "tensor",
        lambda *args, **kwargs: original_tensor(
            *args, **{key: value for key, value in kwargs.items() if key != "device"}
        ),
    )

    views, state, count, identity = extractor.advance_hidden_views("first")
    assert count == 3
    assert torch.equal(views["mean"], torch.tensor([4.0, 5.0, 6.0, 7.0]))
    assert torch.equal(views["last"], torch.tensor([8.0, 9.0, 10.0, 11.0]))
    assert identity["feature_protocols"] == {
        "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
    }
    parent = [value.clone() for value in state]
    _views, advanced, _count, continuation_identity = extractor.advance_hidden_views(
        "next", parent_state=state, continuation=True
    )
    assert all(torch.equal(left, right) for left, right in zip(state, parent))
    assert int(advanced[2].item()) == int(state[2].item()) + 3
    assert continuation_identity["continuation"] is True
    assert continuation_identity["generated_rwkv_text"] is False
    assert continuation_identity["sampling_invoked"] is False


def test_persistent_suffix_views_pool_tail_without_splitting_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _AdvanceModel()
    extractor._tokenizer = _SuffixTokenizer()
    extractor._runtime = {}
    monkeypatch.setattr(extractor, "load", lambda: None)
    monkeypatch.setattr(extractor, "_load_base_identity", lambda: {})
    original_tensor = torch.tensor
    monkeypatch.setattr(
        torch,
        "tensor",
        lambda *args, **kwargs: original_tensor(
            *args, **{key: value for key, value in kwargs.items() if key != "device"}
        ),
    )
    parent = _AdvanceModel.zero_state(1)
    parent[2].fill_(7)
    preserved = [value.clone() for value in parent]

    views, state, total, prefix, suffix, identity = (
        extractor.advance_hidden_suffix_views(
            "prefixsuffix",
            suffix_start=len("prefix"),
            parent_state=parent,
            continuation=True,
        )
    )

    assert total == 4
    assert prefix == suffix == 2
    assert torch.equal(views["mean"], torch.tensor([10.0, 11.0, 12.0, 13.0]))
    assert torch.equal(views["last"], torch.tensor([12.0, 13.0, 14.0, 15.0]))
    assert int(state[2].item()) == 11
    assert all(torch.equal(left, right) for left, right in zip(parent, preserved))
    assert identity["one_forward"] is True
    assert identity["token_sequence_exact"] is True
    assert identity["generated_rwkv_text"] is False


def test_persistent_suffix_views_reject_nonadditive_token_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _AdvanceModel()
    extractor._tokenizer = _SuffixTokenizer()
    extractor._runtime = {}
    monkeypatch.setattr(extractor, "load", lambda: None)
    parent = _AdvanceModel.zero_state(1)

    with pytest.raises(ValueError, match="not token additive"):
        extractor.advance_hidden_suffix_views(
            "prefixbroken",
            suffix_start=len("prefix"),
            parent_state=parent,
            continuation=True,
        )


def test_persistent_global_suffix_views_share_exactly_one_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = PersistentVLLMRWKVExtractor(LocalVLLMRWKVSettings())
    extractor._model = _AdvanceModel()
    extractor._tokenizer = _SuffixTokenizer()
    extractor._runtime = {}
    monkeypatch.setattr(extractor, "load", lambda: None)
    monkeypatch.setattr(extractor, "_load_base_identity", lambda: {})
    original_tensor = torch.tensor
    monkeypatch.setattr(
        torch,
        "tensor",
        lambda *args, **kwargs: original_tensor(
            *args, **{key: value for key, value in kwargs.items() if key != "device"}
        ),
    )
    calls = 0
    original_forward = _AdvanceModel.forward_all_hidden

    def counted_forward(
        tokens: torch.Tensor, state: list[torch.Tensor]
    ) -> torch.Tensor:
        nonlocal calls
        calls += 1
        return original_forward(tokens, state)

    monkeypatch.setattr(extractor._model, "forward_all_hidden", counted_forward)
    parent = _AdvanceModel.zero_state(1)
    parent[2].fill_(7)
    preserved = [value.clone() for value in parent]

    views, state, total, prefix, suffix, identity = (
        extractor.advance_hidden_global_suffix_views(
            "prefixsuffix",
            suffix_start=len("prefix"),
            parent_state=parent,
            continuation=True,
        )
    )

    assert calls == 1
    assert total == 4
    assert prefix == suffix == 2
    assert set(views) == {"global_mean", "suffix_mean", "final_last"}
    assert torch.equal(views["global_mean"], torch.tensor([6.0, 7.0, 8.0, 9.0]))
    assert torch.equal(views["suffix_mean"], torch.tensor([10.0, 11.0, 12.0, 13.0]))
    assert torch.equal(views["final_last"], torch.tensor([12.0, 13.0, 14.0, 15.0]))
    assert int(state[2].item()) == 11
    assert all(torch.equal(left, right) for left, right in zip(parent, preserved))
    assert identity["one_forward"] is True
    assert identity["token_sequence_exact"] is True
    assert identity["generated_rwkv_text"] is False
    assert identity["sampling_invoked"] is False


def test_state_profile_identity_is_all_or_nothing() -> None:
    with pytest.raises(ValueError, match="requires manifest"):
        LocalVLLMRWKVSettings(state_profile_manifest=Path("profiles.json"))
    with pytest.raises(ValueError, match="profile ID"):
        LocalVLLMRWKVSettings(
            state_profile_manifest=Path("profiles.json"),
            state_profile_manifest_sha256="a" * 64,
            state_profile_id="bad profile",
            state_profile_sha256="b" * 64,
        )


def test_explicit_zero_profile_keeps_the_native_zero_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = LocalVLLMRWKVSettings(
        state_profile_manifest=Path("profiles.json"),
        state_profile_manifest_sha256="a" * 64,
        state_profile_id="zero",
        state_profile_sha256="0" * 64,
    )
    extractor = PersistentVLLMRWKVExtractor(settings)
    monkeypatch.setattr(
        RWKV7InitialStateProfiles,
        "load",
        lambda *_args, **_kwargs: RWKV7InitialStateProfiles.zero_only(),
    )
    model = type(
        "ZeroProfileModel",
        (),
        {
            "total_num_layers": 2,
            "num_attention_heads": 2,
            "head_size": 64,
            "z": {"blocks.0.att.key.weight": torch.zeros(1)},
            "wkv_state_dtype": torch.float32,
        },
    )()

    assert extractor._load_initial_wkv_state(model) is None


def test_derived_runtime_validates_state_against_model_artifact_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_revision = "1" * 40
    artifact_revision = "2" * 40
    settings = LocalVLLMRWKVSettings(
        engine_revision=runtime_revision,
        model_artifact_engine_revision=artifact_revision,
        runtime_derivation_manifest=Path("runtime-derivation.json"),
        runtime_derivation_manifest_sha256="d" * 64,
        state_profile_manifest=Path("profiles.json"),
        state_profile_manifest_sha256="a" * 64,
        state_profile_id="zero",
        state_profile_sha256="0" * 64,
    )
    extractor = PersistentVLLMRWKVExtractor(settings)
    captured: dict[str, object] = {}

    def fake_load(*_args: object, **kwargs: object) -> RWKV7InitialStateProfiles:
        captured.update(kwargs)
        return RWKV7InitialStateProfiles.zero_only()

    monkeypatch.setattr(RWKV7InitialStateProfiles, "load", fake_load)
    model = type(
        "DerivedRuntimeProfileModel",
        (),
        {
            "total_num_layers": 2,
            "num_attention_heads": 2,
            "head_size": 64,
            "z": {"blocks.0.att.key.weight": torch.zeros(1)},
            "wkv_state_dtype": torch.float32,
        },
    )()

    assert extractor._load_initial_wkv_state(model) is None
    assert captured["model_revision"] == artifact_revision
    assert captured["model_revision"] != runtime_revision
