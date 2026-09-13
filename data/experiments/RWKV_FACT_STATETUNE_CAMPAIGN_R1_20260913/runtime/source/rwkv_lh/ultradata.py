"""Inspect external UltraData records and prepare std-I/O development tasks.

External text is never relabeled as a production role trace. Candidate execution
uses the existing isolated benchmark verifier, including its private-test boundary.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(text):
    return json.loads(text, object_pairs_hook=_unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"nonfinite JSON: {value}")))


def read_frozen_range(path: Path, expected_sha256: str) -> tuple[list[dict], dict]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("source range SHA-256 mismatch")
    lines = raw.split(b"\n")
    tail = lines.pop()
    records = []
    offset = 0
    for number, line in enumerate(lines, 1):
        record = {"line_number": number, "byte_offset": offset, "bytes": len(line),
                  "row_sha256": hashlib.sha256(line).hexdigest()}
        offset += len(line) + 1
        try:
            row = _json(line)
            if not isinstance(row, dict):
                raise ValueError("row must be an object")
            record["row"] = row
        except (ValueError, UnicodeError) as error:
            record["error"] = str(error)
        records.append(record)
    return records, {"complete_rows": len(records), "invalid_rows": sum("error" in x for x in records),
                     "trailing_bytes": len(tail), "tail_sha256": hashlib.sha256(tail).hexdigest()}


def audit_trajectory(row: Mapping[str, Any]) -> dict:
    """Structural observations only: tool output and final text are not truth labels."""
    result = {"uuid": row.get("uuid"), "domain": row.get("domain"), "source": row.get("source"),
              "role_training_eligible": False, "independently_verified_success": None,
              "environment_reproduced": False, "review_reasons": [],
              "message_count": 0, "tool_calls": 0, "tool_results": 0,
              "masked_assistant_turns": 0, "unmasked_assistant_turns": 0,
              "unspecified_loss_assistant_turns": 0, "pending_calls": 0,
              "orphan_results": 0, "undefined_tool_calls": [], "terminal_kind": "unknown"}
    messages, tools = row.get("messages"), row.get("tools")
    if not isinstance(messages, list) or not isinstance(tools, list) or not messages:
        result["review_reasons"].append("invalid_messages_or_tools")
        return result
    defined = {}
    for tool in tools:
        function = tool.get("function", {}) if isinstance(tool, dict) else {}
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            result["review_reasons"].append("invalid_tool_definition")
            continue
        name = function["name"]
        if name in defined:
            result["review_reasons"].append("duplicate_tool_definition")
        defined[name] = function
    result["tool_names"] = sorted(defined)
    result["possible_model_assistance_tools"] = sorted(name for name, tool in defined.items()
        if re.search(r"cloud_assist|stronger.{0,30}model|language model|LLM|模型", name + " " + str(tool.get("description", "")), re.I))
    counts, pending = Counter(), []
    observed_calls = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            result["review_reasons"].append("invalid_message")
            continue
        role = message.get("role")
        counts[str(role)] += 1
        if role not in {"system", "user", "assistant", "tool"}:
            result["review_reasons"].append("unknown_message_role")
        if role == "assistant":
            if "loss" not in message:
                result["unspecified_loss_assistant_turns"] += 1
            elif message["loss"] is False:
                result["masked_assistant_turns"] += 1
            elif message["loss"] is True:
                result["unmasked_assistant_turns"] += 1
            else:
                result["review_reasons"].append("invalid_loss_mask")
            calls = message.get("tool_calls") or []
            if not isinstance(calls, list):
                result["review_reasons"].append("invalid_tool_calls")
                continue
            if pending:
                result["review_reasons"].append("assistant_before_pending_results")
            for call in calls:
                function = call.get("function", {}) if isinstance(call, dict) else {}
                if not isinstance(function, dict) or not isinstance(function.get("name"), str):
                    result["review_reasons"].append("malformed_tool_call")
                    continue
                name = function["name"]
                result["tool_calls"] += 1
                observed_calls.append(name)
                if name not in defined:
                    result["undefined_tool_calls"].append(name)
                args = function.get("arguments")
                try:
                    decoded = _json(args) if isinstance(args, str) else args
                    if not isinstance(decoded, dict):
                        raise ValueError("arguments not an object")
                except ValueError:
                    result["review_reasons"].append("invalid_arguments_json")
                pending.append(call.get("id"))
        elif role == "tool":
            result["tool_results"] += 1
            call_id = message.get("tool_call_id")
            if not pending:
                result["orphan_results"] += 1
            elif call_id is not None:
                if call_id in pending:
                    pending.remove(call_id)
                else:
                    result["orphan_results"] += 1
                    result["review_reasons"].append("unmatched_tool_call_id")
            else:
                pending.pop(0)
                result["review_reasons"].append("positional_pairing_without_call_ids")
    result.update(message_count=len(messages), role_counts=dict(counts), pending_calls=len(pending),
                  called_tools=dict(Counter(observed_calls)),
                  serialized_utf8_bytes=len(json.dumps(row, ensure_ascii=False).encode()),
                  possible_model_assistance_calls=sorted(set(observed_calls) & set(result["possible_model_assistance_tools"])))
    last = messages[-1] if isinstance(messages[-1], dict) else {}
    result["terminal_kind"] = ("pending_tool" if pending else
        "assistant_text_unverified" if last.get("role") == "assistant" and last.get("content") and not last.get("tool_calls") else
        "tool_result" if last.get("role") == "tool" else "other")
    result["review_reasons"] = sorted(set(result["review_reasons"]))
    result["undefined_tool_calls"] = sorted(set(result["undefined_tool_calls"]))
    return result


_CODE_VERIFIER = r'''
import json, math, os, pathlib, resource, signal, subprocess, sys, tempfile
CONFIG = json.loads(__CONFIG__)
workspace = pathlib.Path(sys.argv[1])
def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(CONFIG['case_timeout']) + 1,) * 2)
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (CONFIG['output_limit'],) * 2)
results = []
for index, (input_text, expected) in enumerate(zip(CONFIG['inputs'], CONFIG['outputs'])):
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen([sys.executable, '-I', str(workspace / 'main.py')],
            cwd=workspace, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
            env={'PATH':'/usr/bin:/bin', 'LANG':'C.UTF-8', 'PYTHONDONTWRITEBYTECODE':'1'},
            start_new_session=True, preexec_fn=limits)
        timeout = False
        try:
            process.communicate(input=input_text.encode('utf-8'), timeout=CONFIG['case_timeout'])
        except subprocess.TimeoutExpired:
            timeout = True
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate()
        stdout.seek(0)
        output = stdout.read(CONFIG['output_limit'] + 1)
        try:
            same = output.decode('utf-8').rstrip() == expected.rstrip()
        except UnicodeDecodeError:
            same = False
        passed = not timeout and process.returncode == 0 and len(output) <= CONFIG['output_limit'] and same
        results.append({'case':index, 'passed':passed, 'timeout':timeout, 'exit_code':process.returncode})
print(json.dumps({'cases':len(results), 'passed':sum(x['passed'] for x in results), 'results':results}))
sys.exit(0 if all(x['passed'] for x in results) else 1)
'''


def compile_code_task(row: Mapping[str, Any], *, case_timeout: float = 3.0) -> tuple[dict, dict]:
    """Compile one external std-I/O task, with tests exclusively in private acceptance."""
    identity, query, truth = row.get("uuid"), row.get("query"), row.get("ground_truth")
    if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identity):
        raise ValueError("unsafe or missing task identity")
    if row.get("domain") != "Code" or not isinstance(query, str) or not query.strip():
        raise ValueError("non-Code domain or empty task")
    if not isinstance(truth, dict) or truth.get("call_type") != "std" or truth.get("fn_name") is not None:
        raise ValueError("only explicit std-I/O tasks are supported")
    inputs, outputs = truth.get("inputs"), truth.get("outputs")
    if not isinstance(inputs, list) or not inputs or not isinstance(outputs, list) or len(inputs) != len(outputs):
        raise ValueError("nonempty equal-length I/O arrays required")
    if any(not isinstance(x, str) for x in inputs + outputs):
        raise ValueError("I/O values must be strings")
    seen = {}
    for source, target in zip(inputs, outputs):
        if source in seen and seen[source] != target.rstrip():
            raise ValueError("conflicting targets for identical input")
        seen[source] = target.rstrip()
    if isinstance(case_timeout, bool) or not math.isfinite(case_timeout) or case_timeout <= 0:
        raise ValueError("finite positive timeout required")
    output_limit = max(1024 * 1024, max(len(x.encode()) for x in outputs) + 65536)
    if output_limit > 16 * 1024 * 1024:
        raise ValueError("expected output exceeds bounded pilot verifier capacity")
    config = dict(inputs=inputs, outputs=outputs, case_timeout=case_timeout, output_limit=output_limit)
    program = _CODE_VERIFIER.replace("__CONFIG__", repr(json.dumps(config, ensure_ascii=True)))
    task = {"task_id": "ULTRA-" + identity, "level": "external_code", "user_request": query +
            "\n\nSubmission contract: Implement main.py in Python 3 using the standard library. "
            "Read one test case from stdin and write the specified answer to stdout. "
            "The verifier runs each test in a fresh process, comparing UTF-8 output after removing trailing whitespace only. "
            f"Limits per test: {case_timeout:g} seconds wall time, 512 MiB address space. "
            "Create and run your own checks before delivering.\n",
            "capabilities": ["file_read", "file_write", "command_exec"], "workspace_files": []}
    acceptance = {"runner_control": {"network_policy": "offline"}, "checks": [{"kind": "project_behavior",
                  "program": program, "program_sha256": hashlib.sha256(program.encode()).hexdigest(),
                  "timeout": 180, "browser": False}]}
    return task, acceptance
