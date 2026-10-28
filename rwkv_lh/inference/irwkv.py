"""Persistent direct-model adapter for the pinned local irwkv runtime.

This module is imported by the dedicated Router process, not by the Harness
process.  All irwkv and CUDA imports remain lazy so the product runtime keeps a
small dependency boundary and a separate GPU/process lifecycle.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.state_router.local_backend import (
    LocalIRWKVExtractor,
    LocalIRWKVSettings,
)


class PersistentIRWKVExtractor(LocalIRWKVExtractor):
    """Load one 0.4B model once and serve serialized feature extraction calls."""

    def __init__(self, settings: LocalIRWKVSettings | None = None) -> None:
        super().__init__(settings)
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._runtime: dict[str, Any] | None = None
        self._initial_wkv_state: Any | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        if self._model is not None:
            return
        self._load_base_identity()
        import torch
        import transformers
        import irwkv
        from transformers import AutoTokenizer
        module_path = Path(irwkv.__file__).resolve()
        if not module_path.is_relative_to(self.settings.engine_root.resolve()):
            raise RuntimeError('irwkv resolved outside the frozen source tree')
        tokenizer = AutoTokenizer.from_pretrained(self.settings.model, local_files_only=True, trust_remote_code=False)
        model = self._load_direct_model(self.settings.model.resolve())
        from .native_weight_identity import fingerprint_model
        self._loaded_weight_identity = fingerprint_model(model.model)
        self._initial_wkv_state = self._load_initial_wkv_state(model)
        self._runtime = dict(model_class=type(model.model).__name__,
            hidden_size=model.hidden_size, num_hidden_layers=model.total_num_layers,
            head_size=model.head_size, vocab_size=model.vocab_size,
            wkv_mode='fp32io16', wkv_state_dtype='torch.float32',
            runtime_compute_dtype='torch.bfloat16', torch_version=torch.__version__,
            irwkv_module=str(module_path), irwkv_version=irwkv.__version__,
            transformers_version=transformers.__version__,
            loaded_weight_identity=self._loaded_weight_identity)
        self._model, self._tokenizer = model, tokenizer

    def _load_initial_wkv_state(self, model: Any) -> Any | None:
        """Load one explicitly pinned selector state without changing model weights.

        The profile loader converts portable ``[L,H,V,K]`` tensors to the
        recurrent runtime's ``[L,H,K,V]`` layout.  ``_new_state`` therefore
        performs only the batch expansion and copy, never another transpose.
        """

        manifest = self.settings.state_profile_manifest
        if manifest is None:
            return None
        from rwkv_lh.inference.irwkv_state_profiles_v1 import (
            RWKV7InitialStateProfiles,
        )

        profiles = RWKV7InitialStateProfiles.load(
            str(manifest.resolve()),
            self.settings.state_profile_manifest_sha256,
            model_artifact=str(self.settings.model.resolve()),
            model_revision=self._loaded_weight_identity['tensors_sha256'],
            total_num_layers=int(model.total_num_layers),
            total_num_heads=int(model.num_attention_heads),
            layer_offset=0,
            num_layers=int(model.total_num_layers),
            tp_size=1,
            tp_rank=0,
            num_heads=int(model.num_attention_heads),
            head_size=int(model.head_size),
            device=model.device,
            dtype=model.wkv_state_dtype,
        )
        profile = profiles.resolve(self.settings.state_profile_id)
        if profile.state_sha256 != self.settings.state_profile_sha256:
            raise ValueError("local RWKV state-profile SHA-256 mismatch")
        if profile.wkv_state is None:
            if profile.profile_id != "zero" or profile.state_sha256 != "0" * 64:
                raise ValueError("local RWKV state profile has invalid zero identity")
            return None
        return profile.wkv_state

    def _new_state(self, batch_size: int) -> Any:
        assert self._model is not None
        state = self._model.zero_state(batch_size)
        if self._initial_wkv_state is not None:
            initial = self._initial_wkv_state.unsqueeze(1).expand(
                -1, batch_size, -1, -1, -1
            )
            state[1].copy_(initial)
        return state

    def _state_for_advance(
        self,
        parent_state: Sequence[Any] | None,
        torch_module: Any,
    ) -> Any:
        """Create one authoritative mutable CUDA state from an immutable parent."""

        if parent_state is None:
            return self._new_state(1)
        if len(parent_state) != 3:
            raise ValueError("persistent irwkv parent state must have 3 tensors")
        assert self._model is not None
        state = self._model.zero_state(1)
        for index, (source, destination) in enumerate(zip(parent_state, state)):
            if not isinstance(source, torch_module.Tensor):
                raise TypeError(
                    f"persistent irwkv parent state {index} is not a tensor"
                )
            if tuple(source.shape) != tuple(destination.shape):
                raise ValueError(
                    f"persistent irwkv parent state {index} shape mismatch"
                )
            if source.dtype != destination.dtype:
                raise ValueError(
                    f"persistent irwkv parent state {index} dtype mismatch"
                )
            if source.is_floating_point() and not bool(
                torch_module.isfinite(source).all()
            ):
                raise ValueError(
                    f"persistent irwkv parent state {index} is non-finite"
                )
            destination.copy_(source.to(device=destination.device))
        return state

    def _stateful_token_ids(self, text: str, *, continuation: bool) -> list[int]:
        assert self._tokenizer is not None
        token_ids = self._tokenizer.encode(
            str(text),
            truncation=False,
            add_special_tokens=not continuation,
        )
        if not token_ids or len(token_ids) > self.settings.max_tokens:
            raise ValueError("persistent irwkv state advance token count is invalid")
        return token_ids

    def advance_hidden_feature(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        feature_protocol: str = "rwkv-lh.irwkv-final-hidden-last.v1",
        export_state: bool = True,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]:
        """Advance one input and expose one unmodified hidden view."""

        if not str(text):
            raise ValueError("persistent irwkv state advance text must be non-empty")
        if feature_protocol not in {
            "rwkv-lh.irwkv-final-hidden-last.v1",
            "rwkv-lh.irwkv-final-hidden-mean.v1",
        }:
            raise ValueError("unsupported stateful hidden feature protocol")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent irwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            token_ids = self._stateful_token_ids(text, continuation=continuation)
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor(
                [token_ids], dtype=torch.long, device="cuda"
            )
            hidden = self._model.forward_all_hidden(tokens, state)
            feature = (
                hidden[0, -1]
                if feature_protocol.endswith("-last.v1")
                else hidden[0].float().mean(dim=0)
            ).detach().float().cpu()
            exported_state = (
                [value.detach().cpu().contiguous().clone() for value in state]
                if export_state
                else []
            )
            if not bool(torch.isfinite(feature).all()):
                raise RuntimeError(
                    "persistent irwkv returned non-finite stateful hidden features"
                )
            identity = {
                **self._load_base_identity(),
                "feature_protocol": feature_protocol,
                "extraction": (
                    "causal-lane-final-layer-last-real-token"
                    if feature_protocol.endswith("-last.v1")
                    else "causal-lane-current-segment-real-token-mean"
                ),
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "state_exported": export_state,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return feature, exported_state, len(token_ids), identity

    def advance_hidden_last(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        export_state: bool = True,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]:
        """Compatibility wrapper for the registered last-hidden protocol."""

        return self.advance_hidden_feature(
            text,
            parent_state=parent_state,
            continuation=continuation,
            feature_protocol="rwkv-lh.irwkv-final-hidden-last.v1",
            export_state=export_state,
        )

    def advance_hidden_views(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        export_state: bool = True,
    ) -> tuple[Mapping[str, Any], list[Any], int, Mapping[str, Any]]:
        """Advance once and expose unchanged mean and last hidden views.

        This is an extraction-only optimization for fixed ablations. It does
        not generate, sample, mutate model weights, or advance the supplied
        parent state twice.
        """

        if not str(text):
            raise ValueError("persistent irwkv state advance text must be non-empty")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent irwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            token_ids = self._stateful_token_ids(text, continuation=continuation)
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor([token_ids], dtype=torch.long, device="cuda")
            hidden = self._model.forward_all_hidden(tokens, state)
            features = {
                "mean": hidden[0].float().mean(dim=0).detach().float().cpu(),
                "last": hidden[0, -1].detach().float().cpu(),
            }
            if any(not bool(torch.isfinite(value).all()) for value in features.values()):
                raise RuntimeError(
                    "persistent irwkv returned non-finite stateful hidden views"
                )
            exported_state = (
                [value.detach().cpu().contiguous().clone() for value in state]
                if export_state
                else []
            )
            identity = {
                **self._load_base_identity(),
                "feature_protocols": {
                    "mean": "rwkv-lh.irwkv-final-hidden-mean.v1",
                    "last": "rwkv-lh.irwkv-final-hidden-last.v1",
                },
                "extraction": "one-forward-current-segment-real-token-mean-and-last",
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "state_exported": export_state,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return features, exported_state, len(token_ids), identity

    def evaluate_suffix_choices(
        self,
        prompt: str,
        *,
        expected_label: str,
        candidate_suffixes: Mapping[str, str],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        """Evaluate one exact role suffix without training a downstream decoder.

        The prompt is advanced exactly once from the configured fresh initial
        State.  Teacher-forced scoring, unrestricted greedy decoding, and
        eligible-trie decoding then receive independent clones of the same
        post-prompt recurrent State.  Candidate strings must be exact additive
        tokenizer suffixes of the supplied prompt.
        """

        if not str(prompt):
            raise ValueError("persistent irwkv suffix prompt must be non-empty")
        if not candidate_suffixes or expected_label not in candidate_suffixes:
            raise ValueError("suffix candidates must contain the expected label")
        normalized = {str(label): str(value) for label, value in candidate_suffixes.items()}
        if (
            len(normalized) != len(candidate_suffixes)
            or any(not label or not value for label, value in normalized.items())
        ):
            raise ValueError("suffix candidate labels and values must be non-empty")
        if len(set(normalized.values())) != len(normalized):
            raise ValueError("suffix candidate values must be unique")

        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            prompt_ids = self._tokenizer.encode(
                str(prompt), truncation=False, add_special_tokens=True
            )
            if not prompt_ids or len(prompt_ids) > self.settings.max_tokens:
                raise ValueError("persistent irwkv suffix prompt token count is invalid")

            candidate_ids: dict[str, tuple[int, ...]] = {}
            for label, suffix in normalized.items():
                suffix_ids = tuple(
                    int(value)
                    for value in self._tokenizer.encode(
                        suffix, truncation=False, add_special_tokens=False
                    )
                )
                combined_ids = self._tokenizer.encode(
                    str(prompt) + suffix,
                    truncation=False,
                    add_special_tokens=True,
                )
                if (
                    not suffix_ids
                    or list(prompt_ids) + list(suffix_ids) != list(combined_ids)
                    or len(combined_ids) > self.settings.max_tokens
                ):
                    raise ValueError(
                        "persistent irwkv candidate is not an exact additive suffix"
                    )
                candidate_ids[label] = suffix_ids
            if len(set(candidate_ids.values())) != len(candidate_ids):
                raise ValueError("suffix candidates must have unique token sequences")

            trie: dict[object, Any] = {}
            terminal = object()
            for label, token_ids in candidate_ids.items():
                node = trie
                for token_id in token_ids:
                    if terminal in node:
                        raise ValueError("suffix candidate token sequences have a prefix collision")
                    node = node.setdefault(token_id, {})
                if node:
                    raise ValueError("suffix candidate token sequences have a prefix collision")
                node[terminal] = label

            prompt_state = self._new_state(1)
            prompt_tensor = torch.tensor(
                [prompt_ids], dtype=torch.long, device="cuda"
            )
            prompt_hidden = self._model.forward_all_hidden(prompt_tensor, prompt_state)
            first_logits = self._model.project_logits_fp32(
                prompt_hidden[:, -1, :]
            ).float()
            if first_logits.ndim != 2 or first_logits.shape[0] != 1:
                raise RuntimeError("persistent irwkv returned invalid suffix logits")

            def cloned_state() -> list[Any]:
                return [value.clone() for value in prompt_state]

            def advance_one(
                token_id: int,
                state: list[Any],
            ) -> Any:
                token = torch.tensor([[token_id]], dtype=torch.long, device="cuda")
                hidden = self._model.forward_all_hidden(token, state)
                return self._model.project_logits_fp32(hidden[:, -1, :]).float()

            def token_metrics(logits: Any, target_id: int) -> dict[str, Any]:
                row = logits[0]
                if not bool(torch.isfinite(row).all()):
                    raise RuntimeError("persistent irwkv returned non-finite suffix logits")
                target_logit = row[target_id]
                predicted_id = int(torch.argmax(row).item())
                rank = 1 + int(torch.count_nonzero(row > target_logit).item())
                top_values, top_indices = torch.topk(row, k=min(2, int(row.numel())))
                if int(top_indices[0].item()) == target_id and len(top_values) > 1:
                    best_other = top_values[1]
                elif int(top_indices[0].item()) == target_id:
                    best_other = torch.tensor(float("-inf"), device=row.device)
                else:
                    best_other = top_values[0]
                log_probability = torch.log_softmax(row, dim=-1)[target_id]
                return {
                    "target_token_id": int(target_id),
                    "predicted_token_id": predicted_id,
                    "top1_correct": predicted_id == target_id,
                    "target_rank": rank,
                    "target_log_probability": float(log_probability.item()),
                    "target_vs_best_other_margin": float(
                        (target_logit - best_other).item()
                    ),
                }

            expected_ids = candidate_ids[expected_label]
            teacher_state = cloned_state()
            teacher_logits = first_logits
            teacher_tokens: list[dict[str, Any]] = []
            for position, target_id in enumerate(expected_ids):
                metrics = token_metrics(teacher_logits, target_id)
                metrics["position"] = position
                teacher_tokens.append(metrics)
                if position + 1 < len(expected_ids):
                    teacher_logits = advance_one(target_id, teacher_state)
            total_nll = -sum(
                float(row["target_log_probability"]) for row in teacher_tokens
            )

            unrestricted_state = cloned_state()
            unrestricted_logits = first_logits
            unrestricted_ids: list[int] = []
            for position in range(len(expected_ids)):
                generated = int(torch.argmax(unrestricted_logits[0]).item())
                unrestricted_ids.append(generated)
                if position + 1 < len(expected_ids):
                    unrestricted_logits = advance_one(generated, unrestricted_state)

            constrained_state = cloned_state()
            constrained_logits = first_logits
            constrained_ids: list[int] = []
            constrained_decisions: list[dict[str, Any]] = []
            node = trie
            while terminal not in node:
                allowed = sorted(int(key) for key in node if key is not terminal)
                if not allowed:
                    raise RuntimeError("suffix candidate trie reached an empty branch")
                chosen = max(
                    allowed,
                    key=lambda token_id: (
                        float(constrained_logits[0, token_id].item()),
                        -token_id,
                    ),
                )
                ordered = sorted(
                    (
                        (float(constrained_logits[0, token_id].item()), token_id)
                        for token_id in allowed
                    ),
                    key=lambda value: (-value[0], value[1]),
                )
                margin = (
                    ordered[0][0] - ordered[1][0]
                    if len(ordered) > 1
                    else None
                )
                constrained_decisions.append(
                    {
                        "position": len(constrained_ids),
                        "allowed_token_ids": allowed,
                        "allowed_token_logits": {
                            str(token_id): float(
                                constrained_logits[0, token_id].item()
                            )
                            for token_id in allowed
                        },
                        "chosen_token_id": chosen,
                        "chosen_token_logit": float(
                            constrained_logits[0, chosen].item()
                        ),
                        "chosen_vs_runner_up_margin": margin,
                    }
                )
                constrained_ids.append(chosen)
                node = node[chosen]
                if terminal not in node:
                    constrained_logits = advance_one(chosen, constrained_state)
            predicted_label = str(node[terminal])

            result = {
                "schema_version": "rwkv-lh.native-role-suffix-evaluation.v1",
                "expected_label": expected_label,
                "candidate_labels": list(normalized),
                "prompt_token_count": len(prompt_ids),
                "prompt_token_ids": list(prompt_ids),
                "prompt_token_ids_scope": "full_prompt",
                "input_bos_token_count": len(prompt_ids) - len(self._tokenizer.encode(
                    str(prompt), truncation=False, add_special_tokens=False)),
                "target_token_ids": list(expected_ids),
                "target_token_count": len(expected_ids),
                "teacher_forced": {
                    "tokens": teacher_tokens,
                    "total_nll": total_nll,
                    "mean_nll": total_nll / len(teacher_tokens),
                    "token_top1_correct": sum(
                        int(bool(row["top1_correct"])) for row in teacher_tokens
                    ),
                    "sequence_exact": all(
                        bool(row["top1_correct"]) for row in teacher_tokens
                    ),
                },
                "unrestricted_greedy": {
                    "token_ids": unrestricted_ids,
                    "expected_length_exact": tuple(unrestricted_ids) == expected_ids,
                },
                "eligible_trie": {
                    "token_ids": constrained_ids,
                    "predicted_label": predicted_label,
                    "correct": predicted_label == expected_label,
                    "decisions": constrained_decisions,
                },
            }
            identity = {
                **self._load_base_identity(),
                "feature_protocol": "rwkv-lh.native-role-suffix-evaluation.v1",
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "fresh_initial_state": True,
                "one_prompt_forward": True,
                "post_prompt_state_clones": 3,
                "token_sequence_exact": True,
                "downstream_decoder_trained": False,
            }
            self._last_identity = identity
            return result, identity

    def select_suffix_choices(
        self,
        prompt: str,
        *,
        candidate_suffixes: Mapping[str, str],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        """Select one exact suffix with the frozen LM head and eligible trie.

        This serving path deliberately has no expected label, teacher-forced
        branch, unrestricted generation branch, hidden-feature classifier, or
        learned downstream decoder.  It advances the prompt once, then follows
        the same deterministic eligible-token trie used by offline evaluation.
        """

        if not str(prompt):
            raise ValueError("persistent irwkv suffix prompt must be non-empty")
        if not candidate_suffixes:
            raise ValueError("native suffix selection requires candidates")
        normalized = {
            str(label): str(value) for label, value in candidate_suffixes.items()
        }
        if (
            len(normalized) != len(candidate_suffixes)
            or any(not label or not value for label, value in normalized.items())
            or len(set(normalized.values())) != len(normalized)
        ):
            raise ValueError("native suffix candidates must be non-empty and unique")

        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            prompt_ids = self._tokenizer.encode(
                str(prompt), truncation=False, add_special_tokens=True
            )
            if not prompt_ids or len(prompt_ids) > self.settings.max_tokens:
                raise ValueError(
                    "persistent irwkv suffix prompt token count is invalid"
                )

            candidate_ids: dict[str, tuple[int, ...]] = {}
            for label, suffix in normalized.items():
                suffix_ids = tuple(
                    int(value)
                    for value in self._tokenizer.encode(
                        suffix, truncation=False, add_special_tokens=False
                    )
                )
                combined_ids = self._tokenizer.encode(
                    str(prompt) + suffix,
                    truncation=False,
                    add_special_tokens=True,
                )
                if (
                    not suffix_ids
                    or list(prompt_ids) + list(suffix_ids) != list(combined_ids)
                    or len(combined_ids) > self.settings.max_tokens
                ):
                    raise ValueError(
                        "persistent irwkv candidate is not an exact additive suffix"
                    )
                candidate_ids[label] = suffix_ids
            if len(set(candidate_ids.values())) != len(candidate_ids):
                raise ValueError("suffix candidates must have unique token sequences")

            trie: dict[object, Any] = {}
            terminal = object()
            for label, token_ids in candidate_ids.items():
                node = trie
                for token_id in token_ids:
                    if terminal in node:
                        raise ValueError(
                            "suffix candidate token sequences have a prefix collision"
                        )
                    node = node.setdefault(token_id, {})
                if node:
                    raise ValueError(
                        "suffix candidate token sequences have a prefix collision"
                    )
                node[terminal] = label

            prompt_state = self._new_state(1)
            prompt_tensor = torch.tensor(
                [prompt_ids], dtype=torch.long, device="cuda"
            )
            prompt_hidden = self._model.forward_all_hidden(
                prompt_tensor, prompt_state
            )
            logits = self._model.project_logits_fp32(
                prompt_hidden[:, -1, :]
            ).float()
            if (
                logits.ndim != 2
                or logits.shape[0] != 1
                or not bool(torch.isfinite(logits).all())
            ):
                raise RuntimeError(
                    "persistent irwkv returned invalid suffix logits"
                )

            node = trie
            selected_ids: list[int] = []
            decisions: list[dict[str, Any]] = []
            while terminal not in node:
                allowed = sorted(int(key) for key in node if key is not terminal)
                if not allowed:
                    raise RuntimeError("suffix candidate trie reached an empty branch")
                ordered = sorted(
                    (
                        (float(logits[0, token_id].item()), token_id)
                        for token_id in allowed
                    ),
                    key=lambda value: (-value[0], value[1]),
                )
                chosen = ordered[0][1]
                decisions.append(
                    {
                        "position": len(selected_ids),
                        "allowed_token_ids": allowed,
                        "allowed_token_logits": {
                            str(token_id): float(logits[0, token_id].item())
                            for token_id in allowed
                        },
                        "chosen_token_id": chosen,
                        "chosen_token_logit": float(logits[0, chosen].item()),
                        "chosen_vs_runner_up_margin": (
                            ordered[0][0] - ordered[1][0]
                            if len(ordered) > 1
                            else None
                        ),
                    }
                )
                selected_ids.append(chosen)
                node = node[chosen]
                if terminal not in node:
                    token = torch.tensor(
                        [[chosen]], dtype=torch.long, device="cuda"
                    )
                    hidden = self._model.forward_all_hidden(token, prompt_state)
                    logits = self._model.project_logits_fp32(
                        hidden[:, -1, :]
                    ).float()
                    if not bool(torch.isfinite(logits).all()):
                        raise RuntimeError(
                            "persistent irwkv returned non-finite suffix logits"
                        )

            result = {
                "schema_version": "rwkv-lh.native-role-suffix-selection.v1",
                "candidate_labels": list(normalized),
                "prompt_token_count": len(prompt_ids),
                "prompt_token_ids": list(prompt_ids),
                "prompt_token_ids_scope": "full_prompt",
                "input_bos_token_count": len(prompt_ids) - len(self._tokenizer.encode(
                    str(prompt), truncation=False, add_special_tokens=False)),
                "selected_label": str(node[terminal]),
                "token_ids": selected_ids,
                "decisions": decisions,
            }
            identity = {
                **self._load_base_identity(),
                "feature_protocol": "rwkv-lh.native-role-suffix-selection.v1",
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "fresh_initial_state": True,
                "one_prompt_forward": True,
                "post_prompt_state_clones": 0,
                "token_sequence_exact": True,
                "expected_label_supplied": False,
                "teacher_forcing_invoked": False,
                "unrestricted_generation_invoked": False,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
                "downstream_decoder_trained": False,
            }
            self._last_identity = identity
            return result, identity

    def advance_hidden_suffix_views(
        self,
        text: str,
        *,
        suffix_start: int,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Mapping[str, Any], list[Any], int, int, int, Mapping[str, Any]]:
        """Advance once and pool unchanged hidden rows from an exact text suffix.

        The caller supplies a character boundary, but the method accepts it only
        when separately tokenizing the prefix and suffix reproduces the exact
        one-piece token sequence.  This exposes request-tail features without
        adding an artificial recurrent-state boundary.
        """

        if not str(text):
            raise ValueError("persistent irwkv state advance text must be non-empty")
        if not 0 < int(suffix_start) < len(str(text)):
            raise ValueError("persistent irwkv suffix boundary is invalid")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent irwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            value = str(text)
            token_ids = self._stateful_token_ids(value, continuation=continuation)
            prefix_ids = self._tokenizer.encode(
                value[:suffix_start],
                truncation=False,
                add_special_tokens=not continuation,
            )
            suffix_ids = self._tokenizer.encode(
                value[suffix_start:],
                truncation=False,
                add_special_tokens=False,
            )
            if not prefix_ids or not suffix_ids or token_ids != prefix_ids + suffix_ids:
                raise ValueError(
                    "persistent irwkv suffix boundary is not token additive"
                )
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor([token_ids], dtype=torch.long, device="cuda")
            hidden = self._model.forward_all_hidden(tokens, state)
            suffix_hidden = hidden[0, len(prefix_ids) :]
            features = {
                "mean": suffix_hidden.float().mean(dim=0).detach().float().cpu(),
                "last": suffix_hidden[-1].detach().float().cpu(),
            }
            if any(not bool(torch.isfinite(item).all()) for item in features.values()):
                raise RuntimeError(
                    "persistent irwkv returned non-finite suffix hidden views"
                )
            exported_state = [
                item.detach().cpu().contiguous().clone() for item in state
            ]
            identity = {
                **self._load_base_identity(),
                "feature_protocols": {
                    "mean": "rwkv-lh.irwkv-final-hidden-suffix-mean.v1",
                    "last": "rwkv-lh.irwkv-final-hidden-suffix-last.v1",
                },
                "extraction": "one-forward-exact-additive-suffix-mean-and-last",
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "one_forward": True,
                "token_sequence_exact": True,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return (
                features,
                exported_state,
                len(token_ids),
                len(prefix_ids),
                len(suffix_ids),
                identity,
            )

    def advance_hidden_global_suffix_views(
        self,
        text: str,
        *,
        suffix_start: int,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Mapping[str, Any], list[Any], int, int, int, Mapping[str, Any]]:
        """Advance once and expose global, exact-suffix, and final hidden views.

        The exact additive suffix check is identical to
        :meth:`advance_hidden_suffix_views`.  All returned tensors are direct
        reductions or copies of the same unmodified ``forward_all_hidden``
        result, so the authoritative recurrent state advances exactly once.
        """

        if not str(text):
            raise ValueError("persistent irwkv state advance text must be non-empty")
        if not 0 < int(suffix_start) < len(str(text)):
            raise ValueError("persistent irwkv suffix boundary is invalid")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent irwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            value = str(text)
            token_ids = self._stateful_token_ids(value, continuation=continuation)
            prefix_ids = self._tokenizer.encode(
                value[:suffix_start],
                truncation=False,
                add_special_tokens=not continuation,
            )
            suffix_ids = self._tokenizer.encode(
                value[suffix_start:],
                truncation=False,
                add_special_tokens=False,
            )
            if not prefix_ids or not suffix_ids or token_ids != prefix_ids + suffix_ids:
                raise ValueError(
                    "persistent irwkv suffix boundary is not token additive"
                )
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor([token_ids], dtype=torch.long, device="cuda")
            hidden = self._model.forward_all_hidden(tokens, state)
            suffix_hidden = hidden[0, len(prefix_ids) :]
            features = {
                "global_mean": hidden[0].float().mean(dim=0).detach().float().cpu(),
                "suffix_mean": suffix_hidden.float()
                .mean(dim=0)
                .detach()
                .float()
                .cpu(),
                "final_last": hidden[0, -1].detach().float().cpu(),
            }
            if any(not bool(torch.isfinite(item).all()) for item in features.values()):
                raise RuntimeError(
                    "persistent irwkv returned non-finite global/suffix hidden views"
                )
            exported_state = [
                item.detach().cpu().contiguous().clone() for item in state
            ]
            identity = {
                **self._load_base_identity(),
                "feature_protocols": {
                    "global_mean": "rwkv-lh.irwkv-final-hidden-mean.v1",
                    "suffix_mean": (
                        "rwkv-lh.irwkv-final-hidden-suffix-mean.v1"
                    ),
                    "final_last": "rwkv-lh.irwkv-final-hidden-last.v1",
                },
                "extraction": (
                    "one-forward-global-mean-exact-additive-suffix-mean-and-final-last"
                ),
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "one_forward": True,
                "token_sequence_exact": True,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return (
                features,
                exported_state,
                len(token_ids),
                len(prefix_ids),
                len(suffix_ids),
                identity,
            )

    def _load_direct_model(self, model_path: Path) -> Any:
        from .irwkv_direct import load_direct_model
        return load_direct_model(model_path, runtime_temp=self.settings.runtime_temp)

    def _token_rows(self, texts: Sequence[str]) -> list[list[int]]:
        self.load()
        assert self._tokenizer is not None
        rows = [
            self._tokenizer.encode(
                str(text),
                truncation=True,
                max_length=self.settings.max_tokens,
                add_special_tokens=True,
            )
            for text in texts
        ]
        if not rows or any(not row for row in rows):
            raise ValueError("persistent irwkv token rows must be non-empty")
        return rows

    def _extract_matrix(
        self,
        operation: str,
        texts: Sequence[str],
        *,
        codes: Sequence[str] = (),
        layer_index: int = -1,
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        if not texts or any(not str(text).strip() for text in texts):
            raise ValueError("persistent irwkv texts must be non-empty")
        import torch

        with self._lock, torch.inference_mode():
            token_rows = self._token_rows(texts)
            assert self._model is not None
            model = self._model
            layer_count = int(model.total_num_layers)
            resolved_layer = layer_index if layer_index >= 0 else layer_count + layer_index
            if not 0 <= resolved_layer < layer_count:
                raise ValueError("WKV layer index is outside the local model")
            code_token_ids: list[int] = []
            if codes:
                assert self._tokenizer is not None
                for code in codes:
                    encoded = self._tokenizer.encode(
                        f" {code}", add_special_tokens=False
                    )
                    if len(encoded) != 1:
                        raise ValueError(
                            f"constrained code is not one RWKV token: {code!r}"
                        )
                    code_token_ids.append(int(encoded[0]))
            buckets: dict[int, list[int]] = defaultdict(list)
            for index, row in enumerate(token_rows):
                buckets[len(row)].append(index)
            result_rows: list[Any | None] = [None] * len(token_rows)
            if operation in {"hidden_mean", "hidden_last"}:
                ordered = sorted(range(len(token_rows)), key=lambda index: len(token_rows[index]))
                for start in range(0, len(ordered), self.settings.batch_size):
                    batch_indices = ordered[start : start + self.settings.batch_size]
                    maximum = max(len(token_rows[index]) for index in batch_indices)
                    tokens = torch.full(
                        (len(batch_indices), maximum),
                        int(self._tokenizer.eos_token_id),
                        dtype=torch.long,
                        device="cuda",
                    )
                    for local_index, source_index in enumerate(batch_indices):
                        row = token_rows[source_index]
                        tokens[local_index, : len(row)] = torch.tensor(
                            row, dtype=torch.long, device="cuda"
                        )
                    state = self._new_state(len(batch_indices))
                    hidden = model.forward_all_hidden(tokens, state)
                    for local_index, source_index in enumerate(batch_indices):
                        token_count = len(token_rows[source_index])
                        if operation == "hidden_mean":
                            value = hidden[local_index, :token_count].float().mean(dim=0)
                        else:
                            value = hidden[local_index, token_count - 1].float()
                        result_rows[source_index] = value.detach().cpu()
                matrix = torch.stack(result_rows)
                if not bool(torch.isfinite(matrix).all()):
                    raise RuntimeError(
                        "persistent irwkv returned non-finite hidden features"
                    )
                protocols = {
                    "hidden_mean": (
                        "rwkv-lh.irwkv-final-hidden-mean.v1",
                        "final-layer-all-real-token-mean",
                    ),
                    "hidden_last": (
                        "rwkv-lh.irwkv-final-hidden-last.v1",
                        "final-layer-last-real-token",
                    ),
                }
                feature_protocol, extraction = protocols[operation]
                identity = {
                    **self._load_base_identity(),
                    "feature_protocol": feature_protocol,
                    "extraction": extraction,
                    "runtime": dict(self._runtime or {}),
                    "persistent_process": True,
                    "batch_padding": "right-pad-excluded-from-feature-pooling",
                }
                self._last_identity = identity
                return matrix, [len(row) for row in token_rows], identity
            for token_count in sorted(buckets):
                indices = buckets[token_count]
                for start in range(0, len(indices), self.settings.batch_size):
                    batch_indices = indices[start : start + self.settings.batch_size]
                    tokens = torch.tensor(
                        [token_rows[index] for index in batch_indices],
                        dtype=torch.long,
                        device="cuda",
                    )
                    state = self._new_state(len(batch_indices))
                    hidden = model.forward_all_hidden(tokens, state)
                    if operation == "wkv_statistics":
                        recurrent = state[1][resolved_layer].float()
                        values = torch.cat(
                            (
                                recurrent.mean(dim=-1).flatten(1),
                                recurrent.mean(dim=-2).flatten(1),
                                recurrent.diagonal(dim1=-2, dim2=-1).flatten(1),
                                recurrent.square().mean(dim=-1).sqrt().flatten(1),
                            ),
                            dim=1,
                        )
                    elif operation == "code_logits":
                        logits = model.project_logits_fp32(hidden[:, -1, :])
                        code_index = torch.tensor(
                            code_token_ids,
                            dtype=torch.long,
                            device=logits.device,
                        )
                        values = logits.index_select(1, code_index).float()
                    else:
                        raise ValueError(
                            f"unsupported persistent irwkv operation: {operation}"
                        )
                    values = values.detach().float().cpu()
                    for local_index, source_index in enumerate(batch_indices):
                        result_rows[source_index] = values[local_index]
            if any(row is None for row in result_rows):
                raise RuntimeError("persistent extraction left unfilled rows")
            matrix = torch.stack(result_rows)
            if not bool(torch.isfinite(matrix).all()):
                raise RuntimeError("persistent irwkv returned non-finite features")
        protocols = {
            "hidden_mean": (
                "rwkv-lh.irwkv-final-hidden-mean.v1",
                "final-layer-all-real-token-mean",
            ),
            "hidden_last": (
                "rwkv-lh.irwkv-final-hidden-last.v1",
                "final-layer-last-real-token",
            ),
            "wkv_statistics": (
                "rwkv-lh.irwkv-final-wkv-statistics.v1",
                "last-layer-row-column-diagonal-rms",
            ),
            "code_logits": (
                "rwkv-lh.irwkv-constrained-code-logits.v1",
                "last-token-fp32-lm-head-selected-codes",
            ),
        }
        feature_protocol, extraction = protocols[operation]
        identity = {
            **self._load_base_identity(),
            "feature_protocol": feature_protocol,
            "extraction": extraction,
            "runtime": dict(self._runtime or {}),
            "persistent_process": True,
        }
        self._last_identity = identity
        return matrix, [len(row) for row in token_rows], identity

    def extract_wkv_statistics(
        self,
        texts: Sequence[str],
        *,
        layer_index: int = -1,
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        return self._extract_matrix(
            "wkv_statistics", texts, layer_index=layer_index
        )

    def extract_last_hidden(
        self,
        texts: Sequence[str],
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        """Return final-layer last-real-token hidden vectors as FP32."""

        return self._extract_matrix("hidden_last", texts)

    def extract_hidden_pair(
        self,
        texts: Sequence[str],
    ) -> tuple[Any, Any, list[int], Mapping[str, Any]]:
        """Extract last-token and real-token-mean features from one forward."""

        if not texts or any(not str(text).strip() for text in texts):
            raise ValueError("persistent irwkv texts must be non-empty")
        import torch

        with self._lock, torch.inference_mode():
            token_rows = self._token_rows(texts)
            assert self._model is not None
            assert self._tokenizer is not None
            model = self._model
            ordered = sorted(
                range(len(token_rows)), key=lambda index: len(token_rows[index])
            )
            last_rows: list[Any | None] = [None] * len(token_rows)
            mean_rows: list[Any | None] = [None] * len(token_rows)
            for start in range(0, len(ordered), self.settings.batch_size):
                batch_indices = ordered[start : start + self.settings.batch_size]
                maximum = max(len(token_rows[index]) for index in batch_indices)
                tokens = torch.full(
                    (len(batch_indices), maximum),
                    int(self._tokenizer.eos_token_id),
                    dtype=torch.long,
                    device="cuda",
                )
                for local_index, source_index in enumerate(batch_indices):
                    row = token_rows[source_index]
                    tokens[local_index, : len(row)] = torch.tensor(
                        row, dtype=torch.long, device="cuda"
                    )
                # Fresh feature extraction must honor the explicitly pinned
                # immutable profile just like every other non-continuation
                # path.  Calling ``model.zero_state`` here silently bypasses
                # ``_initial_wkv_state`` and makes tuned/zero pair features
                # indistinguishable regardless of the registered profile.
                state = self._new_state(len(batch_indices))
                hidden = model.forward_all_hidden(tokens, state)
                for local_index, source_index in enumerate(batch_indices):
                    token_count = len(token_rows[source_index])
                    last_rows[source_index] = (
                        hidden[local_index, token_count - 1].float().detach().cpu()
                    )
                    mean_rows[source_index] = (
                        hidden[local_index, :token_count]
                        .float()
                        .mean(dim=0)
                        .detach()
                        .cpu()
                    )
            last = torch.stack(last_rows)
            mean = torch.stack(mean_rows)
            if not bool(torch.isfinite(last).all() and torch.isfinite(mean).all()):
                raise RuntimeError(
                    "persistent irwkv returned non-finite hidden features"
                )
        identity = {
            **self._load_base_identity(),
            "feature_protocols": {
                "last": "rwkv-lh.irwkv-final-hidden-last.v1",
                "mean": "rwkv-lh.irwkv-final-hidden-mean.v1",
            },
            "extraction": "one-forward-last-and-real-token-mean",
            "runtime": dict(self._runtime or {}),
            "persistent_process": True,
            "batch_padding": "right-pad-excluded-from-feature-pooling",
        }
        self._last_identity = identity
        return last, mean, [len(row) for row in token_rows], identity

    def extract_hidden_prefix_mean_pair(
        self,
        texts: Sequence[str],
        prefixes: Sequence[str],
    ) -> tuple[Any, Any, list[int], list[int], Mapping[str, Any]]:
        """Extract full and causal-prefix means from the same RWKV forward."""

        if (
            not texts
            or len(texts) != len(prefixes)
            or any(not str(text).strip() for text in texts)
            or any(not str(prefix).strip() for prefix in prefixes)
        ):
            raise ValueError("persistent irwkv text/prefix rows must align")
        import torch

        with self._lock, torch.inference_mode():
            token_rows = self._token_rows(texts)
            assert self._model is not None
            assert self._tokenizer is not None
            prefix_counts = []
            for text, prefix, full_tokens in zip(texts, prefixes, token_rows):
                if not str(text).startswith(str(prefix)):
                    raise ValueError("hidden prefix must be an exact text prefix")
                prefix_tokens = self._tokenizer.encode(
                    str(prefix),
                    truncation=False,
                    add_special_tokens=True,
                )
                common = 0
                for left, right in zip(prefix_tokens, full_tokens):
                    if left != right:
                        break
                    common += 1
                if common < 4 or common > len(full_tokens):
                    raise ValueError("hidden prefix token alignment is too short")
                prefix_counts.append(common)
            model = self._model
            ordered = sorted(
                range(len(token_rows)), key=lambda index: len(token_rows[index])
            )
            full_mean_rows: list[Any | None] = [None] * len(token_rows)
            prefix_mean_rows: list[Any | None] = [None] * len(token_rows)
            for start in range(0, len(ordered), self.settings.batch_size):
                batch_indices = ordered[start : start + self.settings.batch_size]
                maximum = max(len(token_rows[index]) for index in batch_indices)
                tokens = torch.full(
                    (len(batch_indices), maximum),
                    int(self._tokenizer.eos_token_id),
                    dtype=torch.long,
                    device="cuda",
                )
                for local_index, source_index in enumerate(batch_indices):
                    row = token_rows[source_index]
                    tokens[local_index, : len(row)] = torch.tensor(
                        row, dtype=torch.long, device="cuda"
                    )
                state = self._new_state(len(batch_indices))
                hidden = model.forward_all_hidden(tokens, state)
                for local_index, source_index in enumerate(batch_indices):
                    token_count = len(token_rows[source_index])
                    prefix_count = prefix_counts[source_index]
                    full_mean_rows[source_index] = (
                        hidden[local_index, :token_count]
                        .float()
                        .mean(dim=0)
                        .detach()
                        .cpu()
                    )
                    prefix_mean_rows[source_index] = (
                        hidden[local_index, :prefix_count]
                        .float()
                        .mean(dim=0)
                        .detach()
                        .cpu()
                    )
            full_mean = torch.stack(full_mean_rows)
            prefix_mean = torch.stack(prefix_mean_rows)
            if not bool(
                torch.isfinite(full_mean).all() and torch.isfinite(prefix_mean).all()
            ):
                raise RuntimeError(
                    "persistent irwkv returned non-finite prefix features"
                )
        identity = {
            **self._load_base_identity(),
            "feature_protocols": {
                "mean": "rwkv-lh.irwkv-final-hidden-mean.v1",
                "prefix_mean": "rwkv-lh.irwkv-causal-prefix-hidden-mean-lcp.v1",
            },
            "extraction": "one-forward-full-and-causal-prefix-token-mean",
            "runtime": dict(self._runtime or {}),
            "persistent_process": True,
            "batch_padding": "right-pad-excluded-from-feature-pooling",
            "prefix_alignment": "longest-common-token-prefix",
        }
        self._last_identity = identity
        return (
            full_mean,
            prefix_mean,
            [len(row) for row in token_rows],
            prefix_counts,
            identity,
        )

    def score_single_token_codes(
        self,
        prompts: Sequence[str],
        codes: Sequence[str],
    ) -> Any:
        if not codes or len(set(codes)) != len(codes):
            raise ValueError("constrained Router codes must be unique and non-empty")
        matrix, _, _ = self._extract_matrix("code_logits", prompts, codes=codes)
        return matrix


__all__ = ["PersistentIRWKVExtractor"]
