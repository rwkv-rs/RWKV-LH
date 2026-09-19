#!/usr/bin/env python3
"""Generate the frozen ten-case real Agent capability ladder V1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1"
DATASET_OUTPUT = ROOT / "data/datasets/rwkv_lh_agent_capability_ladder_v1"
TASK_SCHEMA = "rwkv-agent-capability-ladder-v1.tasks.v1"
ACCEPTANCE_SCHEMA = "rwkv-agent-capability-ladder-v1.acceptance.v1"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


VERIFY_PRICING = r'''from __future__ import annotations

import math
from pathlib import Path

from pricing import final_price


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    cases = [
        ((100, 15), 85.0),
        ((19.99, 25), 14.99),
        ((8.335, 0), 8.34),
        ((10, 100), 0.0),
    ]
    for arguments, expected in cases:
        actual = final_price(*arguments)
        require(isinstance(actual, float), "final_price must return float")
        require(math.isclose(actual, expected, abs_tol=1e-9), f"{arguments}: {actual}")
    for arguments in [(-1, 5), (10, -1), (10, 101), (True, 10), (10, False)]:
        try:
            final_price(*arguments)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"invalid input accepted: {arguments}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("python verify_project.py" in readme, "README verification command missing")
    require("discount" in readme.casefold(), "README behavior missing")
    print("AGENT-LADDER-L1-FIX01 verified")


if __name__ == "__main__":
    main()
'''


PRICING_BUG = r'''from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def final_price(price: int | float, discount_percent: int | float) -> float:
    """Return a currency amount rounded with ROUND_HALF_UP."""

    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise TypeError("price must be numeric")
    if isinstance(discount_percent, bool) or not isinstance(discount_percent, (int, float)):
        raise TypeError("discount_percent must be numeric")
    if price < 0:
        raise ValueError("price must be non-negative")
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    # BUG: the percentage scale is wrong and binary float enters the Decimal path.
    multiplier = Decimal("1") - Decimal(str(discount_percent / 10))
    amount = Decimal(str(price)) * multiplier
    return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
'''


TRANSACTIONS = {
    "month": "2026-08",
    "transactions": [
        {"id": "T01", "type": "income", "amount": 3200.0, "category": "salary", "date": "2026-08-01"},
        {"id": "T02", "type": "expense", "amount": 52.4, "category": "food", "date": "2026-08-02"},
        {"id": "T03", "type": "expense", "amount": 180.0, "category": "rent", "date": "2026-08-03"},
        {"id": "T04", "type": "income", "amount": 480.5, "category": "freelance", "date": "2026-08-09"},
        {"id": "T05", "type": "expense", "amount": 25.6, "category": "transport", "date": "2026-08-11"},
        {"id": "T06", "type": "expense", "amount": 99.9, "category": "food", "date": "2026-08-18"},
        {"id": "T07", "type": "income", "amount": 17.0, "category": "refund", "date": "2026-07-30"},
    ],
}


VERIFY_DATA = r'''from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    source = json.loads((ROOT / "transactions.json").read_text(encoding="utf-8"))
    actual = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
    month = source["month"]
    rows = [item for item in source["transactions"] if item["date"].startswith(month)]
    income = round(sum(item["amount"] for item in rows if item["type"] == "income"), 2)
    expense = round(sum(item["amount"] for item in rows if item["type"] == "expense"), 2)
    categories: dict[str, float] = {}
    for item in rows:
        if item["type"] == "expense":
            categories[item["category"]] = round(categories.get(item["category"], 0) + item["amount"], 2)
    expected = {
        "month": month,
        "transaction_count": len(rows),
        "income": income,
        "expense": expense,
        "balance": round(income - expense, 2),
        "expense_by_category": dict(sorted(categories.items())),
    }
    require(actual == expected, f"summary mismatch: {actual!r} != {expected!r}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("transactions.json" in readme and "summary.json" in readme, "README inputs/outputs missing")
    require("python verify_project.py" in readme, "README verification command missing")
    print("AGENT-LADDER-L1-DATA01 verified")


if __name__ == "__main__":
    main()
'''


VERIFY_NOTES = r'''from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from notes_store import add_note, list_notes, load_notes, remove_note


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_cli(*arguments: str) -> object:
    completed = subprocess.run(
        [sys.executable, "notes_cli.py", *arguments],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=20,
        check=False,
    )
    require(completed.returncode == 0, completed.stdout + completed.stderr)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        db = Path(directory) / "notes.json"
        require(load_notes(db) == [], "missing database must load as empty")
        first = add_note(db, "book train", ["travel", "urgent"])
        second = add_note(db, "send report", ["work"])
        require(first["id"] == "N0001" and second["id"] == "N0002", "stable ids required")
        require([item["id"] for item in list_notes(db)] == ["N0001", "N0002"], "insertion order lost")
        require([item["id"] for item in list_notes(db, tag="travel")] == ["N0001"], "tag filter failed")
        require(remove_note(db, "N0001") is True, "existing note was not removed")
        require(remove_note(db, "N9999") is False, "unknown remove must be false")
        require([item["id"] for item in load_notes(db)] == ["N0002"], "persistence mismatch")

        cli_db = str(Path(directory) / "cli.json")
        added = run_cli("--db", cli_db, "add", "call bank", "--tag", "finance", "--tag", "urgent")
        require(added["id"] == "N0001", f"CLI add mismatch: {added}")
        listed = run_cli("--db", cli_db, "list", "--tag", "finance")
        require(isinstance(listed, list) and listed[0]["text"] == "call bank", "CLI list mismatch")
        removed = run_cli("--db", cli_db, "remove", "N0001")
        require(removed == {"removed": True, "id": "N0001"}, "CLI remove mismatch")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("notes_cli.py" in readme and "--db" in readme, "README CLI usage missing")
    print("AGENT-LADDER-L2-CLI01 verified")


if __name__ == "__main__":
    main()
'''


INVENTORY_INIT = '''from .service import InventoryService, InsufficientStock\n\n__all__ = ["InventoryService", "InsufficientStock"]\n'''


INVENTORY_STORAGE = r'''from __future__ import annotations

import json
from pathlib import Path


def load_inventory(path: str | Path) -> dict[str, int]:
    target = Path(path)
    if not target.exists():
        return {}
    value = json.loads(target.read_text(encoding="utf-8"))
    return {str(key): int(amount) for key, amount in value.get("stock", {}).items()}


def save_inventory(path: str | Path, stock: dict[str, int]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"stock": stock}, sort_keys=True) + "\n", encoding="utf-8")
'''


INVENTORY_SERVICE_BUG = r'''from __future__ import annotations

from pathlib import Path

from .storage import load_inventory, save_inventory


class InsufficientStock(ValueError):
    pass


class InventoryService:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def stock(self, sku: str) -> int:
        return load_inventory(self.path).get(sku, 0)

    def set_stock(self, sku: str, amount: int) -> None:
        values = load_inventory(self.path)
        values[sku] = amount
        save_inventory(self.path, values)

    def reserve(self, sku: str, amount: int) -> int:
        values = load_inventory(self.path)
        values[sku] = values.get(sku, 0) - amount
        save_inventory(self.path, values)
        if values[sku] < 0:
            raise InsufficientStock(sku)
        return values[sku]

    def release(self, sku: str, amount: int) -> int:
        values = load_inventory(self.path)
        values[sku] = values.get(sku, 0) + amount
        return values[sku]
'''


VERIFY_INVENTORY = r'''from __future__ import annotations

import json
import tempfile
from pathlib import Path

from inventory import InsufficientStock, InventoryService


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "stock.json"
        service = InventoryService(path)
        service.set_stock("A", 10)
        require(service.reserve("A", 4) == 6, "reserve result mismatch")
        require(InventoryService(path).stock("A") == 6, "reserve was not persisted")
        before = path.read_bytes()
        try:
            service.reserve("A", 7)
        except InsufficientStock:
            pass
        else:
            raise AssertionError("insufficient reservation was accepted")
        require(path.read_bytes() == before and service.stock("A") == 6, "failed reserve was not atomic")
        require(service.release("A", 3) == 9, "release result mismatch")
        require(InventoryService(path).stock("A") == 9, "release was not persisted")
        for method, arguments in [
            (service.set_stock, ("A", -1)),
            (service.reserve, ("A", 0)),
            (service.release, ("A", -2)),
        ]:
            try:
                method(*arguments)
            except (TypeError, ValueError):
                pass
            else:
                raise AssertionError(f"invalid amount accepted by {method.__name__}")
        value = json.loads(path.read_text(encoding="utf-8"))
        require(value == {"stock": {"A": 9}}, f"unexpected durable schema: {value}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("atomic" in readme.casefold() and "python verify_project.py" in readme, "README contract missing")
    print("AGENT-LADDER-L2-REPAIR01 verified")


if __name__ == "__main__":
    main()
'''


CATALOG_HTML = r'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>物品目录</title><link rel="stylesheet" href="styles.css"></head>
<body><main><h1>物品目录</h1><input id="search-input" aria-label="搜索"><select id="category-filter" aria-label="分类"></select><section id="item-list"></section><p id="empty-state">暂无结果</p></main><script src="app.js"></script></body>
</html>
'''


CATALOG_CSS = r''':root { color-scheme: light; --ink:#172033; --surface:#fff; --accent:#4f46e5; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,sans-serif; color:var(--ink); background:#eef2ff; }
main { width:min(960px,92vw); margin:3rem auto; padding:2rem; background:var(--surface); border-radius:18px; }
#item-list { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:1rem; }
.card { border:1px solid #dbe2f0; border-radius:12px; padding:1rem; }
'''


CATALOG_JS_BUG = r'''(function () {
  "use strict";
  const seed = [
    { id: "i1", name: "键盘", category: "办公", note: "机械轴" },
    { id: "i2", name: "咖啡杯", category: "生活", note: "陶瓷" }
  ];
  function normalizeItems(items) { return items; }
  function filterItems(items, query, category) { return items; }
  function editItem(items, id, patch) { return items; }
  function importItems(text) { return []; }
  function exportItems(items) { return "[]"; }
  window.CatalogApp = { normalizeItems, filterItems, editItem, importItems, exportItems, seed };
})();
'''


VERIFY_CATALOG = r'''from __future__ import annotations

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.assets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "link" and values.get("href"):
            self.assets.add(values["href"])
        if tag == "script" and values.get("src"):
            self.assets.add(values["src"])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    parser = Parser()
    parser.feed(html)
    required_ids = {"search-input", "category-filter", "item-list", "empty-state", "edit-dialog", "edit-form"}
    require(required_ids <= parser.ids, f"missing ids: {sorted(required_ids - parser.ids)}")
    require({"styles.css", "app.js"} <= parser.assets, "assets not wired")
    for token in ("@media", ":focus", "grid", "border-radius", "--"):
        require(token in css, f"CSS token missing: {token}")
    require(len(css) >= 900, "responsive styling is incomplete")
    for token in ("localStorage", "CatalogApp", "filterItems", "editItem", "importItems", "exportItems"):
        require(token in js, f"JavaScript token missing: {token}")
    node_test = r"""
const fs=require("fs"), vm=require("vm");
global.window={}; global.document=undefined;
global.localStorage={values:new Map(),getItem(k){return this.values.get(k)||null},setItem(k,v){this.values.set(k,String(v))}};
vm.runInThisContext(fs.readFileSync("app.js","utf8"),{filename:"app.js"});
const api=window.CatalogApp;
for (const name of ["normalizeItems","filterItems","editItem","importItems","exportItems"]) if(typeof api[name]!=="function") throw new Error(name);
const items=api.normalizeItems([{id:"a",name:"Blue Pen",category:"Office",note:"Fine"},{id:"b",name:"Mug",category:"Home",note:"Blue"}]);
if(api.filterItems(items,"blue","").length!==2) throw new Error("query filter");
if(api.filterItems(items,"","Office").map(x=>x.id).join()!=="a") throw new Error("category filter");
const edited=api.editItem(items,"a",{name:"Black Pen"});
if(edited[0].name!=="Black Pen"||items[0].name!=="Blue Pen") throw new Error("immutable edit");
const encoded=api.exportItems(edited), decoded=api.importItems(encoded);
if(JSON.stringify(decoded)!==JSON.stringify(edited)) throw new Error("import/export");
console.log(JSON.stringify({ok:true,count:decoded.length}));
"""
    completed = subprocess.run(["node", "-e", node_test], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30, check=False)
    require(completed.returncode == 0, completed.stdout + completed.stderr)
    require(json.loads(completed.stdout.strip().splitlines()[-1]) == {"ok": True, "count": 2}, "Node result mismatch")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("python verify_project.py" in readme and "localStorage" in readme, "README incomplete")
    print("AGENT-LADDER-L3-WEB01 verified")


if __name__ == "__main__":
    main()
'''


QUEUE_INIT = '''from .queue import DurableQueue\n\n__all__ = ["DurableQueue"]\n'''


QUEUE_STORAGE_BUG = r'''from __future__ import annotations

import json
from pathlib import Path


def load_state(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        return {"next_id": 1, "jobs": [], "completed": 0}
    return json.loads(target.read_text(encoding="utf-8"))


def save_state(path: str | Path, state: dict) -> None:
    Path(path).write_text(json.dumps(state) + "\n", encoding="utf-8")
'''


QUEUE_SERVICE_BUG = r'''from __future__ import annotations

from pathlib import Path

from .storage import load_state, save_state


class DurableQueue:
    def __init__(self, path: str | Path, max_attempts: int = 2) -> None:
        self.path = Path(path)
        self.max_attempts = max_attempts

    def enqueue(self, payload: dict) -> dict:
        state = load_state(self.path)
        job = {"id": f"J{state['next_id']:04d}", "payload": payload, "attempts": 0, "status": "queued"}
        state["next_id"] += 1
        state["jobs"].append(job)
        save_state(self.path, state)
        return job

    def claim(self) -> dict | None:
        state = load_state(self.path)
        queued = sorted((item for item in state["jobs"] if item["status"] == "queued"), key=lambda item: item["id"], reverse=True)
        if not queued:
            return None
        queued[0]["status"] = "inflight"
        return queued[0]

    def ack(self, job_id: str) -> bool:
        return False

    def fail(self, job_id: str) -> str:
        return "queued"

    def stats(self) -> dict[str, int]:
        state = load_state(self.path)
        return {name: sum(item["status"] == name for item in state["jobs"]) for name in ("queued", "inflight", "failed")} | {"completed": state.get("completed", 0)}
'''


VERIFY_QUEUE = r'''from __future__ import annotations

import tempfile
from pathlib import Path

from queue_app import DurableQueue


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "queue.json"
        queue = DurableQueue(path, max_attempts=2)
        first = queue.enqueue({"name": "A"})
        second = queue.enqueue({"name": "B"})
        require((first["id"], second["id"]) == ("J0001", "J0002"), "stable ids missing")
        claimed = queue.claim()
        require(claimed and claimed["id"] == "J0001", "claim is not FIFO")
        require(DurableQueue(path, 2).stats()["inflight"] == 1, "claim was not persisted")
        require(queue.fail("J0001") == "queued", "first failure must retry")
        require(queue.claim()["id"] == "J0002", "retry must move to queue tail")
        require(queue.ack("J0002") is True, "ack failed")
        restarted = DurableQueue(path, max_attempts=2)
        retried = restarted.claim()
        require(retried and retried["id"] == "J0001" and retried["attempts"] == 1, "retry state lost")
        require(restarted.fail("J0001") == "failed", "max attempts must dead-letter")
        require(restarted.claim() is None, "failed job was reclaimed")
        require(restarted.ack("missing") is False, "unknown ack must be false")
        require(restarted.stats() == {"queued": 0, "inflight": 0, "failed": 1, "completed": 1}, "stats mismatch")
        try:
            restarted.enqueue([])
        except TypeError:
            pass
        else:
            raise AssertionError("non-object payload accepted")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("FIFO" in readme and "retry" in readme.casefold(), "README queue semantics missing")
    require("python verify_project.py" in readme, "README verifier command missing")
    print("AGENT-LADDER-L3-QUEUE01 verified")


if __name__ == "__main__":
    main()
'''


VERIFY_LEDGER = r'''from __future__ import annotations

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.labels = 0
        self.assets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "label":
            self.labels += 1
        if tag == "link" and values.get("href"):
            self.assets.add(values["href"])
        if tag == "script" and values.get("src"):
            self.assets.add(values["src"])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    parser = Parser(); parser.feed(html)
    ids = {"entry-form", "entry-type", "entry-amount", "entry-date", "entry-note", "month-picker", "month-income", "month-expense", "month-balance", "entry-list", "empty-state"}
    require(ids <= parser.ids, f"missing ids: {sorted(ids-parser.ids)}")
    require(parser.labels >= 4 and {"styles.css", "app.js"} <= parser.assets, "accessible form/assets missing")
    require("viewport" in html and ('lang="zh-CN"' in html or "lang='zh-CN'" in html), "responsive Chinese document missing")
    for token in ("--", "@media", ":focus", "grid", "border-radius"):
        require(token in css, f"CSS token missing: {token}")
    require(len(css) >= 1200, "polished responsive CSS incomplete")
    for token in ("localStorage", "JSON.parse", "JSON.stringify", "calculateMonthlySummary", "loadRecords", "saveRecords", "addRecord", "deleteRecord", "window.LedgerApp"):
        require(token in js, f"JavaScript contract missing: {token}")
    node_test = r"""
const fs=require("fs"),vm=require("vm"); global.window={}; global.document=undefined;
global.localStorage={values:new Map(),getItem(k){return this.values.has(k)?this.values.get(k):null},setItem(k,v){this.values.set(k,String(v))},removeItem(k){this.values.delete(k)}};
vm.runInThisContext(fs.readFileSync("app.js","utf8"),{filename:"app.js"}); const api=window.LedgerApp;
for(const n of ["calculateMonthlySummary","loadRecords","saveRecords","addRecord","deleteRecord"]) if(typeof api[n]!=="function") throw new Error(n);
const rows=[{id:"r1",type:"income",amount:1500,date:"2026-08-03",note:"salary"},{id:"r2",type:"expense",amount:200,date:"2026-08-04",note:"food"},{id:"r3",type:"expense",amount:25.5,date:"2026-08-09",note:"train"},{id:"r4",type:"income",amount:99,date:"2026-07-31",note:"old"}];
const summary=api.calculateMonthlySummary(rows,"2026-08");
if(JSON.stringify(summary)!==JSON.stringify({income:1500,expense:225.5,balance:1274.5})) throw new Error(JSON.stringify(summary));
api.saveRecords(rows,localStorage); if(JSON.stringify(api.loadRecords(localStorage))!==JSON.stringify(rows)) throw new Error("storage");
const added=api.addRecord(rows,{id:"r5",type:"expense",amount:10,date:"2026-08-10",note:"tea"}); if(added.length!==5||rows.length!==4) throw new Error("add");
const deleted=api.deleteRecord(added,"r2"); if(deleted.length!==4||deleted.some(x=>x.id==="r2")) throw new Error("delete");
console.log(JSON.stringify({summary,ok:true}));
"""
    completed = subprocess.run(["node", "-e", node_test], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30, check=False)
    require(completed.returncode == 0, completed.stdout + completed.stderr)
    require(json.loads(completed.stdout.strip().splitlines()[-1])["ok"] is True, "Node verification failed")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("localStorage" in readme and "python verify_project.py" in readme, "README incomplete")
    print("AGENT-LADDER-L4-LEDGER01 verified")


if __name__ == "__main__":
    main()
'''


VERIFY_TRACKER = r'''from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tracker import IssueTracker


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def cli(*arguments: str) -> object:
    completed = subprocess.run([sys.executable, "tracker_cli.py", *arguments], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=20, check=False)
    require(completed.returncode == 0, completed.stdout + completed.stderr)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "issues.json"
        tracker = IssueTracker(path)
        one = tracker.create("Broken login", "high")
        two = tracker.create("Update copy", "low")
        require((one["id"], two["id"]) == ("I0001", "I0002"), "stable ids missing")
        require(tracker.close("I0001") is True and tracker.close("missing") is False, "close behavior wrong")
        require([item["id"] for item in tracker.list(status="open")] == ["I0002"], "status filter wrong")
        require(tracker.stats() == {"total": 2, "open": 1, "closed": 1, "high": 1, "medium": 0, "low": 1}, "stats wrong")
        export_path = Path(directory) / "export.json"
        require(tracker.export(export_path) == 2 and export_path.is_file(), "export failed")
        imported_path = Path(directory) / "imported.json"
        imported = IssueTracker(imported_path)
        require(imported.import_file(export_path) == 2, "import count wrong")
        require(imported.stats() == tracker.stats(), "import round trip wrong")
        try:
            tracker.create("bad", "urgent")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid priority accepted")

        cli_db = str(Path(directory) / "cli.json")
        created = cli("--db", cli_db, "create", "CLI issue", "--priority", "medium")
        require(created["id"] == "I0001", "CLI create wrong")
        listed = cli("--db", cli_db, "list", "--status", "open")
        require([item["id"] for item in listed] == ["I0001"], "CLI list wrong")
        stats = cli("--db", cli_db, "stats")
        require(stats["open"] == 1 and stats["total"] == 1, "CLI stats wrong")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for token in ("create", "close", "list", "stats", "export", "import", "python verify_project.py"):
        require(token in readme, f"README token missing: {token}")
    print("AGENT-LADDER-L4-TRACKER01 verified")


if __name__ == "__main__":
    main()
'''


VERIFY_PACKAGING = r'''from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    value = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    build = value.get("build-system", {})
    project = value.get("project", {})
    require(isinstance(build.get("requires"), list) and build["requires"], "build requirements missing")
    require(build.get("build-backend") == "setuptools.build_meta", "setuptools backend missing")
    require(project.get("name") == "evidence-demo" and project.get("version") == "0.1.0", "project identity wrong")
    require(project.get("requires-python") == ">=3.11", "Python requirement wrong")
    require(project.get("readme") == "README.md", "README metadata wrong")
    require(project.get("scripts", {}).get("evidence-demo") == "evidence_demo.cli:main", "CLI entry point wrong")
    sys.path.insert(0, str(ROOT / "src"))
    from evidence_demo import greet
    require(greet("Ada") == "Hello, Ada!", "package function wrong")
    try:
        greet("")
    except ValueError:
        pass
    else:
        raise AssertionError("empty name accepted")
    sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
    require("https://packaging.python.org/" in sources, "official packaging URL missing")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("evidence-demo" in readme and "python verify_project.py" in readme, "README usage missing")
    print("AGENT-LADDER-L5-PACKAGING01 verified")


if __name__ == "__main__":
    main()
'''


VERIFY_RWKV_SITE = r'''from __future__ import annotations

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.ids: set[str] = set(); self.assets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"): self.ids.add(values["id"])
        if tag == "link" and values.get("href"): self.assets.add(values["href"])
        if tag == "script" and values.get("src"): self.assets.add(values["src"])


def require(condition: bool, message: str) -> None:
    if not condition: raise AssertionError(message)


def main() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
    require(isinstance(data, list) and len(data) >= 3, "at least three resources required")
    require(all(set(item) == {"title", "category", "url", "summary"} for item in data), "resource schema wrong")
    require(len({item["url"] for item in data}) == len(data), "resource URLs must be unique")
    require(len({item["category"] for item in data}) >= 2, "at least two categories required")
    for item in data:
        require(item["url"].startswith("https://github.com/BlinkDL/"), f"non-official URL: {item['url']}")
        require(item["url"] in sources and len(item["summary"].strip()) >= 20, "source citation/summary missing")
    parser = Parser(); parser.feed(html)
    require({"search-input", "category-filter", "resource-list", "empty-state"} <= parser.ids, "UI ids missing")
    require({"styles.css", "app.js"} <= parser.assets and "viewport" in html, "assets/viewport missing")
    require(len(css) >= 900 and "@media" in css and ":focus" in css and "grid" in css, "responsive CSS incomplete")
    node_test = r"""
const fs=require("fs"),vm=require("vm"); global.window={}; global.document=undefined;
vm.runInThisContext(fs.readFileSync("app.js","utf8"),{filename:"app.js"}); const api=window.RWKVResources;
if(!api||typeof api.filterResources!=="function") throw new Error("API missing");
const rows=JSON.parse(fs.readFileSync("data.json","utf8"));
if(api.filterResources(rows,"rwkv","").length<1) throw new Error("query filter");
const category=rows[0].category; if(api.filterResources(rows,"",category).some(x=>x.category!==category)) throw new Error("category filter");
console.log(JSON.stringify({ok:true,count:rows.length}));
"""
    completed = subprocess.run(["node", "-e", node_test], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30, check=False)
    require(completed.returncode == 0, completed.stdout + completed.stderr)
    require(json.loads(completed.stdout.strip().splitlines()[-1])["ok"] is True, "Node verification failed")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("python verify_project.py" in readme and "SOURCES.md" in readme, "README verification/source usage missing")
    print("AGENT-LADDER-L5-RWKV01 verified")


if __name__ == "__main__":
    main()
'''


def task(
    task_id: str,
    level: str,
    request: str,
    capabilities: list[str],
    files: list[tuple[str, str]],
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "level": level,
        "user_request": request,
        "capabilities": capabilities,
        "workspace_files": [
            {"path": path, "content": content} for path, content in files
        ],
        "workspace_generators": [],
    }


def fixed_tasks() -> list[dict[str, object]]:
    return [
        task(
            "AGENT-LADDER-L1-FIX01",
            "tier1_closed_loop",
            "pricing.py 的折扣计算在生产样例中出现负数；公开验证器和函数接口已给出。不得修改 verify_project.py。请定位根因、修复通用计价与输入校验、补充 README，并在结束前运行 python verify_project.py 直到通过。",
            ["bug_diagnosis", "targeted_code_repair", "verification", "documentation"],
            [("pricing.py", PRICING_BUG), ("verify_project.py", VERIFY_PRICING)],
        ),
        task(
            "AGENT-LADDER-L1-DATA01",
            "tier1_closed_loop",
            "transactions.json 是不可修改的原始交易数据，month 指定统计月份。不得修改 transactions.json 或 verify_project.py。请生成 summary.json（精确字段由公开验证器定义）、补充 README 说明输入输出，并在结束前运行 python verify_project.py 直到通过。",
            ["data_inspection", "deterministic_transformation", "verification", "documentation"],
            [
                ("transactions.json", canonical_json(TRANSACTIONS)),
                ("verify_project.py", VERIFY_DATA),
            ],
        ),
        task(
            "AGENT-LADDER-L2-CLI01",
            "tier2_small_workflow",
            "需要一个只用 Python 标准库的持久化笔记工具。数据库是 JSON；函数接口为 load_notes、add_note、list_notes、remove_note，CLI 支持全局 --db 以及 add/list/remove 子命令，输出 JSON。不得修改 verify_project.py。请创建 notes_store.py、notes_cli.py、README.md，并运行 python verify_project.py 直到通过。",
            ["small_project_creation", "json_persistence", "cli_design", "verification"],
            [("verify_project.py", VERIFY_NOTES)],
        ),
        task(
            "AGENT-LADDER-L2-REPAIR01",
            "tier2_small_workflow",
            "inventory 包发生失败预留仍扣库存、release 刷新后丢失等事务缺陷；必须保持 inventory.__init__ 暴露的 API，只用标准库。不得修改 verify_project.py。请系统修复 storage.py/service.py 的校验、原子失败与持久化，补充 README，并运行 python verify_project.py 直到通过。",
            ["cross_file_bug_repair", "transaction_semantics", "persistence", "regression_verification"],
            [
                ("inventory/__init__.py", INVENTORY_INIT),
                ("inventory/storage.py", INVENTORY_STORAGE),
                ("inventory/service.py", INVENTORY_SERVICE_BUG),
                ("verify_project.py", VERIFY_INVENTORY),
            ],
        ),
        task(
            "AGENT-LADDER-L3-WEB01",
            "tier3_cross_file",
            "现有原生物品目录网页只有骨架。需要完善响应式界面、关键词与分类联合筛选、不可变编辑、JSON 导入导出和 localStorage 持久化；无 document 时仍暴露 window.CatalogApp 的公开纯函数。不得修改 verify_project.py。请协调修改 index.html、styles.css、app.js，补充 README，并运行 python verify_project.py 直到通过。",
            ["existing_web_extension", "multi_file_coordination", "persistent_state", "behavioral_verification"],
            [
                ("index.html", CATALOG_HTML),
                ("styles.css", CATALOG_CSS),
                ("app.js", CATALOG_JS_BUG),
                ("verify_project.py", VERIFY_CATALOG),
            ],
        ),
        task(
            "AGENT-LADDER-L3-QUEUE01",
            "tier3_cross_file",
            "queue_app 的持久队列在 claim、ack、fail 和重启后破坏 FIFO/重试语义。保持 DurableQueue API，只用标准库；失败任务移到队尾，达到 max_attempts 后进入 failed。不得修改 verify_project.py。请修复跨模块实现、补充 README，并运行 python verify_project.py 直到通过。",
            ["cross_module_repair", "durable_state_machine", "retry_semantics", "regression_verification"],
            [
                ("queue_app/__init__.py", QUEUE_INIT),
                ("queue_app/storage.py", QUEUE_STORAGE_BUG),
                ("queue_app/queue.py", QUEUE_SERVICE_BUG),
                ("verify_project.py", VERIFY_QUEUE),
            ],
        ),
        task(
            "AGENT-LADDER-L4-LEDGER01",
            "tier4_medium_project",
            "产品需要一个简洁好看的个人记账网页：原生 HTML/CSS/JavaScript，记录收入和支出，按所选月份自动显示收入、支出、结余，支持删除，刷新后 localStorage 数据仍在；纯函数在无 document 环境可测。不得修改 verify_project.py。请从零创建 index.html、styles.css、app.js、README.md，并运行 python verify_project.py 直到通过。",
            ["medium_project_creation", "responsive_web_ui", "persistent_local_state", "end_to_end_verification"],
            [("verify_project.py", VERIFY_LEDGER)],
        ),
        task(
            "AGENT-LADDER-L4-TRACKER01",
            "tier4_medium_project",
            "需要从零交付只用 Python 标准库的 issue tracker：tracker 包负责 JSON 持久化与 create/close/list/stats/export/import，tracker_cli.py 提供对应 JSON CLI，ID 稳定且支持状态筛选。不得修改 verify_project.py。请创建完整多文件项目和 README，并运行 python verify_project.py 直到通过。",
            ["medium_project_creation", "multi_module_architecture", "cli_and_persistence", "end_to_end_verification"],
            [("verify_project.py", VERIFY_TRACKER)],
        ),
        task(
            "AGENT-LADDER-L5-PACKAGING01",
            "tier5_networked_project",
            "需要依据当前官方 Python Packaging User Guide 创建一个 src-layout 示例包，项目名 evidence-demo、版本 0.1.0、Python >=3.11、setuptools 后端、CLI 入口 evidence-demo，并在 SOURCES.md 记录实际使用的官方证据 URL。不得修改 verify_project.py。请先使用 web_search 获取公开证据，再创建 pyproject.toml、src/evidence_demo/__init__.py、src/evidence_demo/cli.py、README.md、SOURCES.md，最后运行 python verify_project.py 直到通过。",
            ["public_web_retrieval", "evidence_grounding", "packaging_project_creation", "verification"],
            [("verify_project.py", VERIFY_PACKAGING)],
        ),
        task(
            "AGENT-LADDER-L5-RWKV01",
            "tier5_networked_project",
            "需要基于 BlinkDL 官方 GitHub 公开页面创建一个原生、响应式、可搜索和按分类筛选的 RWKV 资料网页。data.json 至少 3 条、至少 2 类，字段严格为 title/category/url/summary；SOURCES.md 必须逐条引用实际检索证据 URL。不得修改 verify_project.py。请先使用 web_search 检索真实证据，再创建 index.html、styles.css、app.js、data.json、README.md、SOURCES.md，最后运行 python verify_project.py 直到通过。",
            ["public_web_retrieval", "multi_source_evidence", "networked_web_project", "end_to_end_verification"],
            [("verify_project.py", VERIFY_RWKV_SITE)],
        ),
    ]


def case_acceptance(task_value: dict[str, object]) -> dict[str, object]:
    task_id = str(task_value["task_id"])
    files = {
        str(item["path"]): str(item["content"])
        for item in task_value["workspace_files"]  # type: ignore[index]
    }
    verifier = files["verify_project.py"]
    expected_files = {
        "AGENT-LADDER-L1-FIX01": ["README.md", "pricing.py", "verify_project.py"],
        "AGENT-LADDER-L1-DATA01": ["README.md", "summary.json", "transactions.json", "verify_project.py"],
        "AGENT-LADDER-L2-CLI01": ["README.md", "notes_cli.py", "notes_store.py", "verify_project.py"],
        "AGENT-LADDER-L2-REPAIR01": ["README.md", "inventory/__init__.py", "inventory/service.py", "inventory/storage.py", "verify_project.py"],
        "AGENT-LADDER-L3-WEB01": ["README.md", "app.js", "index.html", "styles.css", "verify_project.py"],
        "AGENT-LADDER-L3-QUEUE01": ["README.md", "queue_app/__init__.py", "queue_app/queue.py", "queue_app/storage.py", "verify_project.py"],
        "AGENT-LADDER-L4-LEDGER01": ["README.md", "app.js", "index.html", "styles.css", "verify_project.py"],
        "AGENT-LADDER-L4-TRACKER01": ["README.md", "tracker/__init__.py", "tracker/service.py", "tracker/store.py", "tracker_cli.py", "verify_project.py"],
        "AGENT-LADDER-L5-PACKAGING01": ["README.md", "SOURCES.md", "pyproject.toml", "src/evidence_demo/__init__.py", "src/evidence_demo/cli.py", "verify_project.py"],
        "AGENT-LADDER-L5-RWKV01": ["README.md", "SOURCES.md", "app.js", "data.json", "index.html", "styles.css", "verify_project.py"],
    }[task_id]
    checks: list[dict[str, object]] = [
        {"kind": "file_content", "path": "verify_project.py", "content": verifier},
        {"kind": "command_exit", "argv": ["python", "verify_project.py"], "exit_code": 0, "timeout": 60},
        {"kind": "directory_file_set", "path": ".", "files": expected_files},
        {"kind": "event_min_count", "event_type": "attempt_started", "count": 1},
        {"kind": "no_scope_violation_events"},
        {"kind": "agent_process_tree_closed"},
    ]
    network = task_id.startswith("AGENT-LADDER-L5-")
    if task_id == "AGENT-LADDER-L5-PACKAGING01":
        checks.insert(
            3,
            {
                "kind": "network_evidence_grounding",
                "operations": ["web_search", "connector_lookup"],
                "paths": ["SOURCES.md"],
                "required_hosts": ["packaging.python.org"],
                "min_successful_actions": 1,
                "min_records": 1,
                "min_cited_urls": 1,
            },
        )
    elif task_id == "AGENT-LADDER-L5-RWKV01":
        checks.insert(
            3,
            {
                "kind": "network_evidence_grounding",
                "operations": ["web_search", "connector_lookup"],
                "paths": ["data.json", "SOURCES.md"],
                "required_hosts": ["github.com"],
                "min_successful_actions": 1,
                "min_records": 2,
                "min_cited_urls": 2,
            },
        )
    return {
        "checks": checks,
        "runner_control": {
            "network_policy": "auto_public" if network else "offline",
            "network_explicit_approval": False,
            "network_public_workspace_paths": [],
        },
    }


def main() -> None:
    if OUTPUT.exists() or DATASET_OUTPUT.exists():
        raise SystemExit(
            f"refusing to replace frozen outputs: {OUTPUT}, {DATASET_OUTPUT}"
        )
    tasks_list = fixed_tasks()
    tasks = {
        "schema_version": TASK_SCHEMA,
        "suite": "RWKV-LH-AGENT-CAPABILITY-LADDER-V1",
        "tasks": tasks_list,
    }
    acceptance = {
        "schema_version": ACCEPTANCE_SCHEMA,
        "suite": "RWKV-LH-AGENT-CAPABILITY-LADDER-V1",
        "cases": {
            str(item["task_id"]): case_acceptance(item) for item in tasks_list
        },
    }
    output_files = {
        "__init__.py": b'"""Frozen real Agent capability ladder V1."""\n',
        "tasks.json": canonical_json(tasks).encode("utf-8"),
        "acceptance.json": canonical_json(acceptance).encode("utf-8"),
    }
    OUTPUT.mkdir(parents=True)
    for name, payload in output_files.items():
        (OUTPUT / name).write_bytes(payload)
    script_path = Path(__file__).resolve()
    benchmark_manifest = {
        "schema_version": "rwkv-agent-capability-ladder-v1.manifest.v1",
        "dataset_id": "rwkv_lh_agent_capability_ladder_v1",
        "version": "1",
        "source": "user-authorized real local Agent workflows with deterministic synthetic seeds",
        "purpose": "measure contiguous end-to-end Agent capability independently of Full90 component diagnostics",
        "generation": {
            "script": str(script_path.relative_to(ROOT)),
            "script_sha256": sha256_bytes(script_path.read_bytes()),
            "deterministic": True,
        },
        "task_count": len(tasks_list),
        "levels": {
            level: sum(item["level"] == level for item in tasks_list)
            for level in (
                "tier1_closed_loop",
                "tier2_small_workflow",
                "tier3_cross_file",
                "tier4_medium_project",
                "tier5_networked_project",
            )
        },
        "task_ids": [item["task_id"] for item in tasks_list],
        "file_sha256": {
            name: sha256_bytes(payload)
            for name, payload in sorted(output_files.items())
        },
        "acceptance_visible_to_agent": False,
        "public_verifier_visible_to_agent": True,
        "holdout_excluded_from_state_tuning": True,
        "raw_output_modified": False,
    }
    manifest_payload = canonical_json(benchmark_manifest).encode("utf-8")
    (OUTPUT / "manifest.json").write_bytes(manifest_payload)

    benchmark_hashes = {
        name: sha256_bytes((OUTPUT / name).read_bytes())
        for name in ("__init__.py", "tasks.json", "acceptance.json", "manifest.json")
    }
    dataset_manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_id": "rwkv_lh_agent_capability_ladder_v1",
        "version": "1",
        "source": "user-authorized capability requirements; deterministic local fixtures; runtime public evidence is not copied into the dataset",
        "purpose": "frozen ten-case holdout for real Agent capability ceiling and state-tuning regression measurement",
        "generation": {
            "script": str(script_path.relative_to(ROOT)),
            "script_sha256": sha256_bytes(script_path.read_bytes()),
            "command": "uv run python scripts/generate_agent_capability_ladder_v1.py",
        },
        "task_count": len(tasks_list),
        "benchmark_files_sha256": benchmark_hashes,
        "split": "holdout_only",
        "state_tuning_eligible": False,
        "similarity_guard": {
            "algorithm": "UTF-8 byte 5-gram cosine",
            "maximum_train_dev_holdout_similarity": 0.95,
        },
    }
    dataset_readme = f'''# RWKV-LH Agent Capability Ladder V1

- 来源：用户授权的真实本地 Agent 工作流；seed 由确定性脚本合成，未复制外部语料。
- 版本：1（2026-08-30 冻结）。
- 用途：独立于 Full90，测量五层连续端到端能力上限；仅作 holdout，禁止进入 state tuning。
- 生成：`uv run python scripts/generate_agent_capability_ladder_v1.py`。
- 任务：10（每层 2）；本地 8，联网 2。
- tasks SHA-256：`{benchmark_hashes["tasks.json"]}`。
- acceptance SHA-256：`{benchmark_hashes["acceptance.json"]}`。
- 评价：byte-exact、公有 verifier、隔离隐藏 checker、真实 evidence URL 交集；不得按结果修改口径。
'''
    DATASET_OUTPUT.mkdir(parents=True)
    (DATASET_OUTPUT / "README.md").write_text(dataset_readme, encoding="utf-8")
    (DATASET_OUTPUT / "manifest.json").write_text(
        canonical_json(dataset_manifest), encoding="utf-8"
    )
    print(
        canonical_json(
            {
                "output": str(OUTPUT),
                "dataset_record": str(DATASET_OUTPUT),
                "task_count": len(tasks_list),
                "tasks_sha256": benchmark_hashes["tasks.json"],
                "acceptance_sha256": benchmark_hashes["acceptance.json"],
                "manifest_sha256": benchmark_hashes["manifest.json"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
