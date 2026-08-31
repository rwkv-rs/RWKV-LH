#!/usr/bin/env python3
"""Freeze the 6000-family exact-tool coverage collection plan.

This script creates fixtures only.  It never calls a model and never emits a
training row.  A later runner must preserve the 13.3B Executor response before
parsing and admit only Harness/verifier-passing attempts.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.protocol import (
    ABSTAIN_LABEL,
    EXACT_TOOL_LABELS,
    selector_menu_digest,
)
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import TaskAction

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "datasets" / "rwkv_lh_exact_tool_coverage_v1"
SCHEMA = "rwkv-lh.exact-tool-coverage-plan.v1"
CASE_SCHEMA = "rwkv-lh.exact-tool-coverage-case.v1"
SPLIT_COUNTS = {"train": 240, "dev": 30, "test": 30}
TOTAL_PER_CLASS = sum(SPLIT_COUNTS.values())
PREFLIGHT_PER_CLASS = 2
DEDUP_ALGORITHM = "utf8-byte-5gram-cosine.v1"
DEDUP_THRESHOLD = 0.95
PROTOCOL = (
    ROOT
    / "data"
    / "experiments"
    / "LOCAL_DUAL_MODEL_STATE_PROFILES_V1_20260828"
    / "SELECTOR_COVERAGE_COLLECTION_V1.md"
)

README = """# RWKV-LH Exact-Tool Coverage v1

This is a frozen collection plan, not a training dataset.

- 20 labels × 300 independent semantic families = 6000 cases.
- Family split is fixed at train/dev/test = 240/30/30 per label using the
  registered SHA-256 modulo rule.
- Fixtures contain mechanical ground truth and operation-specific verifiers.
- No model has been called and no raw RWKV output is present here.
- A later runner must commit raw 13.3B Executor output before parsing and may
  promote only Harness/verifier-passing attempts into the Selector pool.
"""

SPLIT_DOMAINS = {
    "preflight": (
        "alder",
        "brass",
        "clover",
        "driftwood",
        "elm",
        "fjord",
        "ginger",
        "heath",
        "indigo",
        "jasper",
    ),
    "train": (
        "cedar",
        "harbor",
        "meadow",
        "cobalt",
        "juniper",
        "willow",
        "ember",
        "granite",
        "orchard",
        "lighthouse",
    ),
    "dev": (
        "quartz",
        "tundra",
        "saffron",
        "mariner",
        "topaz",
        "rainfall",
        "canyon",
        "lotus",
        "citadel",
        "seabird",
    ),
    "test": (
        "aster",
        "birch",
        "delta",
        "iris",
        "lumen",
        "nimbus",
        "pebble",
        "raven",
        "solace",
        "zephyr",
    ),
}
OBJECTS = (
    "ledger",
    "catalog",
    "release",
    "archive",
    "matrix",
    "workshop",
    "registry",
    "notebook",
    "inventory",
    "briefing",
    "shipment",
    "timeline",
    "manifest",
    "playbook",
    "snapshot",
)
QUALIFIERS = (
    "audited",
    "bounded",
    "canonical",
    "dated",
    "explicit",
    "frozen",
    "grounded",
    "isolated",
    "literal",
    "measured",
    "scoped",
    "verified",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    if len(raw) < n:
        return Counter({raw: 1})
    return Counter(raw[index : index + n] for index in range(len(raw) - n + 1))


def _cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    numerator = sum(left[item] * right[item] for item in left.keys() & right.keys())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _split_for_family(family_id: str) -> str:
    bucket = int(hashlib.sha256(family_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "dev"
    if bucket == 1:
        return "test"
    return "train"


def _family_ids(label: str) -> dict[str, list[str]]:
    selected = {split: [] for split in SPLIT_COUNTS}
    counter = 0
    slug = label.replace("_", "-").lower()
    while any(len(selected[split]) < limit for split, limit in SPLIT_COUNTS.items()):
        family_id = f"ETCV1-{slug}-{counter:05d}"
        split = _split_for_family(family_id)
        if len(selected[split]) < SPLIT_COUNTS[split]:
            selected[split].append(family_id)
        counter += 1
    return selected


def _file(path: str, content: str) -> dict[str, Any]:
    raw = content.encode("utf-8")
    return {
        "path": path,
        "content_utf8": content,
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
    }


def _progress(*, final: bool = False) -> dict[str, Any]:
    return {
        "completed_stage_count": 2 if final else 0,
        "action_index": 2 if final else 0,
        "succeeded_operations": ["write_file", "read_file"] if final else [],
        "failed_operations": [],
        "protocol_rejection_count": 0,
    }


def _surface(label: str, split: str, index: int, family_id: str) -> dict[str, str]:
    domains = SPLIT_DOMAINS[split]
    label_index = EXACT_TOOL_LABELS.index(label)
    domain = domains[(index * 7 + label_index * 3) % len(domains)]
    obj = OBJECTS[(index * 11 + label_index * 5) % len(OBJECTS)]
    qualifier = QUALIFIERS[(index * 5 + label_index * 7) % len(QUALIFIERS)]
    suffix = hashlib.sha256(family_id.encode("utf-8")).hexdigest()[:10]
    stem = f"{domain}-{obj}-{qualifier}-{index:03d}-{suffix}"
    return {
        "domain": domain,
        "object": obj,
        "qualifier": qualifier,
        "stem": stem,
        "ticket": f"ticket-{1000 + index}-{suffix[:6]}",
    }


def _ordinary_case(
    label: str,
    split: str,
    index: int,
    family_id: str,
) -> tuple[str, str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    s = _surface(label, split, index, family_id)
    stem = s["stem"]
    workspace: dict[str, Any] = {"directories": [], "files": []}
    args: dict[str, Any]
    verifier: dict[str, Any]

    if label == "list_directory":
        root = f"inventory/{stem}"
        workspace = {
            "directories": [root, f"{root}/nested"],
            "files": [
                _file(f"{root}/alpha.txt", f"{s['ticket']} alpha\n"),
                _file(f"{root}/nested/beta.json", '{"ready":true}\n'),
            ],
        }
        objective = f"List bounded recursive path, type, and size metadata under {root}; do not read file contents."
        args = {"path": root, "recursive": True, "max_entries": 100}
        verifier = {"type": "directory_metadata_exact", "root": root, "entry_count": 3}
    elif label == "search_text":
        root = f"corpus/{stem}"
        marker = f"NEEDLE_{s['ticket'].replace('-', '_').upper()}"
        workspace = {
            "directories": [root],
            "files": [
                _file(f"{root}/notes.md", f"preface\n{marker} primary\nclosing\n"),
                _file(f"{root}/log.txt", f"header\nquiet\n{marker} secondary\n"),
                _file(f"{root}/clean.txt", "no matching marker here\n"),
            ],
        }
        objective = f"Find every literal {marker} line under {root} and return bounded ordered locators without mutating files."
        args = {
            "pattern": marker,
            "path": root,
            "mode": "literal",
            "case_sensitive": True,
            "recursive": True,
            "max_results": 100,
        }
        verifier = {
            "type": "search_text_exact",
            "ordered_locators": [f"{root}/log.txt:3", f"{root}/notes.md:2"],
            "workspace_mutation_count": 0,
        }
    elif label == "read_file":
        path = f"inputs/{stem}.txt"
        content = f"{s['qualifier']} {s['domain']} record\nreference={s['ticket']}\n"
        workspace["files"] = [_file(path, content)]
        objective = (
            f"Observe the exact complete UTF-8 contents of {path} from byte zero."
        )
        args = {"path": path, "start_byte": 0, "max_tokens": 4096}
        verifier = {
            "type": "read_file_exact",
            "path": path,
            "content_sha256": _sha256_bytes(content.encode()),
        }
    elif label == "read_json":
        path = f"records/{stem}.json"
        value = {"ticket": s["ticket"], "ready": True, "rank": index + 1}
        content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        workspace["files"] = [_file(path, content)]
        objective = (
            f"Parse {path} and observe its complete canonical compact JSON value."
        )
        args = {"path": path, "start_byte": 0, "max_tokens": 4096}
        verifier = {"type": "read_json_canonical_exact", "path": path, "value": value}
    elif label == "file_digest":
        path = f"artifacts/{stem}.dat"
        content = (
            f"artifact {s['ticket']}\n{s['domain']} {s['object']} {s['qualifier']}\n"
        )
        workspace["files"] = [_file(path, content)]
        objective = f"Observe only the SHA-256 digest and byte size of {path}."
        args = {"path": path}
        verifier = {
            "type": "file_digest_exact",
            "path": path,
            "sha256": _sha256_bytes(content.encode()),
            "bytes": len(content.encode()),
        }
    elif label == "write_file":
        path = f"outputs/{stem}.txt"
        content = f"completed {s['ticket']}\n"
        objective = f"Create {path} with exactly the UTF-8 text {content!r}."
        args = {
            "path": path,
            "content": content,
            "create_parents": True,
            "overwrite": True,
        }
        verifier = {"type": "file_content_exact", "path": path, "content_utf8": content}
    elif label == "write_json":
        path = f"state/{stem}.json"
        value = {"ticket": s["ticket"], "status": "ready", "sequence": index}
        workspace["files"] = [_file(path, '{"obsolete":true,"sequence":-1}\n')]
        objective = f"Replace {path} with the complete JSON value for {s['ticket']}, status ready, sequence {index}; remove old keys."
        args = {"path": path, "value": value, "create_parents": True, "overwrite": True}
        verifier = {"type": "json_value_exact", "path": path, "value": value}
    elif label == "patch_json":
        path = f"config/{stem}.json"
        before = {"ticket": s["ticket"], "status": "pending", "keep": s["domain"]}
        workspace["files"] = [_file(path, json.dumps(before) + "\n")]
        objective = f"Change only top-level status in {path} from pending to ready while preserving every other key."
        args = {"path": path, "updates": {"status": "ready"}}
        verifier = {
            "type": "json_patch_exact",
            "path": path,
            "before": before,
            "updates": {"status": "ready"},
        }
    elif label == "replace_text":
        path = f"docs/{stem}.txt"
        before = f"ticket {s['ticket']}\nstate=pending\nowner={s['domain']}\n"
        workspace["files"] = [_file(path, before)]
        objective = f"Replace the exact first occurrence of state=pending with state=ready in {path}; preserve all other bytes."
        args = {"path": path, "old": "state=pending", "new": "state=ready", "count": 1}
        verifier = {
            "type": "replace_text_exact",
            "path": path,
            "before": before,
            "after": before.replace("state=pending", "state=ready", 1),
        }
    elif label == "remove_line":
        path = f"settings/{stem}.env"
        line = f"REMOVE_{s['ticket'].replace('-', '_').upper()}=1"
        before = f"KEEP=1\n{line}\nOWNER={s['domain']}\n"
        workspace["files"] = [_file(path, before)]
        objective = f"Remove the one complete line {line} from {path}; retain every other line exactly."
        args = {"path": path, "text": line, "all": False}
        verifier = {
            "type": "remove_line_exact",
            "path": path,
            "removed_line": line,
            "after": f"KEEP=1\nOWNER={s['domain']}\n",
        }
    elif label == "append_file":
        path = f"logs/{stem}.log"
        before = f"opened {s['ticket']}\n"
        appended = f"closed {s['qualifier']} {s['object']}\n"
        workspace["files"] = [_file(path, before)]
        objective = f"Append exactly {appended!r} once to existing {path}, preserving all current bytes."
        args = {"path": path, "content": appended}
        verifier = {
            "type": "append_once_exact",
            "path": path,
            "before": before,
            "appended": appended,
            "after": before + appended,
        }
    elif label == "make_directory":
        path = f"deliveries/{stem}/reports"
        objective = f"Create the directory {path}, including missing parents, without creating files."
        args = {"path": path, "parents": True}
        verifier = {"type": "directory_exists_exact", "path": path, "file_count": 0}
    elif label == "copy_file":
        source = f"templates/{stem}.ini"
        destination = f"generated/{stem}.ini"
        content = f"ticket={s['ticket']}\nmode={s['qualifier']}\n"
        workspace["files"] = [_file(source, content)]
        objective = (
            f"Copy the exact bytes of {source} to {destination}; retain the source."
        )
        args = {"source": source, "destination": destination}
        verifier = {
            "type": "copy_exact",
            "source": source,
            "destination": destination,
            "sha256": _sha256_bytes(content.encode()),
        }
    elif label == "move_file":
        source = f"incoming/{stem}.txt"
        destination = f"archive/{stem}.txt"
        content = f"move {s['ticket']} {s['object']}\n"
        workspace["files"] = [_file(source, content)]
        objective = f"Move {source} to {destination}; preserve exact bytes and leave no source path."
        args = {"source": source, "destination": destination}
        verifier = {
            "type": "move_exact",
            "source": source,
            "destination": destination,
            "sha256": _sha256_bytes(content.encode()),
        }
    elif label == "delete_file":
        path = f"stale/{stem}.tmp"
        sibling = f"stale/{stem}.keep"
        content = f"stale {s['ticket']}\n"
        sibling_content = f"retain {s['ticket']}\n"
        workspace["files"] = [
            _file(path, content),
            _file(sibling, sibling_content),
        ]
        objective = f"Delete only the explicitly scoped file {path}; do not alter sibling paths."
        args = {"path": path, "missing_ok": False, "recursive": False}
        verifier = {
            "type": "path_absent_siblings_unchanged",
            "path": path,
            "sibling_path": sibling,
            "sibling_sha256": _sha256_bytes(sibling_content.encode()),
        }
    elif label == "bind_evidence":
        path = f"sources/{stem}.md"
        lines = [f"line {number} {s['ticket']} {s['domain']}" for number in range(1, 9)]
        content = "\n".join(lines) + "\n"
        workspace["files"] = [_file(path, content)]
        objective = f"Bind lines 3 through 5 of {path} as exact evidence with their source locator."
        args = {
            "path": path,
            "start_line": 3,
            "end_line": 5,
            "source": s["ticket"],
            "max_tokens": 2048,
        }
        verifier = {
            "type": "evidence_span_exact",
            "path": path,
            "start_line": 3,
            "end_line": 5,
            "quote": "\n".join(lines[2:5]),
        }
    elif label == "check_command":
        path = f"checks/{stem}.txt"
        content = f"verified {s['ticket']}\n"
        workspace["files"] = [_file(path, content)]
        code = f"from pathlib import Path; assert Path({path!r}).read_text(encoding='utf-8') == {content!r}"
        objective = f"Run a read-only Python assertion that {path} contains its registered exact text."
        args = {
            "argv": ["python", "-c", code],
            "cwd": ".",
            "timeout": 30.0,
            "env": {},
            "expected_exit_code": 0,
        }
        verifier = {
            "type": "read_only_command_exact",
            "expected_exit_code": 0,
            "workspace_mutation_count": 0,
        }
    elif label == "run_command":
        path = f"generated/{stem}.txt"
        content = f"generated {s['ticket']}\n"
        code = f"from pathlib import Path; p=Path({path!r}); p.parent.mkdir(parents=True, exist_ok=True); p.write_text({content!r}, encoding='utf-8')"
        objective = f"Run the provided mutating Python generator to create {path} with its registered exact content."
        args = {
            "argv": ["python", "-c", code],
            "cwd": ".",
            "timeout": 30.0,
            "env": {},
            "expected_exit_code": 0,
        }
        verifier = {
            "type": "mutating_command_effect_exact",
            "expected_exit_code": 0,
            "path": path,
            "content_utf8": content,
        }
    else:  # pragma: no cover - caller handles final_answer/ABSTAIN
        raise ValueError(f"unsupported fixture label: {label}")

    request = f"For {s['ticket']}, complete one {s['qualifier']} {s['domain']} {s['object']} workspace step. {objective}"
    return request, objective, workspace, args, verifier


def _special_case(
    label: str,
    split: str,
    index: int,
    family_id: str,
) -> tuple[str, str, dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    s = _surface(label, split, index, family_id)
    if label == "final_answer":
        path = f"completed/{s['stem']}.txt"
        content = f"verified completion {s['ticket']}\n"
        evidence_sha256 = _sha256_bytes(content.encode())
        objective = (
            f"All work for {s['ticket']} is complete: {path} was observed at SHA-256 "
            f"{evidence_sha256}. Return the concise final answer without another tool call."
        )
        request = (
            f"Create and verify the {s['qualifier']} {s['domain']} {s['object']} "
            f"result recorded as {path} for {s['ticket']}, then report completion."
        )
        workspace = {"directories": [], "files": [_file(path, content)]}
        verifier = {
            "type": "final_text_nonempty_byte_exact",
            "required_facts": [s["ticket"], "complete"],
            "evidence_path": path,
            "evidence_sha256": evidence_sha256,
        }
        return request, objective, workspace, {"operation": "final_answer"}, verifier

    remote_capabilities = (
        "private SQL connector",
        "authenticated mail sender",
        "calendar scheduling API",
        "remote browser session",
        "cloud virtual-machine console",
        "payment settlement gateway",
        "mobile-device control plane",
        "private issue-tracker connector",
        "remote OCR service",
        "warehouse robotics controller",
        "customer-records API",
        "external image generator",
    )
    ambiguous_fields = (
        "status",
        "owner",
        "retention date",
        "release channel",
        "checksum",
        "priority",
        "destination",
        "approval flag",
        "encoding",
        "version",
        "access mode",
        "display title",
    )
    destructive_scopes = (
        "every sibling workspace",
        "the parent of the allowed workspace",
        "all mounted project roots",
        "every matching user directory",
        "the complete shared archive",
        "all system temporary paths",
        "every repository checkout",
        "the unbounded cache hierarchy",
        "all connected storage volumes",
        "the entire build history",
        "every remote backup",
        "all tenant workspaces",
    )
    missing_references = (
        "the report mentioned yesterday",
        "the latest unnamed attachment",
        "that earlier configuration",
        "the referenced source file",
        "the prior result document",
        "the current manifest",
        "the approved notebook",
        "the expected release note",
        "the relevant audit record",
        "the canonical snapshot",
        "the selected inventory file",
        "the verified evidence page",
    )
    conflicts = (
        ("remain byte-for-byte present", "be deleted before this stage ends"),
        ("retain its current contents", "be overwritten with unrelated text"),
        ("stay at its current path", "be moved away with no source left"),
        ("remain an empty file", "receive an appended non-empty record"),
        ("keep its current SHA-256", "have one line removed"),
        ("remain absent", "be created before this same stage completes"),
        ("stay valid JSON", "be replaced by malformed non-JSON bytes"),
        ("preserve every key", "delete one existing key"),
        ("remain read-only and unchanged", "be mutated by a command"),
        ("retain the source path", "move it and leave no source path"),
        ("keep its exact line count", "append a new complete line"),
        ("remain a directory", "be replaced by a regular file"),
    )
    variant = index % len(remote_capabilities)
    resource = f"boundary/{s['stem']}"
    rules = (
        (
            "unsupported_capability",
            (
                f"Use the {remote_capabilities[variant]} to change remote resource "
                f"{resource} for {s['ticket']}; that external capability is absent from "
                "the frozen local tool menu."
            ),
            (
                f"No registered operation can access the required "
                f"{remote_capabilities[variant]} or observe remote resource {resource}; "
                "select no operation."
            ),
        ),
        (
            "ambiguous_target",
            (
                f"Change the {ambiguous_fields[variant]} for {s['ticket']} in either "
                f"{resource}-alpha.json or {resource}-beta.json, but the request provides "
                "neither which target nor the desired value."
            ),
            (
                f"Two distinct targets and an unspecified {ambiguous_fields[variant]} "
                f"value leave {resource} without one mechanically determined operation."
            ),
        ),
        (
            "unsafe_unscoped_mutation",
            (
                f"For {s['ticket']}, recursively erase {destructive_scopes[variant]} plus "
                f"anything resembling {resource}, without an authorized bounded root."
            ),
            (
                f"The requested destructive scope, {destructive_scopes[variant]}, is "
                f"outside a single explicit workspace target for {resource}; select no "
                "operation."
            ),
        ),
        (
            "missing_observable_reference",
            (
                f"Read {missing_references[variant]} for {s['ticket']} and summarize its "
                f"{s['domain']} details, although no path, locator, or prior observation "
                f"identifies {resource} or any file."
            ),
            (
                f"The phrase {missing_references[variant]!r} has no observable locator "
                f"for {resource}; choosing a read operation would invent its target."
            ),
        ),
        (
            "irreconcilable_effects",
            (
                f"In one indivisible stage for {s['ticket']}, require {resource}.dat to "
                f"{conflicts[variant][0]} and also to {conflicts[variant][1]}, with no "
                "priority or resolution rule."
            ),
            (
                f"The two simultaneous postconditions for {resource}.dat conflict: it "
                f"must {conflicts[variant][0]} yet also {conflicts[variant][1]}."
            ),
        ),
    )
    rule_id, request, objective = rules[index % len(rules)]
    verifier = {
        "type": "mechanical_abstain_boundary",
        "rule_id": rule_id,
        "rule_input_sha256": _sha256_bytes(
            _canonical({"request": request, "objective": objective}).encode()
        ),
        "raw_output_applicable": False,
    }
    return request, objective, {"directories": [], "files": []}, None, verifier


def _case(label: str, split: str, index: int, family_id: str) -> dict[str, Any]:
    if label in {"final_answer", ABSTAIN_LABEL}:
        request, objective, workspace, execution, verifier = _special_case(
            label, split, index, family_id
        )
    else:
        request, objective, workspace, arguments, verifier = _ordinary_case(
            label, split, index, family_id
        )
        execution = {"operation": label, "expected_arguments": arguments}
    progress = _progress(final=label == "final_answer")
    selector_projection = {
        "task_request": request,
        "stage_objective": objective,
        "stage_role": "completion" if label == "final_answer" else "work",
        "progress": progress,
    }
    case_id = f"ETC-{EXACT_TOOL_LABELS.index(label):02d}-{split.upper()}-{index:03d}"
    return {
        "schema_version": CASE_SCHEMA,
        "case_id": case_id,
        "semantic_family_id": family_id,
        "split": split,
        "label": label,
        "selector_projection": selector_projection,
        "selector_projection_sha256": _sha256_bytes(
            _canonical(selector_projection).encode("utf-8")
        ),
        "workspace": workspace,
        "executor_contract": execution,
        "verifier": verifier,
        "collection_status": "not_run",
        "raw_rwkv_output_present": False,
    }


def _jsonl_bytes(rows: list[Mapping[str, Any]]) -> bytes:
    return ("".join(_canonical(dict(row)) + "\n" for row in rows)).encode("utf-8")


def _validate_fixture_paths(row: Mapping[str, Any]) -> None:
    candidates: list[str] = []
    workspace = row["workspace"]
    candidates.extend(str(path) for path in workspace["directories"])
    candidates.extend(str(item["path"]) for item in workspace["files"])
    execution = row["executor_contract"]
    if isinstance(execution, Mapping):
        arguments = execution.get("expected_arguments")
        if isinstance(arguments, Mapping):
            candidates.extend(
                str(arguments[name])
                for name in ("path", "source", "destination", "cwd")
                if name in arguments
            )
    for value in candidates:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise AssertionError(
                f"fixture path must remain workspace-relative: {value!r}"
            )


def _similarity_audit(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {
        label: [] for label in EXACT_TOOL_LABELS
    }
    for row in rows:
        grouped[str(row["label"])].append(row)
    by_label: dict[str, dict[str, Any]] = {}
    total_kept = 0
    global_maximum = 0.0
    for label in EXACT_TOOL_LABELS:
        kept_vectors: list[Counter[bytes]] = []
        maximum = 0.0
        for row in grouped[label]:
            vector = _byte_ngrams(_canonical(row["selector_projection"]))
            duplicate = False
            for existing in kept_vectors:
                score = _cosine(vector, existing)
                maximum = max(maximum, score)
                if score >= DEDUP_THRESHOLD:
                    duplicate = True
                    break
            if not duplicate:
                kept_vectors.append(vector)
        kept = len(kept_vectors)
        total_kept += kept
        global_maximum = max(global_maximum, maximum)
        by_label[label] = {
            "input": len(grouped[label]),
            "kept": kept,
            "dropped": len(grouped[label]) - kept,
            "maximum_compared_similarity": round(maximum, 12),
        }
    if total_kept != len(rows):
        raise AssertionError(
            "registered class-local similarity audit would drop fixture families"
        )
    return {
        "algorithm": DEDUP_ALGORITHM,
        "threshold": DEDUP_THRESHOLD,
        "input": len(rows),
        "kept": total_kept,
        "dropped": len(rows) - total_kept,
        "maximum_compared_similarity": round(global_maximum, 12),
        "by_label": by_label,
    }


def build(output: Path = OUTPUT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for label in EXACT_TOOL_LABELS:
        families = _family_ids(label)
        for split in ("train", "dev", "test"):
            rows.extend(
                _case(label, split, index, family_id)
                for index, family_id in enumerate(families[split])
            )
    preflight_rows = [
        _case(
            label,
            "preflight",
            index,
            f"ETCV1-PREFLIGHT-{label.replace('_', '-').lower()}-{index:02d}",
        )
        for label in EXACT_TOOL_LABELS
        for index in range(PREFLIGHT_PER_CLASS)
    ]

    family_ids = [row["semantic_family_id"] for row in rows]
    projections = [row["selector_projection_sha256"] for row in rows]
    if len(rows) != len(EXACT_TOOL_LABELS) * TOTAL_PER_CLASS:
        raise AssertionError("unexpected coverage plan size")
    if len(set(family_ids)) != len(family_ids):
        raise AssertionError("semantic family IDs must be globally unique")
    if len(set(projections)) != len(projections):
        raise AssertionError("selector projections must be byte-distinct")
    if any(
        _split_for_family(row["semantic_family_id"]) != row["split"] for row in rows
    ):
        raise AssertionError("family split digest mismatch")
    harness = ActionHarness()
    validated_action_contracts = 0
    for row in [*rows, *preflight_rows]:
        _validate_fixture_paths(row)
        rendered = _canonical(row["selector_projection"])
        if any(
            field in rendered for field in ('"arguments"', '"parameters"', '"result"')
        ):
            raise AssertionError("Selector projection leaked Executor fields")
        if row["label"] in {"final_answer", ABSTAIN_LABEL}:
            continue
        execution = row["executor_contract"]
        if not isinstance(execution, Mapping):
            raise TypeError("ordinary fixture requires an Executor contract")
        normalized = harness.normalize_action(
            TaskAction(
                str(execution.get("operation") or ""),
                dict(execution.get("expected_arguments") or {}),
            )
        )
        if normalized.action_type != row["label"]:
            raise AssertionError("fixture action differs from expected label")
        validated_action_contracts += 1
    similarity_audit = _similarity_audit(rows)

    output.mkdir(parents=True, exist_ok=True)
    cases_path = output / "cases.jsonl"
    preflight_path = output / "preflight.jsonl"
    readme_path = output / "README.md"
    cases_path.write_bytes(_jsonl_bytes(rows))
    preflight_path.write_bytes(_jsonl_bytes(preflight_rows))
    readme_path.write_text(README, encoding="utf-8")
    label_counts = Counter(row["label"] for row in rows)
    split_counts = Counter(row["split"] for row in rows)
    label_split_counts = {
        label: {
            split: sum(row["label"] == label and row["split"] == split for row in rows)
            for split in SPLIT_COUNTS
        }
        for label in EXACT_TOOL_LABELS
    }
    manifest = {
        "schema_version": SCHEMA,
        "dataset_version": "rwkv-lh.exact-tool-coverage.v1",
        "artifact_kind": "frozen_collection_plan_not_training_data",
        "source": "Frozen current Harness registry and independently generated workspace fixtures",
        "purpose": "Collect verified exact-tool labels for the independent 2.9B Selector",
        "generation": "uv run python scripts/generate_exact_tool_selector_coverage_v1.py",
        "generator": {
            "path": "scripts/generate_exact_tool_selector_coverage_v1.py",
            "sha256": _sha256_file(Path(__file__).resolve()),
        },
        "protocol": {
            "path": PROTOCOL.relative_to(ROOT).as_posix(),
            "sha256": _sha256_file(PROTOCOL),
        },
        "tool_menu_digest": selector_menu_digest(),
        "class_order": list(EXACT_TOOL_LABELS),
        "counts": {
            "total": len(rows),
            "semantic_families": len(set(family_ids)),
            "by_label": {label: label_counts[label] for label in EXACT_TOOL_LABELS},
            "by_split": dict(split_counts),
            "by_label_and_split": label_split_counts,
            "preflight_total": len(preflight_rows),
            "preflight_by_label": {
                label: sum(row["label"] == label for row in preflight_rows)
                for label in EXACT_TOOL_LABELS
            },
        },
        "split_protocol": "sha256(family_id) modulo 10: 0=dev, 1=test, 2..9=train; preselected to 240/30/30 per label before model calls",
        "validation": {
            "model_calls": 0,
            "raw_rwkv_outputs": 0,
            "training_rows": 0,
            "unique_family_ids": len(set(family_ids)),
            "unique_selector_projections": len(set(projections)),
            "family_split_mismatch_count": 0,
            "selector_executor_field_leak_count": 0,
            "workspace_relative_path_failure_count": 0,
            "validated_harness_action_contracts": validated_action_contracts,
            "similarity_audit": similarity_audit,
        },
        "files": {
            "README.md": {
                "bytes": readme_path.stat().st_size,
                "sha256": _sha256_file(readme_path),
            },
            "cases.jsonl": {
                "bytes": cases_path.stat().st_size,
                "sha256": _sha256_file(cases_path),
            },
            "preflight.jsonl": {
                "bytes": preflight_path.stat().st_size,
                "sha256": _sha256_file(preflight_path),
            },
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    print(json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
