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


def validate_episode_compatibility(registration, plan, result, *, registration_sha256):
    """Bind the exact carry validator's required stages and numerical limits."""
    from rwkv_lh.statetune_native_validation import validate_carry_plan
    validate_carry_plan(plan)
    core.require(result.get('passed') is True and result.get('optimizer_steps') == 0 and 'error' not in result
                 and result.get('registration_sha256') == registration_sha256
                 and result.get('runtime_sha256') == registration['runtime']['sha256']
                 and all(plan[key] == registration[key] for key in ('base_sha256', 'context_tokens', 'source_manifest_sha256'))
                 and 0 <= result['elapsed_seconds'] <= plan['max_seconds'], 'State-carry compatibility identity differs')
    stages = result['stages']
    core.require(stages[-1]['stage'] == 'complete' and stages[-1].get('binary_inventory_verified') is True,
                 'State-carry compatibility did not finish')
    for kind, plans, multiplier in (('chunked_serving_alignment', plan['alignment_plans'], 2),
                                    ('chunked_gradient', plan['gradient_plans'], 1),
                                    ('long_chunked_backward', plan['long_backward_plans'], 1)):
        rows = [s for s in stages if s['stage'] == kind]
        core.require(len(rows) == len(plans) * multiplier and all(r.get('comparison_passed') is True for r in rows),
                     'State-carry validation coverage differs')
        expected = sorted((p['tokens'], tuple(b - a for a, b in
            zip(p['chunk_starts'], p['chunk_starts'][1:] + [p['tokens']])), state)
            for p in plans for state in (('zero', 'nonzero') if multiplier == 2 else ('',)))
        actual = sorted((r['tokens'], tuple(r['chunk_sizes']), r.get('state', '') if multiplier == 2 else '') for r in rows)
        core.require(actual == expected, 'State-carry validation membership differs')
        for row in rows:
            core.require(any(row['tokens'] == p['tokens'] and row['chunk_sizes'] ==
                [b - a for a, b in zip(p['chunk_starts'], p['chunk_starts'][1:] + [p['tokens']])] for p in plans),
                'State-carry validation geometry differs')
            if kind == 'chunked_serving_alignment':
                core.require(max(row['chunk_max_logit_errors'] + row['chunk_max_state_errors']) <= plan['max_logit_error'],
                             'State-carry alignment failed')
            elif kind == 'chunked_gradient':
                core.require(row['gradient_relative_error'] <= plan['max_gradient_relative_error']
                             and row['loss_relative_error'] <= plan['max_loss_relative_error'], 'State-carry gradient failed')
            else:
                core.require(row['recompute_equal'] and row['all_layer_gradients_finite_nonzero']
                             and row['base_unchanged'] and row['state_unchanged']
                             and row['peak_allocated_bytes'] <= plan['max_allocated_bytes'], 'State-carry long backward failed')
    core.require(plan.get('episode_dataset') == registration['dataset'], 'real episode validation dataset differs')
    probes = [row for row in stages if row['stage'] == 'real_episode_backward']
    core.require(bool(plan.get('episode_probe_ids'))
                 and sorted(row['episode_id'] for row in probes) == sorted(plan['episode_probe_ids']),
                 'real episode validation coverage differs')
    core.require(all(row.get('comparison_passed') is True and row['optimizer_steps'] == 0
                 and row['dataset_sha256'] == registration['dataset']['sha256'] and row['recompute_equal']
                 and row['all_layer_gradients_finite_nonzero'] and row['base_unchanged'] and row['state_unchanged']
                 and row['peak_allocated_bytes'] <= plan['max_allocated_bytes'] for row in probes),
                 'real episode validation failed')


def production_model_identity(role: str, manifest: Mapping) -> str:
    """Direct native serving identifies the source checkpoint, not its container.

    Both hashes remain independently verified; legacy role services explicitly
    identify their serialized weights. This does not permit unbound aliases.
    """
    return manifest["source"]["sha256"] if role in ("direct_actor", "project_executor") else manifest["output"]["weights_sha256"]


def validate_compatibility(registration: Mapping, compatibility: Mapping, result: Mapping, *, registration_sha256: str) -> None:
    elapsed, limit = result.get("elapsed_seconds"), compatibility.get("max_seconds")
    stages = result.get("stages")
    core.require(result.get("passed") is True and result.get("optimizer_steps") == 0
                 and "error" not in result
                 and type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0
                 and type(limit) in (int, float) and math.isfinite(limit) and 0 < limit and elapsed <= limit
                 and isinstance(stages, list) and bool(stages) and isinstance(stages[-1], Mapping)
                 and stages[-1].get("stage") == "complete"
                 and result.get("runtime_sha256") == registration["runtime"]["sha256"]
                 and result.get("registration_sha256") == registration_sha256
                 and compatibility.get("purpose") == "numerical_mechanism_only"
                 and compatibility.get("optimizer_steps") == 0
                 and all(compatibility.get(key) == registration[key]
                         for key in ("base_sha256", "context_tokens", "source_manifest_sha256")),
                 "Native compatibility evidence does not match this runtime/model/context")
    from .statetune_native_validation import validate_result
    validate_result(compatibility, result)
    from .inference.native_weight_identity import identity_from_validation
    identity_from_validation(result)


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
                   started_at: float | None = None, episode_mode: bool = False) -> dict:
    """Independent batch-one samples; token-weighted accumulation, State-only AdamW.

    Time/resource budgets stop before the next optimizer step. They never imply
    that the registered epochs, role validation or Agent acceptance completed.
    """
    import torch
    from rwkv_lh.statetune_episodes import validate_row
    from rwkv_lh.statetune_state_carry import episode_chunks, state_carry_backward
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
            if episode_mode:
                # Dataset admission binds the actual tokenizer; this rechecks
                # spans, booleans and all boundaries for direct optimizer users.
                validate_row(sample, context_tokens=context_tokens,
                             vocab_size=getattr(model.layout, 'vocab', 65536), bos_token_id=0)
            else:
                core.collate_samples([sample], context_tokens=context_tokens)
        def targets(sample):
            return (sum(count for (_, count), mark in zip(sample['target_spans'], sample['supervised']) if mark)
                    if episode_mode else len(sample['target_token_ids']))
        for epoch in range(config["epochs"]):
            order = list(range(len(samples)))
            generator.shuffle(order)
            for offset in range(0, len(order), config["gradient_accumulation"]):
                reason = stop_reason()
                if reason:
                    return stopped("interrupted", reason)
                group = [samples[i] for i in order[offset:offset + config["gradient_accumulation"]]]
                target_count = sum(targets(row) for row in group)
                optimizer.zero_grad(set_to_none=True)
                weighted_loss = 0.0
                current_samples = []
                for sample in group:
                    reason = stop_reason()
                    if reason:
                        return stopped("interrupted", reason)
                    sample_targets = targets(sample)
                    weight = sample_targets / target_count
                    if episode_mode:
                        chunks = episode_chunks(sample['token_ids'], sample['target_spans'], sample['chunk_starts'],
                                                context_tokens=context_tokens, supervised=sample['supervised'])
                        carried = state_carry_backward(model, chunks, weight=weight)
                        core.require(carried['recompute_equal'], 'chunk boundary recomputation differs')
                        loss_value = carried['loss']
                        sample_id = sample['episode_id']
                        record({'event': 'episode_backward_completed', 'episode_id': sample_id,
                                'chunks': carried['chunks'], 'targets': carried['targets'], 'loss': loss_value})
                        del chunks
                    else:
                        batch = core.collate_samples([sample], context_tokens=context_tokens)
                        logits = model(batch["input_ids"].to(device))
                        loss = core.target_cross_entropy(logits, batch["labels"].to(device))
                        core.require(bool(torch.isfinite(loss)), "nonfinite target loss")
                        (loss * weight).backward()
                        loss_value, sample_id = float(loss.detach()), sample['sample_id']
                        del logits, loss
                    core.require(math.isfinite(loss_value), 'nonfinite target loss')
                    weighted_loss += loss_value * weight
                    current_samples.append({"sample_id": sample_id, "loss": loss_value, "target_tokens": sample_targets})
                    result["samples_seen"] += 1
                    result["target_tokens_seen"] += sample_targets
                bad_gradients = {name: "missing" if p.grad is None else "nonfinite"
                                 for name, p in parameters.items()
                                 if p.grad is None or not bool(torch.isfinite(p.grad).all())}
                if bad_gradients:
                    record({"event": "gradient_validation_failed", **result,
                            "failure_context": {"epoch": epoch + 1, "samples": current_samples,
                                                "parameters": bad_gradients}})
                    raise ValueError("State gradient is missing or nonfinite")
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


def save_failure_state(model, output: Path) -> dict:
    """Keep exact failed-run parameters for diagnosis, never a serving profile."""
    import torch
    path = Path(output) / "FAILURE_STATE.pth"
    values = {name: value.detach().cpu().clone()
              for name, value in core.state_parameters(model, layers=model.layout.layers).items()}
    with path.open("xb") as handle:
        torch.save(values, handle)
        handle.flush()
        os.fsync(handle.fileno())
    return {"path": str(path), "sha256": core.sha256_file(path), "purpose": "failure_diagnostic_only"}


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
    episode_mode = registration.get('dataset_kind') == 'executor_episodes'
    core.require(registration.get('dataset_kind') in (None, 'executor_episodes'), 'unknown dataset kind')
    core.require(not episode_mode or role == 'project_executor', 'episode training supports only Executor')
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
    elif role in ("project_executor",):
        from rwkv_lh.project_role_evaluation import validate_plan
        validate_plan(evaluation)
        core.require(evaluation['context_tokens'] == registration['context_tokens'],
                     'Project training and evaluation context must match')
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
    model = None
    try:
        from rwkv_lh.statetune_native_runtime import verify_native_runtime, load_native_runtime, verify_loaded_libraries
        runtime_ref = registration["runtime"]
        runtime = verify_native_runtime(runtime_ref["path"], runtime_ref["sha256"], source_root=source_root,
                                        source_manifest_sha256=registration["source_manifest_sha256"])
        compatibility_ref = registration["compatibility_registration"]
        compatibility_result = sealed(registration["compatibility_result"])
        if episode_mode:
            validate_episode_compatibility(registration, sealed(compatibility_ref), compatibility_result,
                                           registration_sha256=compatibility_ref['sha256'])
        else:
            validate_compatibility(registration, sealed(compatibility_ref), compatibility_result,
                                   registration_sha256=compatibility_ref["sha256"])
            from .inference.native_weight_identity import identity_from_validation
            report['serving_weight_identity'] = identity_from_validation(compatibility_result)
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
        if episode_mode:
            from rwkv_lh.statetune_episodes import load_split
            core.verify_file(artifact / 'rwkv_vocab_v20230424.txt', manifest['output']['vocab_sha256'])
            dataset, samples = load_split(registration['dataset']['path'], registration['dataset']['sha256'], 'TRAIN.jsonl',
                context_tokens=registration['context_tokens'], vocab_size=int(tokenizer.vocab_size),
                bos_token_id=int(tokenizer.bos_token_id), model_sha256=production_model_sha,
                tokenizer_sha256=manifest['output']['vocab_sha256'])
        else:
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
                "regression_fingerprint": registration['regression_fingerprint'], "layout": vars(model.layout)})
        result = optimize_state(model, samples, registration["optimizer"], context_tokens=registration["context_tokens"],
                                record=record, started_at=started, episode_mode=episode_mode)
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
        if model is not None:
            try:
                record({"event": "failure_state_saved", "failure_state": save_failure_state(model, output)})
            except Exception as snapshot_error:
                # Preserve the original training error even if disk capture fails.
                record({"event": "failure_state_save_failed", "failure_state_error": str(snapshot_error)})
        record({"event": "run_failed", "status": "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed",
                "error_type": type(exc).__name__, "error": str(exc), "retained": False})
        raise
    finally:
        report.update(elapsed_seconds=time.monotonic() - started, log_sha256=core.sha256_file(log),
                      finished_at=datetime.now(timezone.utc).isoformat())
        _atomic_json(output / "RESULT.json", report)
    return report
