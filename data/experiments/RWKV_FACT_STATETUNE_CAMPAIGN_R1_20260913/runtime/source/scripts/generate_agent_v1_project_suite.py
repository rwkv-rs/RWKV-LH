#!/usr/bin/env python3
"""Generate the frozen first-release local Agent project suite."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmarks/rwkv_e2e/rwkv_agent_v1"
SCHEMA_TASKS = "rwkv-agent-v1.tasks.v1"
SCHEMA_ACCEPTANCE = "rwkv-agent-v1.acceptance.v1"


VERIFY_APP = r"""from __future__ import annotations

import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = {"index.html", "styles.css", "app.js", "README.md", "verify_app.py"}
REQUIRED_IDS = {
    "entry-form",
    "entry-type",
    "entry-amount",
    "entry-date",
    "entry-note",
    "month-picker",
    "month-income",
    "month-expense",
    "month-balance",
    "entry-list",
    "empty-state",
}


class LedgerHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.stylesheet = False
        self.script = False
        self.form = False
        self.buttons = 0
        self.labels = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "link" and values.get("href") == "styles.css":
            self.stylesheet = True
        if tag == "script" and values.get("src") == "app.js":
            self.script = True
        if tag == "form" and values.get("id") == "entry-form":
            self.form = True
        if tag == "button":
            self.buttons += 1
        if tag == "label":
            self.labels += 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    actual_files = {path.name for path in ROOT.iterdir() if path.is_file()}
    require(actual_files == REQUIRED_FILES, f"unexpected file set: {sorted(actual_files)}")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    parser = LedgerHTMLParser()
    parser.feed(html)
    require(REQUIRED_IDS <= parser.ids, f"missing HTML ids: {sorted(REQUIRED_IDS - parser.ids)}")
    require(parser.stylesheet and parser.script and parser.form, "HTML assets/form are not wired")
    require(parser.buttons >= 1 and parser.labels >= 4, "form needs a button and accessible labels")
    require('lang="zh-CN"' in html or "lang='zh-CN'" in html, "page language must be zh-CN")
    require("viewport" in html, "responsive viewport is missing")

    for token in ("--", "@media", ":focus", "grid", "border-radius"):
        require(token in css, f"CSS quality token missing: {token}")
    require(len(css) >= 1200, "CSS is too small to implement the requested polished responsive UI")

    for token in (
        "localStorage",
        "JSON.parse",
        "JSON.stringify",
        "calculateMonthlySummary",
        "loadRecords",
        "saveRecords",
        "addRecord",
        "deleteRecord",
        "window.LedgerApp",
        "addEventListener",
    ):
        require(token in js, f"JavaScript contract missing: {token}")
    require(re.search(r"income", js, re.I) is not None, "income behavior is missing")
    require(re.search(r"expense", js, re.I) is not None, "expense behavior is missing")
    require("localStorage" in readme and "verify_app.py" in readme, "README usage/verification is incomplete")

    node_test = r'''
const fs = require("fs");
const vm = require("vm");
global.window = {};
global.document = undefined;
global.localStorage = {
  values: new Map(),
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null; },
  setItem(key, value) { this.values.set(key, String(value)); },
  removeItem(key) { this.values.delete(key); }
};
vm.runInThisContext(fs.readFileSync("app.js", "utf8"), { filename: "app.js" });
const api = window.LedgerApp;
if (!api) throw new Error("window.LedgerApp is missing");
for (const name of ["calculateMonthlySummary", "loadRecords", "saveRecords", "addRecord", "deleteRecord"]) {
  if (typeof api[name] !== "function") throw new Error(`${name} must be a function`);
}
const records = [
  {id:"r1", type:"income", amount:1500, date:"2026-08-03", note:"salary"},
  {id:"r2", type:"expense", amount:200, date:"2026-08-04", note:"food"},
  {id:"r3", type:"expense", amount:25.5, date:"2026-08-09", note:"train"},
  {id:"r4", type:"income", amount:99, date:"2026-07-31", note:"old"}
];
const summary = api.calculateMonthlySummary(records, "2026-08");
if (JSON.stringify(summary) !== JSON.stringify({income:1500, expense:225.5, balance:1274.5})) {
  throw new Error(`wrong monthly summary: ${JSON.stringify(summary)}`);
}
api.saveRecords(records, global.localStorage);
if (JSON.stringify(api.loadRecords(global.localStorage)) !== JSON.stringify(records)) {
  throw new Error("localStorage round trip failed");
}
const added = api.addRecord(records, {id:"r5", type:"expense", amount:10, date:"2026-08-10", note:"tea"});
if (added.length !== 5 || records.length !== 4) throw new Error("addRecord must return a new complete array");
const deleted = api.deleteRecord(added, "r2");
if (deleted.length !== 4 || deleted.some(item => item.id === "r2")) throw new Error("deleteRecord failed");
console.log(JSON.stringify({summary, storage:true, add:true, delete:true}));
'''
    completed = subprocess.run(
        ["node", "-e", node_test],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )
    require(completed.returncode == 0, (completed.stdout + completed.stderr)[-4000:])
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    require(result == {
        "summary": {"income": 1500, "expense": 225.5, "balance": 1274.5},
        "storage": True,
        "add": True,
        "delete": True,
    }, f"unexpected behavior result: {result}")
    print("AGENT-V1-WEB01 verified")


if __name__ == "__main__":
    main()
"""


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to replace frozen suite: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    init = '"""First formal local Agent project suite."""\n'
    task = {
        "task_id": "AGENT-V1-WEB01",
        "level": "project",
        "user_request": (
            "创建一个简洁好看的个人记账网页，可以记录收入和支出，自动显示所选月份的收入、支出与结余，"
            "支持删除记录；刷新后数据仍保存在 localStorage。只使用原生 HTML、CSS 和 JavaScript，提供 "
            "index.html、styles.css、app.js、README.md。不要修改 verify_app.py；完成前运行 python "
            "verify_app.py 并修复所有失败。为可测试性，app.js 必须暴露 window.LedgerApp，其中 "
            "calculateMonthlySummary(records, monthKey)、loadRecords(storage)、saveRecords(records, storage)、"
            "addRecord(records, record)、deleteRecord(records, id) 都是可在没有 document 时调用的函数；"
            "记录结构为 {id,type,amount,date,note}，月度汇总结构严格为 {income,expense,balance}。"
        ),
        "capabilities": [
            "medium_project_creation",
            "multi_file_web_implementation",
            "persistent_local_state",
            "test_driven_verification",
        ],
        "workspace_files": [{"path": "verify_app.py", "content": VERIFY_APP}],
        "workspace_generators": [],
    }
    tasks = {
        "schema_version": SCHEMA_TASKS,
        "suite": "RWKV-LH-AGENT-V1",
        "tasks": [task],
    }
    acceptance = {
        "schema_version": SCHEMA_ACCEPTANCE,
        "suite": "RWKV-LH-AGENT-V1",
        "cases": {
            "AGENT-V1-WEB01": {
                "checks": [
                    {"kind": "file_content", "path": "verify_app.py", "content": VERIFY_APP},
                    {"kind": "command_exit", "argv": ["python", "verify_app.py"], "exit_code": 0},
                    {
                        "kind": "directory_file_set",
                        "path": ".",
                        "files": ["README.md", "app.js", "index.html", "styles.css", "verify_app.py"],
                    },
                    {"kind": "file_contains", "path": "app.js", "text": "window.LedgerApp"},
                    {"kind": "file_contains", "path": "app.js", "text": "localStorage"},
                    {"kind": "event_min_count", "event_type": "attempt_started", "count": 5},
                    {"kind": "agent_process_tree_closed"},
                ]
            }
        },
    }
    files = {
        "__init__.py": init.encode("utf-8"),
        "tasks.json": canonical_json(tasks).encode("utf-8"),
        "acceptance.json": canonical_json(acceptance).encode("utf-8"),
    }
    for name, value in files.items():
        (OUTPUT / name).write_bytes(value)
    manifest = {
        "schema_version": "rwkv-agent-v1.manifest.v1",
        "dataset_id": "rwkv_agent_v1_project_suite",
        "version": "1",
        "source": "user-authorized RWKV-LH first formal local Agent capability matrix",
        "purpose": "mechanically verify a real medium multi-file personal-ledger web project",
        "generation": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "deterministic": True,
        },
        "task_count": 1,
        "task_ids": ["AGENT-V1-WEB01"],
        "file_sha256": {name: sha256_bytes(value) for name, value in sorted(files.items())},
        "acceptance_visible_to_agent": False,
        "public_verifier_visible_to_agent": True,
        "raw_output_modified": False,
    }
    (OUTPUT / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
    print(canonical_json({
        "output": str(OUTPUT),
        "task_count": 1,
        "manifest_sha256": sha256_bytes((OUTPUT / "manifest.json").read_bytes()),
    }), end="")


if __name__ == "__main__":
    main()
