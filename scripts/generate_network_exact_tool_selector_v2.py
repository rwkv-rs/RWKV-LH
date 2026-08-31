#!/usr/bin/env python3
"""Generate the frozen 25-class intent-contract dataset for Selector v2."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_ABSTAIN_LABEL,
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
    network_selector_menu_digest,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "datasets" / "rwkv_lh_network_exact_tool_selector_v2_4"
PROTOCOL = (
    ROOT
    / "data"
    / "experiments"
    / "NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
    / "PREREGISTRATION_V2_4.md"
)
SCHEMA_VERSION = "rwkv-lh.network-exact-tool-selector-row.v2.4"
DATASET_VERSION = "rwkv-lh.network-exact-tool-selector.v2.4"
SPLIT_COUNTS = {"train": 240, "dev": 30, "test": 30}
SIMILARITY_ALGORITHM = "utf8-byte-5gram-cosine.v1"
SIMILARITY_THRESHOLD = 0.95

SPLIT_SURFACES = {
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

SUBJECTS = (
    "release ledger",
    "build registry",
    "incident notebook",
    "package catalog",
    "research brief",
    "weather report",
    "source archive",
    "quality matrix",
    "deployment manifest",
    "audit timeline",
    "inventory snapshot",
    "migration playbook",
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
PROJECT_TONES = ("amber", "bright", "calm", "deep", "fair", "green", "quiet", "swift")
PROJECT_FORMS = ("arc", "beacon", "bridge", "compass", "harbor", "ridge", "signal", "trail")
PROJECT_MATERIALS = ("birch", "copper", "flint", "glass", "iron", "maple", "stone", "willow")
PROJECT_OBJECTS = ("atlas", "catalog", "ledger", "matrix", "notebook", "registry", "timeline", "workshop")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def split_for_family(family_id: str) -> str:
    bucket = int(hashlib.sha256(family_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "dev"
    if bucket == 1:
        return "test"
    return "train"


def family_ids(label: str) -> dict[str, list[str]]:
    selected = {split: [] for split in SPLIT_COUNTS}
    counter = 0
    while any(len(selected[name]) < count for name, count in SPLIT_COUNTS.items()):
        family_id = f"NETSEL2-{label.lower().replace('_', '-')}-{counter:06d}"
        split = split_for_family(family_id)
        if len(selected[split]) < SPLIT_COUNTS[split]:
            selected[split].append(family_id)
        counter += 1
    return selected


def surface(label: str, split: str, index: int, family_id: str) -> dict[str, str]:
    label_index = NETWORK_EXACT_TOOL_LABELS.index(label)
    domain = SPLIT_SURFACES[split][(index * 7 + label_index * 3) % 10]
    subject = SUBJECTS[(index * 5 + label_index * 7) % len(SUBJECTS)]
    qualifier = QUALIFIERS[(index * 11 + label_index * 5) % len(QUALIFIERS)]
    family_digest = hashlib.sha256(family_id.encode("utf-8")).digest()
    suffix = family_digest.hex()[:10]
    project = (
        f"{PROJECT_TONES[family_digest[0] % len(PROJECT_TONES)]}-"
        f"{PROJECT_FORMS[family_digest[1] % len(PROJECT_FORMS)]} "
        f"{PROJECT_MATERIALS[family_digest[2] % len(PROJECT_MATERIALS)]}-"
        f"{PROJECT_OBJECTS[family_digest[3] % len(PROJECT_OBJECTS)]}"
    )
    return {
        "domain": domain,
        "subject": subject,
        "qualifier": qualifier,
        "suffix": suffix,
        "ticket": f"case-{10000 + index}-{suffix[:6]}",
        "path": f"{domain}/{subject.replace(' ', '-')}-{qualifier}-{suffix}",
        "marker": f"MARKER_{domain.upper()}_{suffix.upper()}",
        "project": project,
        "scope": f"{project}, {domain} {qualifier} {subject} record {suffix}",
    }


def progress_for(label: str, index: int) -> NetworkSelectorProgress:
    if label == "final_answer":
        return NetworkSelectorProgress(
            completed_stage_count=2 + index % 3,
            action_index=3 + index % 4,
            succeeded_operations=("write_file", "check_command"),
        )
    if label == NETWORK_ABSTAIN_LABEL:
        return NetworkSelectorProgress(
            completed_stage_count=index % 2,
            action_index=index % 3,
            failed_operations=("read_file",) if index % 4 == 0 else (),
            protocol_rejection_count=index % 2,
        )
    histories = (
        (),
        ("list_directory",),
        ("read_file",),
        ("web_search",),
        ("connector_lookup",),
        ("search_text", "read_file"),
    )
    succeeded = tuple(item for item in histories[index % len(histories)] if item != label)
    return NetworkSelectorProgress(
        completed_stage_count=index % 3,
        action_index=index % 5,
        succeeded_operations=succeeded,
        failed_operations=("read_file",) if label != "read_file" and index % 17 == 0 else (),
        protocol_rejection_count=1 if index % 29 == 0 else 0,
    )


def objective_for(label: str, s: dict[str, str], index: int) -> tuple[str, str]:
    path = s["path"]
    marker = s["marker"]
    suffix = s["suffix"]
    variant = index % 6
    values: dict[str, tuple[str, ...]] = {
        "list_directory": (
            f"Enumerate bounded path, type, and size metadata recursively under {path}; do not open file contents.",
            f"Inspect the directory structure at {path} and return names, kinds, and sizes only.",
            f"List entries below {path} with a fixed bound; this is directory metadata, not text search.",
            f"Observe which files and folders exist under {path} without reading their bytes.",
            f"Return a recursive inventory for {path}, limited to path/type/size fields.",
            f"Survey the workspace tree rooted at {path}; no file body is required.",
        ),
        "search_text": (
            f"Search workspace UTF-8 files for the literal token {marker} and return ordered line locators; do not use the internet.",
            f"Locate every local TODO matching {marker} below {path} with bounded regex results.",
            f"Find local source lines containing {marker}; this is workspace search, not public web discovery.",
            f"Scan project text under {path} for pattern {marker} and report file/line matches.",
            f"Use the local text index to find {marker}, preserving result order and cursor bounds.",
            f"Identify workspace occurrences of {marker} without opening unrelated full files.",
        ),
        "read_file": (
            f"Read the exact UTF-8 bytes from {path}/notes.txt starting at the recorded byte offset.",
            f"Observe the next tokenizer-bounded range of plain text in {path}/report.md.",
            f"Open one exact byte range from {path}/config.env as plain UTF-8 text.",
            f"Continue reading {path}/log.txt from next_start_byte without guessing omitted text.",
            f"Retrieve the literal contents of {path}/README.txt within the read bound.",
            f"Inspect a bounded slice of the existing non-JSON file {path}/status.txt.",
        ),
        "read_json": (
            f"Parse {path}/manifest.json and observe its canonical compact JSON value.",
            f"Read the next bounded canonical JSON range from {path}/settings.json.",
            f"Inspect structured keys in the existing JSON file {path}/record.json.",
            f"Observe the parsed JSON object stored at {path}/metadata.json, not raw plain text.",
            f"Load {path}/package.json as JSON and return a tokenizer-bounded canonical range.",
            f"Continue the canonical JSON read of {path}/state.json from its recorded byte offset.",
        ),
        "file_digest": (
            f"Measure the exact SHA-256 and byte size of {path}/artifact.bin without reading or changing its content.",
            f"Observe the content digest for {path}/bundle.tar and leave the file untouched.",
            f"Compute file identity metadata, SHA-256 plus bytes, for {path}/snapshot.dat.",
            f"Verify the checksum of {path}/release.zip without executing or copying it.",
            f"Return the byte count and SHA-256 for the existing file {path}/image.raw.",
            f"Fingerprint {path}/payload.bin through the read-only digest operation.",
        ),
        "write_file": (
            f"Atomically create {path}/summary.txt with the complete provided UTF-8 report.",
            f"Replace {path}/answer.md with the full known text in one atomic write.",
            f"Create the new plain-text file {path}/notice.txt from the visible content.",
            f"Write the complete UTF-8 body to {path}/result.txt, replacing any old body.",
            f"Persist the supplied text exactly at {path}/output.md using an atomic replacement.",
            f"Materialize a complete non-JSON document at {path}/brief.txt.",
        ),
        "write_json": (
            f"Atomically replace {path}/manifest.json with the complete supplied JSON value.",
            f"Create {path}/settings.json from the entire already-known JSON object.",
            f"Write a full JSON array to {path}/records.json, replacing any old value.",
            f"Persist the complete structured value at {path}/package.json; omitted keys are intentionally removed.",
            f"Create or replace {path}/result.json using the whole visible JSON value.",
            f"Serialize the complete known JSON object atomically to {path}/state.json.",
        ),
        "patch_json": (
            f"Update only keys status and revision in {path}/manifest.json while preserving every other top-level key.",
            f"Patch the explicit enabled field in {path}/settings.json without replacing the full object.",
            f"Modify named top-level keys in {path}/record.json and retain all unspecified entries.",
            f"Apply a partial JSON object update to {path}/package.json, preserving unrelated metadata.",
            f"Change only the requested JSON keys in {path}/state.json rather than rewriting it wholesale.",
            f"Merge the explicit top-level patch into {path}/config.json with unspecified keys untouched.",
        ),
        "replace_text": (
            f"Replace the one exact occurrence of OLD_{suffix} with NEW_{suffix} in {path}/notes.txt.",
            f"Substitute a precisely observed text span in {path}/README.md without rewriting unrelated content.",
            f"Change the exact literal version-{suffix} to release-{suffix} inside {path}/config.txt.",
            f"Perform one exact old-to-new text replacement in {path}/report.md.",
            f"Replace the known unique phrase in {path}/status.txt while preserving the rest byte-for-byte.",
            f"Apply the explicit literal substitution to {path}/source.py.",
        ),
        "remove_line": (
            f"Remove the complete line DEPRECATED_{suffix} from {path}/settings.txt.",
            f"Delete one exactly observed UTF-8 line from {path}/notes.md and keep every other line.",
            f"Remove the full obsolete entry in {path}/requirements.txt.",
            f"Erase one complete matching line from {path}/report.txt, not the whole file.",
            f"Drop the exact legacy line from {path}/config.env while retaining adjacent lines.",
            f"Remove the known line marker {marker} from {path}/source.txt.",
        ),
        "append_file": (
            f"Append the supplied audit line to {path}/history.log without replacing existing bytes.",
            f"Add one UTF-8 record at the end of {path}/events.txt.",
            f"Extend {path}/CHANGELOG.md with the provided release paragraph.",
            f"Append a trailing status entry to {path}/journal.txt; preserve the current content.",
            f"Add the known text after the existing bytes of {path}/notes.txt.",
            f"Write one additional line to the end of {path}/ledger.log.",
        ),
        "make_directory": (
            f"Create the workspace directory {path}/generated.",
            f"Ensure the new folder {path}/reports exists without creating a file.",
            f"Make the scoped directory tree {path}/artifacts/current.",
            f"Create a destination folder at {path}/output.",
            f"Materialize the directory {path}/cache/verified inside the workspace.",
            f"Add the empty workspace directory {path}/archive.",
        ),
        "copy_file": (
            f"Copy the exact bytes of {path}/source.bin to {path}/backup.bin and retain the source.",
            f"Duplicate {path}/template.txt at {path}/generated.txt without editing either content.",
            f"Create a byte-identical copy of {path}/manifest.json at {path}/archive.json.",
            f"Copy the scoped file {path}/a.dat to {path}/b.dat, leaving a.dat present.",
            f"Duplicate the existing report from {path}/draft.md to {path}/final.md.",
            f"Replicate exact file bytes from {path}/input to {path}/output.",
        ),
        "move_file": (
            f"Rename {path}/draft.txt to {path}/final.txt so the source path no longer exists.",
            f"Move {path}/incoming.bin to {path}/archive.bin with exact bytes preserved.",
            f"Relocate the existing file from {path}/old.json to {path}/new.json.",
            f"Change the path of {path}/before.md to {path}/after.md rather than copying it.",
            f"Move the scoped artifact into {path}/done/artifact.dat and remove its former path.",
            f"Rename {path}/temp.log as {path}/verified.log.",
        ),
        "delete_file": (
            f"Delete the explicitly scoped file {path}/obsolete.tmp.",
            f"Remove {path}/stale.json from the workspace after its target has been verified.",
            f"Erase the exact path {path}/old.log; do not modify sibling files.",
            f"Delete the known disposable artifact {path}/cache.bin.",
            f"Remove one scoped workspace file at {path}/retired.txt.",
            f"Delete {path}/unused.md and no broader directory.",
        ),
        "bind_evidence": (
            f"Retain lines 12 through 16 from {path}/report.txt as exact quoted evidence with its locator.",
            f"Bind the observed source span in {path}/notes.md so the final answer can cite the exact text.",
            f"Record an exact line range and quote from {path}/audit.log as durable evidence.",
            f"Capture lines 4 through 9 of {path}/result.txt with file and line provenance.",
            f"Preserve the precise supporting quote from {path}/README.md and its locator.",
            f"Bind the selected workspace line span from {path}/manifest.txt as evidence.",
        ),
        "check_command": (
            f"Run the read-only test command python -m pytest for the scoped project under {path}.",
            f"Execute a linter inspection for {path} using argv and shell disabled.",
            f"Check repository status under {path} with a non-mutating command.",
            f"Run the requested read-only validation command and observe its exact exit code.",
            f"Inspect the build with a test-only command; no files should be intentionally changed.",
            f"Execute the bounded verification argv for {path}, expecting the registered exit code.",
        ),
        "run_command": (
            f"Run the approved local build command under {path}; it may create compiled artifacts.",
            f"Execute the mutating formatter argv on the scoped project at {path} with shell disabled.",
            f"Invoke the local generator command that writes outputs below {path}.",
            f"Run the approved installation or migration argv inside the workspace scope.",
            f"Execute the command that updates generated files for {path}.",
            f"Launch the bounded local build step whose intended effect modifies workspace artifacts.",
        ),
        "web_search": (
            f"Search the public web for current information about {s['qualifier']} {s['subject']} {suffix} and return source evidence.",
            f"Fetch the exact public URL https://example.org/{s['domain']}/{suffix} and preserve content-addressed evidence.",
            f"Discover public pages that mention {marker}; this is internet research, not a workspace text search.",
            f"Find recent web sources about the {s['domain']} {s['subject']} and return bounded exact spans.",
            f"Search broadly online to discover candidate sources for {s['qualifier']} {s['subject']} {suffix}.",
            f"Retrieve public website evidence for the query {marker} without assuming a structured record identifier.",
        ),
        "connector_lookup": (
            f"Query the structured GitHub repository record for owner{s['domain']}/repo-{suffix} and return exact fields.",
            f"Look up the exact package release for package-{s['domain']}-{suffix} in its structured registry.",
            f"Retrieve the scholarly metadata record for DOI 10.1234/{s['domain']}.{suffix} from a structured source.",
            f"Read the structured weather observation for {s['domain']}-station-{suffix}, not general web pages.",
            f"Query the exact GitHub release record for owner{s['domain']}/project-{suffix}.",
            f"Use a public structured connector to obtain the canonical package or repository fields for id-{suffix}.",
        ),
        "calculator": (
            f"Evaluate the known arithmetic expression ({100 + index} * 17) + {index % 13} exactly.",
            f"Calculate ({300 + index} - 41) / 7 from the operands already provided.",
            f"Compute the numeric value of 2**{3 + index % 8} + {index} without searching for new facts.",
            f"Evaluate the complete expression ({index + 9} * {index % 23 + 2}) - 5.",
            f"Perform the deterministic arithmetic 1000 / {index % 19 + 1} + 6.",
            f"Return the exact result of ({index + 4} + 11) * 3 using the safe calculator.",
        ),
        "date_diff": (
            f"Calculate the absolute calendar-day distance between 2025-01-{index % 27 + 1:02d} and 2025-03-{index % 27 + 1:02d}.",
            f"Find the number of calendar days between known dates 2024-02-01 and 2024-04-{index % 27 + 1:02d}.",
            f"Compare ISO dates 2026-01-{index % 27 + 1:02d} and 2026-06-15 by absolute day count.",
            f"Compute the day interval from 2023-07-01 to 2023-07-{index % 27 + 1:02d}; both dates are already observed.",
            f"Measure calendar days between 2022-11-{index % 27 + 1:02d} and 2023-01-12.",
            f"Return the absolute ISO-date difference for 2020-05-20 and 2021-05-{index % 27 + 1:02d}.",
        ),
        "current_time": (
            f"Observe the current clock reading in Asia/Shanghai for {s['ticket']}.",
            f"Report the current time in UTC using the local clock capability.",
            f"Read the current wall-clock timestamp for America/New_York.",
            f"Observe what time it is now in Europe/London; this is not a web lookup.",
            f"Get the present timestamp in Asia/Tokyo from the clock operation.",
            f"Return the current time for Australia/Sydney with its timezone offset.",
        ),
        "final_answer": (
            f"All requested work and checks for {s['ticket']} are complete; deliver the grounded result to the user now.",
            f"The exact evidence for {s['subject']} has already been collected and no tool is still needed; answer the user.",
            f"The scoped change at {path} passed verification; finish with an honest user-facing summary.",
            f"No unresolved stage remains for {s['qualifier']} {s['subject']}; return the final response.",
            f"The required facts and citations are already bound; synthesize the completed answer without another action.",
            f"Execution and validation have succeeded for {s['ticket']}; end the run with the result.",
        ),
        NETWORK_ABSTAIN_LABEL: (
            f"The request says only 'handle {s['subject']}' and does not identify an observable target or a unique operation.",
            f"Two incompatible next actions are demanded for {path} with no precedence; do not guess which tool to use.",
            f"The stage asks for an unsupported private account action outside the frozen tool menu.",
            f"The requested destructive scope is ambiguous and lacks an explicit target; choose no operation.",
            f"Required observable information for {s['ticket']} is missing, so exactly one safe tool cannot be selected.",
            f"The stage objective is internally contradictory and cannot map to one authorized operation.",
        ),
    }
    objective = (
        values[label][variant]
        + f" The unique task scope is the {s['scope']}."
    )
    task_surfaces = (
        f"Complete the {s['qualifier']} {s['subject']} for {s['ticket']} and preserve auditable evidence for every change.",
        f"Bring the {s['domain']} {s['subject']} to a verified result for {s['ticket']} while staying within its explicit scope.",
        f"Resolve {s['ticket']} for the {s['qualifier']} {s['subject']}; use observable facts and report any incomplete work honestly.",
        f"Prepare a grounded outcome for the {s['domain']} {s['subject']} identified by {s['ticket']}, with bounded side effects.",
        f"Finish the scoped {s['subject']} workflow for {s['ticket']} and retain exact provenance for facts that support the result.",
        f"Handle the {s['qualifier']} {s['subject']} request tagged {s['ticket']}; do not act outside the named task boundary.",
        f"Produce a checked result for {s['ticket']} in the {s['domain']} {s['subject']} workflow and preserve existing unrelated data.",
        f"Complete the requested {s['subject']} outcome for {s['ticket']} using only authorized operations and verifiable observations.",
        f"Advance {s['ticket']} from its current state to a validated {s['qualifier']} {s['subject']} result.",
        f"Deliver the scoped {s['domain']} {s['subject']} for {s['ticket']}; correctness and exact evidence take priority.",
        f"Process the {s['qualifier']} {s['subject']} ticket {s['ticket']} without guessing missing facts or broadening its scope.",
        f"Complete and verify the {s['domain']} task record {s['ticket']} concerning the specified {s['subject']}.",
    )
    task = (
        task_surfaces[index % len(task_surfaces)]
        + f" The project identity is {s['project']}."
    )
    return task, objective


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    if len(raw) < n:
        return Counter({raw: 1})
    return Counter(raw[index : index + n] for index in range(len(raw) - n + 1))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    numerator = sum(left[key] * right[key] for key in left.keys() & right.keys())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def similarity_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["label"]].append(row)
    by_label: dict[str, Any] = {}
    global_max = 0.0
    threshold_violations = 0
    cross_split_violations = 0
    for label, items in grouped.items():
        vectors = [
            byte_ngrams(canonical(item["selector_projection"])) for item in items
        ]
        vocabulary = {
            gram: index
            for index, gram in enumerate(
                sorted({gram for vector in vectors for gram in vector})
            )
        }
        matrix = np.zeros((len(items), len(vocabulary)), dtype=np.float64)
        for row_index, vector in enumerate(vectors):
            for gram, count in vector.items():
                matrix[row_index, vocabulary[gram]] = count
        norms = np.linalg.norm(matrix, axis=1)
        if bool(np.any(norms == 0.0)):
            raise RuntimeError("similarity audit found an empty byte-ngram vector")
        matrix /= norms[:, None]
        scores = matrix @ matrix.T
        left_indices, right_indices = np.triu_indices(len(items), k=1)
        pair_scores = scores[left_indices, right_indices]
        label_max = float(pair_scores.max(initial=0.0))
        violations = np.flatnonzero(pair_scores >= SIMILARITY_THRESHOLD)
        threshold_violations += int(violations.size)
        cross_split_violations += sum(
            items[int(left_indices[position])]["split"]
            != items[int(right_indices[position])]["split"]
            for position in violations
        )
        global_max = max(global_max, label_max)
        by_label[label] = {"max_similarity": label_max, "rows": len(items)}
    return {
        "algorithm": SIMILARITY_ALGORITHM,
        "threshold": SIMILARITY_THRESHOLD,
        "global_max_similarity": global_max,
        "threshold_violation_count": threshold_violations,
        "cross_split_violation_count": cross_split_violations,
        "by_label": by_label,
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in NETWORK_EXACT_TOOL_LABELS:
        ids = family_ids(label)
        for split in ("train", "dev", "test"):
            for index, family_id in enumerate(ids[split]):
                semantic_index = {"train": 0, "dev": 240, "test": 270}[split] + index
                s = surface(label, split, semantic_index, family_id)
                task, objective = objective_for(label, s, semantic_index)
                selector_input = NetworkSelectorInput.create(
                    task_request=task,
                    stage_objective=objective,
                    stage_role=(
                        "finish"
                        if label == "final_answer"
                        else "boundary"
                        if label == NETWORK_ABSTAIN_LABEL
                        else "work"
                    ),
                    progress=progress_for(label, semantic_index),
                )
                projection = {
                    "task_request": selector_input.task_request,
                    "stage_objective": selector_input.stage_objective,
                    "stage_role": selector_input.stage_role,
                    "progress": selector_input.progress.to_dict(),
                }
                rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "sample_id": f"NETSEL2-{len(rows):05d}",
                        "semantic_family_id": family_id,
                        "split": split,
                        "label": label,
                        "selector_projection": projection,
                        "selector_projection_sha256": canonical_digest(projection),
                        "selector_input_sha256": canonical_digest(selector_input.to_dict()),
                        "rendered_input": selector_input.render(),
                        "rendered_input_sha256": hashlib.sha256(
                            selector_input.render().encode("utf-8")
                        ).hexdigest(),
                        "source": "independent operation-intent contract fixture",
                        "purpose": "train and evaluate the independent 2.9B Hidden+MLP exact-tool Selector",
                    }
                )
    return rows


def main() -> None:
    if not PROTOCOL.is_file():
        raise FileNotFoundError(PROTOCOL)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    expected_total = len(NETWORK_EXACT_TOOL_LABELS) * sum(SPLIT_COUNTS.values())
    if len(rows) != expected_total:
        raise RuntimeError(f"expected {expected_total} rows, got {len(rows)}")
    counts: dict[str, dict[str, int]] = {
        label: {split: 0 for split in SPLIT_COUNTS}
        for label in NETWORK_EXACT_TOOL_LABELS
    }
    for row in rows:
        counts[row["label"]][row["split"]] += 1
        if split_for_family(row["semantic_family_id"]) != row["split"]:
            raise RuntimeError("semantic family split mismatch")
    if any(counts[label] != SPLIT_COUNTS for label in NETWORK_EXACT_TOOL_LABELS):
        raise RuntimeError("per-class split count mismatch")
    similarity = similarity_audit(rows)
    if similarity["threshold_violation_count"]:
        raise RuntimeError(
            "fixed similarity threshold violated: "
            f"{similarity['threshold_violation_count']} pairs"
        )

    cases = OUTPUT / "cases.jsonl"
    cases.write_text(
        "".join(canonical(row) + "\n" for row in rows), encoding="utf-8"
    )
    readme = OUTPUT / "README.md"
    readme.write_text(
        "# RWKV-LH Network Exact-Tool Selector v2.4\n\n"
        "Frozen 25-class operation-intent contract dataset for the independent "
        "2.9B Hidden+MLP Selector. It contains 7500 semantic families with "
        "240/30/30 train/dev/test rows per class. Labels are pre-registered "
        "operation contracts, not model-generated labels. The old v1 coverage "
        "collection plan is not used as training data.\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "rwkv-lh.network-exact-tool-selector-manifest.v2.4",
        "dataset_version": DATASET_VERSION,
        "source": "independent split-specific operation-intent contract fixtures",
        "purpose": "train/evaluate 25-class 2.9B Hidden+MLP tool selection",
        "generation": "uv run python scripts/generate_network_exact_tool_selector_v2.py",
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
        },
        "class_order": list(NETWORK_EXACT_TOOL_LABELS),
        "menu_digest": network_selector_menu_digest(),
        "counts": {
            "total": len(rows),
            "by_label_and_split": counts,
            "by_split": {
                split: sum(1 for row in rows if row["split"] == split)
                for split in SPLIT_COUNTS
            },
        },
        "split_protocol": "sha256(family_id) modulo 10: 0=dev, 1=test, 2..9=train; deterministically selected to 240/30/30 per class",
        "rejected_predecessors": [
            "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_r0_rejected/RESULT.json",
            "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_r1_rejected/RESULT.json",
            "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_r2_rejected/RESULT.json",
            "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_r3_rejected/RESULT.json",
        ],
        "similarity_projection": "canonical-json-selector-projection-task-stage-role-progress.v1",
        "similarity_audit": similarity,
        "field_leak_audit": {
            "forbidden_fields": [
                "parameters",
                "arguments",
                "result",
                "reasoning",
                "executor_state",
                "workspace_contents",
            ],
            "violations": 0,
        },
        "files": {
            "cases.jsonl": {
                "sha256": sha256_file(cases),
                "bytes": cases.stat().st_size,
            },
            "README.md": {
                "sha256": sha256_file(readme),
                "bytes": readme.stat().st_size,
            },
        },
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "dataset": str(OUTPUT),
                "rows": len(rows),
                "cases_sha256": manifest["files"]["cases.jsonl"]["sha256"],
                "menu_digest": manifest["menu_digest"],
                "max_similarity": similarity["global_max_similarity"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
