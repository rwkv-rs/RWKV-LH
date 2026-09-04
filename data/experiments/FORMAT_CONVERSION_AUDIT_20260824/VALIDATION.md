# 验证记录

日期：2026-08-24

## 分析脚本

使用绝对路径执行：

```text
uv run python /home/chase/GitHub/RWKV-LH/temp/analyze_round162_rwkv_format_distribution.py \
  --repo /home/chase/GitHub/RWKV-LH \
  --round-root /home/chase/GitHub/RWKV-LH/data/experiments/Round162_typed_contract_full90_20260823 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/FORMAT_CONVERSION_AUDIT_20260824
```

结果：exit 0；90 trace、500 SQLite、1,111 trace responses、1,111 SQLite decisions。

## 完整性断言

- 三个机器可读 JSON 均通过 `jq empty`。
- `cases=90`、`trace_generation_returned=1111`、`sqlite_decision_events=1111`。
- trace/DB 共有 request=1,111，trace-only=0，DB-only=0。
- raw output byte exact=1,111/1,111。
- trace commit/rollback 与 DB accepted/rejected=1,111/1,111。
- envelope distribution 加总=1,111；parser failures 加总=106；rejections 加总=154。
- accepted action 参数转换分母=520。
- 500 个数据库 `PRAGMA quick_check` 全部为 `ok`，`user_version` 全部为 3。

## 相关回归

第一次执行默认 pytest capture：

```text
uv run pytest -q tests/test_model_session.py tests/test_unified_controller.py
```

在 collection 前因 pytest capture 临时文件丢失退出，`no tests ran`；异常为
`FileNotFoundError` at `_pytest/capture.py`，不是用例断言失败。

关闭 capture 后原样重跑：

```text
uv run pytest -q -s tests/test_model_session.py tests/test_unified_controller.py
```

结果：`46 passed in 11.01s`。

分析脚本另通过 `uv run python -m py_compile`。

## 最终文件 SHA-256

```text
8552502d43553e3c98122a69204397b9080e6035fa13dd7e8f421c2b43117b9a  PROTOCOL.md
e0045d096091da2412466a3f5de6aca23388cc8ca3e8415f89fe831c59b207df  REPORT.md
af001c5c35866720c6331886aaab1ee6ac0d4205488b1f3b4caf3b6f7632d5c8  statistics.json
f1b7838e4a0ed6cc4c9c8a40b1923add8e61dd306eca226616194b9b1fe0ff1d  raw_examples.json
da65042dca956121a21933c0dd28b677ebc498b083916207d7fe351c2ab0210b  source_manifest.json
```
