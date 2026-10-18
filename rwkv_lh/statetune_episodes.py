"""Frozen Executor episode datasets for chunked State-carry StateTune.

An episode is one complete Executor trajectory in the exact token order that
Native serving feeds one persistent State: each turn's input followed by the
decoder-exact action target. Nothing is truncated; episodes longer than the
training chunk are split at arbitrary token positions because the carried
State makes every split exact.

Supervision marks keep masked targets as input only, so the State still sees
everything the model saw while the loss covers only accepted actions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

from rwkv_lh.statetune_core import require, sha256_file, verify_file

EPISODE_FORMAT = "rwkv-lh.coder.executor-episode.v1"
COLLECTION_FORMAT = "rwkv-lh.coder.executor-episode-collection-manifest.v1"
DATASET_SCHEMA = "rwkv-lh.statetune-episode-dataset.v1"
ROW_SCHEMA = "rwkv-lh.statetune-episode-row.v1"
MASK_POLICY = "rwkv-lh.statetune-episode-mask.v1"


def supervision_marks(episode: Mapping, quality: Mapping | None) -> list[bool]:
    """Loss marks per target span under MASK_POLICY.

    Masked: package installation commands (environment specific), non-compact
    JSON (not decoder-exact style), and finish_work unless the episode ended
    with a finished delivery that passed the external generic check.
    """
    finished_ok = (episode["stop_reason"] == "finish_work_finished" and quality is not None
                   and quality.get("checked") is True and quality.get("generic_pass") is True)
    marks = []
    for flags in episode["target_flags"]:
        marks.append(not flags["package_install"] and flags["compact"] is True
                     and (flags["action"] != "finish_work" or finished_ok))
    return marks


def equal_chunk_starts(inputs: int, max_chunk_tokens: int) -> list[int]:
    """Fewest chunks of at most max_chunk_tokens inputs, sized as evenly as possible."""
    require(type(inputs) is int and inputs > 0 and type(max_chunk_tokens) is int and max_chunk_tokens > 0,
            "invalid chunk geometry")
    count = -(-inputs // max_chunk_tokens)
    return [index * inputs // count for index in range(count)]


def validate_episode(episode: Mapping, *, vocab_size: int, bos_token_id: int) -> None:
    require(episode.get("format") == EPISODE_FORMAT, "unknown episode format")
    tokens, spans = episode["token_ids"], episode["target_spans"]
    require(isinstance(tokens, list) and len(tokens) > 1 and tokens[0] == bos_token_id,
            "episode must start with BOS")
    require(all(type(t) is int and 0 <= t < vocab_size for t in tokens), "episode token outside vocabulary")
    require(len(spans) == len(episode["target_flags"]) and bool(spans), "target spans and flags differ")
    previous = 1
    for start, count in spans:
        require(type(start) is int and type(count) is int and count > 0 and start >= previous
                and start + count <= len(tokens), "target span outside episode or overlapping")
        previous = start + count


def _read_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _manifest_file(manifest: Mapping, name: str) -> str:
    files = manifest.get('files', {})
    require(isinstance(files, Mapping) and name in files, f"collection manifest does not seal {name}")
    return files[name]['sha256']


def freeze_episode_dataset(collection: Path, manifest_sha256: str, output: Path, *,
                           max_chunk_tokens: int, vocab_size: int, bos_token_id: int,
                           authorization: Mapping, audit_reference: Mapping) -> dict:
    """Freeze train episodes; existing evaluation sets are never regenerated.

    The separately sealed source audit binds protocol/tokenizer/model identities,
    similarity and coverage audits, exclusions, and any additional target masks.
    This is a training view of an authorized teacher collection, not a claim that
    those teacher actions were produced by RWKV or passed Agent acceptance.
    """
    from rwkv_lh.statetune_data import _protocol
    collection, output = Path(collection), Path(output)
    manifest_path = verify_file(collection / "MANIFEST.json", manifest_sha256)
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("format") == COLLECTION_FORMAT, "unknown collection manifest")
    episodes_path = verify_file(collection / "EPISODES.jsonl", _manifest_file(manifest, "EPISODES.jsonl"))
    quality_path = verify_file(collection / "QUALITY_FLAGS.jsonl", _manifest_file(manifest, "QUALITY_FLAGS.jsonl"))
    verify_file(authorization["path"], authorization["sha256"])
    audit = json.loads(verify_file(audit_reference['path'], audit_reference['sha256']).read_text())
    require(audit['collection_manifest_sha256'] == manifest_sha256
            and audit['episodes_sha256'] == sha256_file(episodes_path)
            and audit.get('training_eligible') is True, 'source audit does not admit this collection')
    require((audit['input_protocol'], audit['protocol_sha256']) == _protocol('project_executor'),
            'source audit protocol differs')
    require(audit['tokenizer_sha256'] == manifest['tokenizer_sha256']
            and bool(audit['coverage']) and bool(audit['similarity']), 'incomplete source audit')
    quality = {row["trajectory_line"]: row for row in _read_jsonl(quality_path)}
    rows = []
    for episode in _read_jsonl(episodes_path):
        validate_episode(episode, vocab_size=vocab_size, bos_token_id=bos_token_id)
        require(episode['trajectory_line'] not in manifest['eval_overlap_exclude_lines'], 'evaluation overlap in collection')
        require(episode['tokenizer_sha256'] == audit['tokenizer_sha256'], 'episode tokenizer differs')
        if episode['run_id'] in audit['excluded_episode_ids']:
            continue
        marks = supervision_marks(episode, quality.get(episode["trajectory_line"]))
        for index in audit['additional_mask_indices'].get(episode['run_id'], []):
            require(type(index) is int and 0 <= index < len(marks), 'audit mask outside episode')
            marks[index] = False
        require(any(marks), 'episode contains no supervised targets after audit')
        rows.append({"schema_version": ROW_SCHEMA, "episode_id": episode["run_id"],
                     "trajectory_line": episode["trajectory_line"], "task_id": episode["task_id"],
                     "token_ids": episode["token_ids"], "target_spans": episode["target_spans"],
                     "supervised": marks, "actions": [flags["action"] for flags in episode["target_flags"]],
                     "chunk_starts": equal_chunk_starts(len(episode["token_ids"]) - 1, max_chunk_tokens),
                     "source_collection_manifest_sha256": manifest_sha256})
    require(len({row["episode_id"] for row in rows}) == len(rows), "duplicate episode identity")
    require(len({row["task_id"] for row in rows}) == len(rows), "one task must not span splits")
    splits = {"TRAIN.jsonl": rows}
    output.mkdir(parents=True, exist_ok=False)
    files = []
    for name, split in splits.items():
        path = output / name
        with path.open("x") as handle:
            for row in split:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        files.append({"path": name, "sha256": sha256_file(path), "episodes": len(split),
                      **_counts(split)})
    result = {"schema_version": DATASET_SCHEMA, "row_schema": ROW_SCHEMA, "mask_policy": MASK_POLICY,
              "source_collection": {"path": str(collection), "manifest_sha256": manifest_sha256,
                                    "episodes_sha256": sha256_file(episodes_path),
                                    "quality_flags_sha256": sha256_file(quality_path)},
              "authorization": dict(authorization), "source_audit": dict(audit_reference),
              "split_algorithm": "audited train collection; existing fixed evaluations unchanged",
              "input_protocol": audit['input_protocol'], "protocol_sha256": audit['protocol_sha256'],
              "tokenizer_sha256": audit['tokenizer_sha256'], "model_sha256": audit['model_sha256'],
              "generator_sha256": sha256_file(__file__), "similarity": audit['similarity'], "coverage": audit['coverage'],
              "max_chunk_tokens": max_chunk_tokens, "vocab_size": vocab_size, "bos_token_id": bos_token_id,
              "files": files, "training_eligible": True}
    with (output / "MANIFEST.json").open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    return result


def validate_row(row: Mapping, *, context_tokens: int, vocab_size: int, bos_token_id: int) -> int:
    """Validate every token, mask and boundary before any model computation."""
    require(row.get('schema_version') == ROW_SCHEMA, 'unknown episode row')
    tokens, spans, marks = row['token_ids'], row['target_spans'], row['supervised']
    require(isinstance(tokens, list) and len(tokens) > 1 and tokens[0] == bos_token_id, 'episode must start with BOS')
    require(all(type(t) is int and 0 <= t < vocab_size for t in tokens), 'episode token outside vocabulary')
    require(len(marks) == len(spans) == len(row['actions']) and all(type(x) is bool for x in marks), 'row marks differ')
    previous, total = 1, 0
    for (start, count), mark in zip(spans, marks):
        require(type(start) is int and type(count) is int and count > 0 and start >= previous
                and start + count <= len(tokens), 'target span outside episode or overlapping')
        previous = start + count
        total += count if mark else 0
    require(total > 0, 'episode contains no supervised targets')
    starts = row['chunk_starts']
    require(isinstance(starts, list) and bool(starts) and starts[0] == 0
            and all(type(x) is int for x in starts), 'invalid chunk starts')
    require(all(0 < b - a <= context_tokens for a, b in zip(starts, starts[1:] + [len(tokens) - 1])),
            'chunk plan is unordered or exceeds context; truncation is forbidden')
    return total


def _counts(rows: Iterable[Mapping]) -> dict:
    tokens = targets = supervised = chunks = 0
    for row in rows:
        tokens += len(row["token_ids"])
        chunks += len(row["chunk_starts"])
        for (start, count), mark in zip(row["target_spans"], row["supervised"]):
            targets += count
            supervised += count if mark else 0
    return {"tokens": tokens, "target_tokens": targets, "supervised_target_tokens": supervised, "chunks": chunks}


def load_split(manifest_path: Path, manifest_sha256: str, split: str, *, context_tokens: int,
               vocab_size: int, bos_token_id: int, model_sha256: str, tokenizer_sha256: str) -> tuple[dict, list[dict]]:
    """Verified rows of one split; every chunk plan must fit the training context."""
    manifest = json.loads(verify_file(manifest_path, manifest_sha256).read_text())
    require(manifest.get("schema_version") == DATASET_SCHEMA and manifest.get("training_eligible") is True,
            "not an admitted episode dataset")
    require(manifest["vocab_size"] == vocab_size and manifest["bos_token_id"] == bos_token_id,
            "dataset tokenizer identity differs")
    from rwkv_lh.statetune_data import _protocol
    require((manifest['input_protocol'], manifest['protocol_sha256']) == _protocol('project_executor'), 'dataset protocol differs')
    require(manifest['model_sha256'] == model_sha256 and manifest['tokenizer_sha256'] == tokenizer_sha256,
            'dataset model/tokenizer differs')
    require(manifest['generator_sha256'] == sha256_file(__file__), 'dataset publisher differs')
    require(manifest["max_chunk_tokens"] <= context_tokens, "dataset chunks exceed the training context")
    entry = [row for row in manifest["files"] if row["path"] == split]
    require(len(entry) == 1, "unknown dataset split")
    rows = _read_jsonl(verify_file(Path(manifest_path).parent / split, entry[0]["sha256"]))
    for row in rows:
        validate_row(row, context_tokens=context_tokens, vocab_size=vocab_size, bos_token_id=bos_token_id)
        require(row["chunk_starts"] == equal_chunk_starts(len(row["token_ids"]) - 1, manifest["max_chunk_tokens"]),
                "row chunk plan differs from the dataset chunk policy")
    require(len(rows) == entry[0]["episodes"], "split row count differs")
    require(len({row['episode_id'] for row in rows}) == len(rows), 'duplicate episode identity')
    require(all(entry[0][key] == value for key, value in _counts(rows).items()), 'split counts differ')
    return manifest, rows


