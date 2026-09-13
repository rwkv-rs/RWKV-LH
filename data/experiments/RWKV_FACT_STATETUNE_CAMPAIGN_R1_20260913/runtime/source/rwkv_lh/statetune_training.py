"""One registered StateTune optimizer for the current role protocols and Native backend."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import shutil
import time
from typing import Any, Callable, Mapping, Sequence

from rwkv_lh import statetune_core as core
from rwkv_lh.statetune_data import admit_dataset, sealed, _protocol

RUN_SCHEMA = "rwkv-lh.statetune-run.v1"


def production_model_identity(role: str, manifest: Mapping) -> str:
    """Direct native serving identifies the source checkpoint, not its container.

    Both hashes remain independently verified; legacy role services explicitly
    identify their serialized weights. This does not permit unbound aliases.
    """
    return manifest["source"]["sha256"] if role == "direct_actor" else manifest["output"]["weights_sha256"]


def validate_compatibility(registration: Mapping, compatibility: Mapping, result: Mapping, *, registration_sha256: str) -> None:
    core.require(result.get("passed") is True and result.get("optimizer_steps") == 0
                 and result.get("runtime_sha256") == registration["runtime"]["sha256"]
                 and result.get("registration_sha256") == registration_sha256
                 and compatibility.get("purpose") == "numerical_mechanism_only"
                 and compatibility.get("optimizer_steps") == 0
                 and all(compatibility.get(key) == registration[key]
                         for key in ("base_sha256", "context_tokens", "source_manifest_sha256")),
                 "Native compatibility evidence does not match this runtime/model/context")


def validate_optimizer(config: Mapping) -> None:
    expected = {"seed", "epochs", "gradient_accumulation", "learning_rate", "betas", "eps", "weight_decay",
                "max_grad_norm", "max_optimizer_steps", "max_seconds", "max_allocated_bytes"}
    core.require(set(config) == expected, "optimizer registration fields differ")
    core.require(type(config["seed"]) is int and 0 <= config["seed"] < 2**63, "invalid optimizer seed")
    for name in ("epochs", "gradient_accumulation", "max_optimizer_steps", "max_allocated_bytes"):
        core.require(type(config[name]) is int and config[name] > 0, "invalid registered " + name)
    for name in ("learning_rate", "eps", "max_grad_norm", "max_seconds", "weight_decay"):
        value = config[name]
        core.require(type(value) in (int, float) and math.isfinite(value)
                     and (value >= 0 if name == "weight_decay" else value > 0), "invalid registered " + name)
    core.require(isinstance(config["betas"], list) and len(config["betas"]) == 2
                 and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v < 1 for v in config["betas"]),
                 "invalid registered betas")


def initialize_state(model, reference: Mapping | None) -> None:
    import torch
    parameters = core.state_parameters(model, layers=model.layout.layers)
    if reference is None:
        with torch.no_grad():
            for parameter in parameters.values():
                parameter.zero_()
        return
    path = core.verify_file(reference["path"], reference["sha256"])
    values = torch.load(path, map_location="cpu", weights_only=True)
    core.require(isinstance(values, dict) and set(values) == set(parameters), "initial State key set differs")
    for name, value in values.items():
        core.require(isinstance(value, torch.Tensor) and value.dtype == torch.bfloat16
                     and value.shape == parameters[name].shape and bool(torch.isfinite(value).all()),
                     "initial portable State geometry/dtype/finiteness differs")
    with torch.no_grad():
        for name, value in values.items():
            parameters[name].copy_(value)


def optimize_state(model, samples: Sequence[Mapping], config: Mapping, *, context_tokens: int,
                   record: Callable[[dict], None], clock: Callable[[], float] = time.monotonic,
                   started_at: float | None = None) -> dict:
    """Independent batch-one samples; token-weighted accumulation, State-only AdamW.

    Time/resource budgets stop before the next optimizer step. They never imply
    that the registered epochs, role validation or Agent acceptance completed.
    """
    import torch
    validate_optimizer(config)
    core.require(bool(samples), "empty training set")
    started = clock() if started_at is None else started_at
    result = {"optimizer_steps": 0, "samples_seen": 0, "target_tokens_seen": 0,
              "epochs_completed": 0, "status": "running", "stop_reason": None}
    parameters = core.freeze_for_state_tuning(model, layers=model.layout.layers)
    frozen = {name: p._version for name, p in model.named_parameters() if name not in parameters}
    device = next(iter(parameters.values())).device
    generator = random.Random(config["seed"])
    torch.manual_seed(config["seed"])
    optimizer = torch.optim.AdamW(parameters.values(), lr=config["learning_rate"], betas=config["betas"],
        eps=config["eps"], weight_decay=config["weight_decay"], foreach=False)
    model.eval()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    def peak():
        return torch.cuda.max_memory_allocated(device) if device.type == "cuda" else 0

    def stop_reason(*, check_steps=True):
        if clock() - started >= config["max_seconds"]:
            return "wall_time_budget"
        if peak() > config["max_allocated_bytes"]:
            return "gpu_memory_budget"
        if check_steps and result["optimizer_steps"] >= config["max_optimizer_steps"]:
            return "optimizer_step_budget"
        return None

    def stopped(status, reason):
        result.update(status=status, stop_reason=reason, elapsed_seconds=clock() - started,
                      peak_allocated_bytes=peak())
        record({"event": "optimization_stopped", **result})
        return dict(result)

    try:
        # Validate the complete train split before any forward or update.
        for sample in samples:
            core.collate_samples([sample], context_tokens=context_tokens)
        for epoch in range(config["epochs"]):
            order = list(range(len(samples)))
            generator.shuffle(order)
            for offset in range(0, len(order), config["gradient_accumulation"]):
                reason = stop_reason()
                if reason:
                    return stopped("interrupted", reason)
                group = [samples[i] for i in order[offset:offset + config["gradient_accumulation"]]]
                target_count = sum(len(row["target_token_ids"]) for row in group)
                optimizer.zero_grad(set_to_none=True)
                weighted_loss = 0.0
                for sample in group:
                    reason = stop_reason()
                    if reason:
                        return stopped("interrupted", reason)
                    batch = core.collate_samples([sample], context_tokens=context_tokens)
                    logits = model(batch["input_ids"].to(device))
                    loss = core.target_cross_entropy(logits, batch["labels"].to(device))
                    core.require(bool(torch.isfinite(loss)), "nonfinite target loss")
                    weight = len(sample["target_token_ids"]) / target_count
                    (loss * weight).backward()
                    weighted_loss += float(loss.detach()) * weight
                    result["samples_seen"] += 1
                    result["target_tokens_seen"] += len(sample["target_token_ids"])
                    del logits, loss
                core.require(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in parameters.values()),
                             "State gradient is missing or nonfinite")
                core.require(all(not p.requires_grad and p.grad is None and p._version == frozen[name]
                                 for name, p in model.named_parameters() if name in frozen), "frozen base was mutated")
                grad_norm = torch.nn.utils.clip_grad_norm_(list(parameters.values()), config["max_grad_norm"],
                                                           error_if_nonfinite=True)
                reason = stop_reason()
                if reason:
                    return stopped("interrupted", reason)
                # The durable intent makes a process killed inside step explicitly
                # uncertain, instead of inventing a successful optimizer count.
                record({"event": "optimizer_step_started", **result, "next_step": result["optimizer_steps"] + 1})
                optimizer.step()
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                result["optimizer_steps"] += 1
                core.require(all(bool(torch.isfinite(p).all()) for p in parameters.values()), "nonfinite updated State")
                record({"event": "optimizer_step_completed", **result, "epoch": epoch + 1,
                        "loss": weighted_loss, "gradient_norm": float(grad_norm),
                        "elapsed_seconds": clock() - started, "peak_allocated_bytes": peak()})
                reason = stop_reason(check_steps=False)
                if reason:
                    return stopped("interrupted", reason)
            result["epochs_completed"] += 1
        return stopped("candidate", "registered_epochs_finished")
    except BaseException as exc:
        stopped("interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed", type(exc).__name__)
        raise
    finally:
        optimizer.zero_grad(set_to_none=True)


def _atomic_json(path: Path, value: Mapping) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def publish_state(model, output: Path, *, profile_id: str, model_artifact: str, engine_revision: str) -> dict:
    """Export portable BF16 once and verify it through the production loader."""
    import torch
    from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
        RWKV7InitialStateProfiles, RWKV7_STATE_PROFILE_MANIFEST_SCHEMA, _PROFILE_ID_PATTERN,
    )
    core.require(bool(_PROFILE_ID_PATTERN.fullmatch(profile_id)) and profile_id != "zero", "invalid candidate profile id")
    output = Path(output).absolute()
    state_path, profile_path = output / "candidate.pth", output / "STATE_PROFILES.json"
    core.require(not state_path.exists() and not profile_path.exists(), "candidate output already exists")
    layout = model.layout
    values = core.portable_state(model, layers=layout.layers, heads=layout.heads, head_size=layout.head_size)
    temporary = output / "candidate.pth.partial"
    with temporary.open("xb") as handle:
        torch.save(values, handle)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(state_path)
    state_sha = core.sha256_file(state_path)
    profile = {"schema_version": RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,
        "model_artifact": model_artifact, "model_revision": engine_revision, "default_profile": "zero",
        "profiles": [{"id": profile_id, "format": "rwkv-peft-time-state.v1",
                      "path": str(state_path), "sha256": state_sha}]}
    _atomic_json(profile_path, profile)
    profile_sha = core.sha256_file(profile_path)
    loaded = RWKV7InitialStateProfiles.load(str(profile_path), profile_sha, model_artifact=model_artifact,
        model_revision=engine_revision, total_num_layers=layout.layers, total_num_heads=layout.heads,
        layer_offset=0, num_layers=layout.layers, tp_size=1, tp_rank=0, num_heads=layout.heads,
        head_size=layout.head_size, device=torch.device("cpu"), dtype=torch.float32)
    expected = torch.stack([values[f"blocks.{i}.att.time_state"] for i in range(layout.layers)]).transpose(-2, -1).float()
    core.require(torch.equal(loaded.resolve(profile_id).wkv_state, expected), "candidate serving State layout differs")
    return {"state": {"path": str(state_path), "sha256": state_sha},
            "manifest": {"path": str(profile_path), "sha256": profile_sha},
            "profile_id": profile_id, "serving_loader_verified": True}


def run_training(registration_reference: Mapping, output: Path, *, source_root: Path) -> dict:
    """Verify immutable identities, train, export a candidate and retain every run."""
    registration = sealed(registration_reference)
    core.require(registration.get("schema_version") == RUN_SCHEMA, "unknown StateTune run registration")
    role = registration["role"]
    protocol, protocol_sha = _protocol(role)
    from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import _PROFILE_ID_PATTERN
    core.require(registration["input_protocol"] == protocol and registration["protocol_sha256"] == protocol_sha,
                 "registered role protocol differs")
    validate_optimizer(registration["optimizer"])
    core.require(isinstance(registration.get("run_id"), str)
                 and _PROFILE_ID_PATTERN.fullmatch(registration["run_id"]) is not None and registration["run_id"] != "zero",
                 "missing or unsafe run identity")
    for name in ("authorization", "evaluation_registration"):
        ref = registration[name]
        core.verify_file(ref["path"], ref["sha256"])
    evaluation = sealed(registration["evaluation_registration"])
    if role == "selector_intent":
        from rwkv_lh.statetune_evaluation import validate_plan
        validate_plan(evaluation)
    core.require(evaluation.get("role") == role and evaluation.get("regression_fingerprint") == registration["regression_fingerprint"]
                 and bool(evaluation.get("metrics")) and bool(evaluation.get("thresholds"))
                 and bool(evaluation.get("agent_metrics")) and bool(evaluation.get("retention_rule")),
                 "role/Agent evaluation metrics and retention rules must be pre-registered")
    output = Path(output).absolute()
    core.require(output == Path(registration["ledger_root"]).absolute() / registration["run_id"],
                 "run output must use its registered ledger and immutable run id")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {"schema_version": RUN_SCHEMA, "run_id": registration["run_id"], "role": role,
        "registration": dict(registration_reference), "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running", "optimizer_steps": 0, "optimizer_step_in_flight": None, "pid": os.getpid(),
        "evaluation_status": "not_run", "retained": False}
    shutil.copyfile(registration_reference["path"], output / "REGISTRATION.json")
    core.verify_file(output / "REGISTRATION.json", registration_reference["sha256"])
    log = output / "events.jsonl"

    def record(row):
        entry = {"at": datetime.now(timezone.utc).isoformat(), **row}
        with log.open("a") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        report.update({k: v for k, v in row.items() if k not in {"event", "next_step"}})
        if row["event"] == "optimizer_step_started":
            report["optimizer_step_in_flight"] = row["next_step"]
        elif row["event"] == "optimizer_step_completed":
            report["optimizer_step_in_flight"] = None
        report["last_event"] = row["event"]
        _atomic_json(output / "RESULT.json", report)

    record({"event": "run_started"})
    try:
        from rwkv_lh.statetune_native_runtime import verify_native_runtime, load_native_runtime, verify_loaded_libraries
        runtime_ref = registration["runtime"]
        runtime = verify_native_runtime(runtime_ref["path"], runtime_ref["sha256"], source_root=source_root,
                                        source_manifest_sha256=registration["source_manifest_sha256"])
        compatibility_ref = registration["compatibility_registration"]
        validate_compatibility(registration, sealed(compatibility_ref), sealed(registration["compatibility_result"]),
                               registration_sha256=compatibility_ref["sha256"])
        load_native_runtime(runtime)
        import torch
        from rwkv_lh.statetune_native_model import build
        from vllm.tokenizers.rwkv import RWKVTokenizer
        core.require(torch.cuda.device_count() == 1 and core.device_uuid_matches(
            str(torch.cuda.get_device_properties(0).uuid), registration["gpu_uuid"]), "training GPU identity differs")
        artifact = Path(runtime["model_artifact"]["path"])
        manifest = core.read_sealed_json(artifact / "manifest.json", runtime["model_artifact"]["manifest_sha256"])
        core.require(manifest["source"]["sha256"] == registration["base_sha256"], "registered base model differs")
        core.verify_file(artifact / "model.safetensors", manifest["output"]["weights_sha256"])
        tokenizer = RWKVTokenizer.from_pretrained(artifact)
        production_model_sha = production_model_identity(role, manifest)
        dataset, samples = admit_dataset(registration["dataset"], role=role,
            expected_regression=registration["regression_fingerprint"], model_sha256=production_model_sha,
            context_tokens=registration["context_tokens"], vocab_size=int(tokenizer.vocab_size), bos_token_id=int(tokenizer.bos_token_id))
        model = build({"model_artifact": str(artifact), "context_tokens": registration["context_tokens"],
                       "base": {"path": manifest["source"]["path"], "sha256": registration["base_sha256"]}})
        initial = registration["initial_state"]
        if initial is not None:
            core.require(initial["model_sha256"] == production_model_sha
                         and initial["input_protocol"] == protocol and initial["protocol_sha256"] == protocol_sha,
                         "unverified State reuse across model/protocol changes")
        initialize_state(model, initial)
        verify_loaded_libraries(runtime)
        record({"event": "identity_admitted", "model_sha256": production_model_sha,
                "weights_container_sha256": manifest["output"]["weights_sha256"],
                "dataset_sha256": registration["dataset"]["sha256"], "train_samples": len(samples),
                "regression_fingerprint": dataset["regression"]["fingerprint"], "layout": vars(model.layout)})
        result = optimize_state(model, samples, registration["optimizer"], context_tokens=registration["context_tokens"],
                                record=record, started_at=started)
        if result["optimizer_steps"]:
            published = publish_state(model, output, profile_id=registration["run_id"], model_artifact=str(artifact),
                                      engine_revision=runtime["engine"]["revision"])
            report.update(output_state=published["state"], output_profile=published["manifest"],
                          serving_loader_verified=published["serving_loader_verified"])
        verify_loaded_libraries(runtime)
        record({"event": "run_finished", **result,
                "evaluation_status": "pending_registered_evaluation" if result["optimizer_steps"] else "not_run",
                "retained": False})
    except BaseException as exc:
        record({"event": "run_failed", "status": "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed",
                "error_type": type(exc).__name__, "error": str(exc), "retained": False})
        raise
    finally:
        report.update(elapsed_seconds=time.monotonic() - started, log_sha256=core.sha256_file(log),
                      finished_at=datetime.now(timezone.utc).isoformat())
        _atomic_json(output / "RESULT.json", report)
    return report
