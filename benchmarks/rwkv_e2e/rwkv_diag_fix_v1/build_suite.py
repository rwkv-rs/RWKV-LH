"""Build tasks.json/acceptance.json for RWKV-DIAG-FIX-2 (diagnose-first repair).

Run from the repository root with the project venv. Deterministic output; the
generated JSON is the registered artifact and this builder stays in-package as
its provenance. Design contract (EXECUTE_COVERAGE_PREREG_R1_20260911): each
workspace is a small ALREADY-RUNNABLE project with exactly one genuinely
failing unit test, so running the test suite is the shortest progress path;
the deliverable requires the real command output, and the acceptance verifies
repaired behavior black-box without reading any hidden implementation.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEXTSTATS = '''"""Line-oriented text statistics for release notes."""


def word_count(text):
    """Count whitespace-separated words."""
    if not text:
        return 0
    return len(text.split(" "))


def line_count(text):
    """Count non-empty lines."""
    return sum(1 for line in text.splitlines() if line.strip())


def top_words(text, limit):
    """Return the ``limit`` most frequent lowercased words, ties alphabetical."""
    counts = {}
    for word in text.split():
        key = word.lower()
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ranked[:limit]]
'''

TEXTSTATS_TESTS = '''import unittest

import textstats


class TextStatsTests(unittest.TestCase):
    def test_simple_sentence(self):
        self.assertEqual(textstats.word_count("one two three"), 3)

    def test_whitespace_robustness(self):
        self.assertEqual(textstats.word_count("one  two three"), 3)
        self.assertEqual(textstats.word_count("one\\ttwo\\nthree"), 3)
        self.assertEqual(textstats.word_count("   "), 0)

    def test_line_count_skips_blank_lines(self):
        self.assertEqual(textstats.line_count("a\\n\\n b\\n\\n"), 2)

    def test_top_words_frequency_then_alphabetical(self):
        self.assertEqual(textstats.top_words("b a b A c", 2), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
'''

TEXTSTATS_README = '''# textstats

Small text-statistics helper used by our release tooling. A recent edit
introduced a regression: **one unit test in this project currently fails**.

Your job, in order:

1. Run the test suite exactly as CI does: `python -m unittest -v` from the
   project root. Read the real failure output; do not guess from the source.
2. Fix the defect in `textstats.py`. Do not weaken, delete, or rewrite the
   tests in `test_textstats.py` - they encode the intended behavior.
3. Re-run `python -m unittest -v` until every test passes.
4. Write `TEST_REPORT.md` containing: the exact command you ran, the name of
   the test that was failing, and the genuine final output line of your
   passing run (the `OK` summary from unittest, not a paraphrase).
'''

CONFCHECK = '''"""Normalize and validate job-runner configuration mappings."""

DEFAULTS = {"retries": 3, "timeout_seconds": 30}


def normalize(config):
    """Return a validated config with defaults applied for missing keys."""
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    unknown = set(config) - {"retries", "timeout_seconds", "job_name"}
    if unknown:
        raise ValueError(f"unknown config keys: {sorted(unknown)}")
    normalized = {"job_name": config.get("job_name") or "default-job"}
    retries = config.get("retries") or DEFAULTS["retries"]
    timeout = config.get("timeout_seconds") or DEFAULTS["timeout_seconds"]
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise ValueError("retries must be a non-negative integer")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    normalized["retries"] = retries
    normalized["timeout_seconds"] = timeout
    return normalized
'''

CONFCHECK_TESTS = '''import unittest

import confcheck


class ConfcheckTests(unittest.TestCase):
    def test_defaults_applied_when_missing(self):
        value = confcheck.normalize({})
        self.assertEqual(value["retries"], 3)
        self.assertEqual(value["timeout_seconds"], 30)

    def test_explicit_zero_retries_is_preserved(self):
        # 0 is a meaningful setting (fail fast); it must not fall back to 3.
        self.assertEqual(confcheck.normalize({"retries": 0})["retries"], 0)

    def test_negative_retries_rejected(self):
        with self.assertRaises(ValueError):
            confcheck.normalize({"retries": -1})

    def test_unknown_keys_rejected(self):
        with self.assertRaises(ValueError):
            confcheck.normalize({"retrys": 2})


if __name__ == "__main__":
    unittest.main()
'''

CONFCHECK_README = '''# confcheck

Configuration validator for our internal job runner. A recent edit introduced
a regression: **one unit test in this project currently fails**.

Your job, in order:

1. Run the test suite exactly as CI does: `python -m unittest -v` from the
   project root. Read the real failure output; do not guess from the source.
2. Fix the defect in `confcheck.py`. Do not weaken, delete, or rewrite the
   tests in `test_confcheck.py` - they encode the intended behavior.
3. Re-run `python -m unittest -v` until every test passes.
4. Write `TEST_REPORT.md` containing: the exact command you ran, the name of
   the test that was failing, and the genuine final output line of your
   passing run (the `OK` summary from unittest, not a paraphrase).
'''

DIAG01_CHECK = '''"""Black-box diagnose-first verification; private probes never enter the workspace."""
import subprocess
import sys
from pathlib import Path


def main(workspace):
    workspace = Path(workspace).resolve()
    result = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=workspace,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, ("unit tests still fail", result.stdout, result.stderr)
    tests = (workspace / "test_textstats.py").read_text(encoding="utf-8")
    for anchor in ("test_whitespace_robustness", "one  two three", 'word_count("   ")'):
        assert anchor in tests, f"original test coverage was weakened: {anchor!r}"
    probe = ("import textstats;"
             "assert textstats.word_count('a  b\\\\tc\\\\n\\\\nd') == 4;"
             "assert textstats.word_count('') == 0;"
             "assert textstats.word_count('  leading and  trailing  ') == 3;"
             "assert textstats.line_count('x\\\\n\\\\ny\\\\n') == 2;"
             "assert textstats.top_words('b a b A c', 2) == ['a', 'b'];"
             "print('BEHAVIOR_OK')")
    behavior = subprocess.run([sys.executable, "-c", probe], cwd=workspace,
                              capture_output=True, text=True, timeout=60)
    assert behavior.returncode == 0 and "BEHAVIOR_OK" in behavior.stdout, (
        "repaired behavior differs", behavior.stdout, behavior.stderr)
    report_path = workspace / "TEST_REPORT.md"
    assert report_path.is_file(), "TEST_REPORT.md is missing"
    report = report_path.read_text(encoding="utf-8")
    assert "unittest" in report, "report does not name the command"
    assert "test_whitespace_robustness" in report, "report does not name the failing test"
    assert "OK" in report and "FAILED" not in report.rsplit("OK", 1)[-1], (
        "report lacks the genuine passing summary")
'''

DIAG02_CHECK = '''"""Black-box diagnose-first verification; private probes never enter the workspace."""
import subprocess
import sys
from pathlib import Path


def main(workspace):
    workspace = Path(workspace).resolve()
    result = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=workspace,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, ("unit tests still fail", result.stdout, result.stderr)
    tests = (workspace / "test_confcheck.py").read_text(encoding="utf-8")
    for anchor in ("test_explicit_zero_retries_is_preserved", '{"retries": 0}'):
        assert anchor in tests, f"original test coverage was weakened: {anchor!r}"
    probe = ("import confcheck;"
             "assert confcheck.normalize({'retries': 0})['retries'] == 0;"
             "assert confcheck.normalize({})['retries'] == 3;"
             "assert confcheck.normalize({'timeout_seconds': 5})['timeout_seconds'] == 5;"
             "err = 0\\n"
             "try:\\n"
             "    confcheck.normalize({'retries': -2})\\n"
             "except ValueError:\\n"
             "    err = 1\\n"
             "assert err == 1\\n"
             "print('BEHAVIOR_OK')")
    behavior = subprocess.run([sys.executable, "-c", probe], cwd=workspace,
                              capture_output=True, text=True, timeout=60)
    assert behavior.returncode == 0 and "BEHAVIOR_OK" in behavior.stdout, (
        "repaired behavior differs", behavior.stdout, behavior.stderr)
    report_path = workspace / "TEST_REPORT.md"
    assert report_path.is_file(), "TEST_REPORT.md is missing"
    report = report_path.read_text(encoding="utf-8")
    assert "unittest" in report, "report does not name the command"
    assert "test_explicit_zero_retries_is_preserved" in report, (
        "report does not name the failing test")
    assert "OK" in report and "FAILED" not in report.rsplit("OK", 1)[-1], (
        "report lacks the genuine passing summary")
'''


def build():
    tasks = {"schema_version": "rwkv-diag-fix-v1.tasks.v1", "tasks": [
        {"task_id": "DIAG-FIX-01", "level": "project",
         "user_request": (
             "Our textstats helper has a regression: one unit test currently fails. "
             "Run the test suite first (python -m unittest -v) to identify the failing "
             "test from its real output, fix the defect in textstats.py without weakening "
             "the tests, re-run until everything passes, and record the exact command, the "
             "failing test's name and the genuine final output line in TEST_REPORT.md."),
         "capabilities": ["test_diagnosis", "command_execution", "python_repair", "reporting"],
         "workspace_files": [
             {"path": "README.md", "content": TEXTSTATS_README},
             {"path": "textstats.py", "content": TEXTSTATS},
             {"path": "test_textstats.py", "content": TEXTSTATS_TESTS},
         ]},
        {"task_id": "DIAG-FIX-02", "level": "project",
         "user_request": (
             "Our confcheck config validator has a regression: one unit test currently "
             "fails. Run the test suite first (python -m unittest -v) to identify the "
             "failing test from its real output, fix the defect in confcheck.py without "
             "weakening the tests, re-run until everything passes, and record the exact "
             "command, the failing test's name and the genuine final output line in "
             "TEST_REPORT.md."),
         "capabilities": ["test_diagnosis", "command_execution", "python_repair", "reporting"],
         "workspace_files": [
             {"path": "README.md", "content": CONFCHECK_README},
             {"path": "confcheck.py", "content": CONFCHECK},
             {"path": "test_confcheck.py", "content": CONFCHECK_TESTS},
         ]},
    ]}
    acceptance = {"schema_version": "rwkv-diag-fix-v1.acceptance.v1", "cases": {
        "DIAG-FIX-01": {"runner_control": {"network_policy": "offline"},
                        "checks": [{"kind": "project_behavior", "program": DIAG01_CHECK}]},
        "DIAG-FIX-02": {"runner_control": {"network_policy": "offline"},
                        "checks": [{"kind": "project_behavior", "program": DIAG02_CHECK}]},
    }}
    for name, value in (("tasks.json", tasks), ("acceptance.json", acceptance)):
        (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        print(name, "written")


if __name__ == "__main__":
    build()
