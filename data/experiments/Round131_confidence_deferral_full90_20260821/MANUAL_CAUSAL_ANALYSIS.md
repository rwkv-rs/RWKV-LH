# R131 首次 Full90 因果审计（实现无效，非正式筛选结果）

日期：2026-08-21  
协议：`Round131_FINAL_OPERATION_CONFIDENCE_DEFERRAL_PROTOCOL.md`  
冻结源：`Round131_source_manifest_20260821.json`，source tree SHA-256
`398e9a76b66723b944d5b53b2e269fb565b38f5eb118557c342f8377cdab3a1a`  
结论：**INVALID_IMPLEMENTATION；不得用本目录判定机制 KEEP/REVERT。**

## 1. 固定口径结果

- 90/90 完成记账，running=0；Strict/TP 34、FP 36、FN 0、OTHER 20。
- agent completed 70、interrupted 20；请求 2344、动作 2048、协议拒绝 198。
- 最终输出 90/90 非空且 90/90 与 RWKV 原始 Final 一致。
- 难度分组：basic 23 TP / 7 FP；medium 8 TP / 18 FP / 4 OTHER；hard 3 TP /
  11 FP / 16 OTHER。
- byte-precision 5/5：B01、B06、B13、B19、B28 全部 Strict 通过。
- 重建 R126 official TP 保留 33/36，损失 B17、M06、M30；R128 proxy 保留
  27/31，损失 B17、LH10、M11、M30。

这些分数只能描述“机制实际未运行时的一次随机复测”，不能作为 R131 机制效果。

## 2. 失效证据

全量审计中共有 70 个正常 action-lane `final_answer`，它们全部满足
`applicable=true`，但同时全部为：

- `metadata_available=false`
- `metric=null`
- `operation_token_count=0`
- `should_defer=false`

所以实际 deferral 为 **0**。与之相反，同一批终局的 model trace 明确记录请求了
`logprobs=1` 且 `logprobs_returned=true`。这排除了后端不支持或漏请求，定位到本地响应
归一化与跨度提取之间的数据一致性问题。

## 3. 根因与复现

本地 vLLM-RWKV 后端在命中 `\n\nUser:` 等 stop suffix 后，返回的 `choice.text` 已经
裁掉停止后缀，但 `choice.logprobs` 仍包含停止后缀 token。例如 B01 精确 checkpoint
复现中，正文 JSON 长度截止于 offset 101，logprob 仍包含 offset 101 的 `\n\n`、
offset 103 的 `User` 和 offset 107 的 `:`。

`LongHorizonModel._operation_span_logprobs()` 原本遍历整组 token。遍历到这些正文外 token
时，最后一个 token 的 `token_start` 大于裁剪后正文长度，触发 `token_end < token_start`
保护并丢弃此前已经正确选出的 `final`、`_`、`answer` 三个 logprob。因此 70/70 正常
Final 都被系统性判成元数据缺失。

根因位于通用 OpenAI-compatible 响应边界，而非题目、阈值、任务语义或 RWKV 状态机。

## 4. 冻结门判定

| Gate | 结果 | 证据 |
|---|---:|---|
| G1 byte 5/5 | PASS | 5/5 |
| G2 Strict ≥34 | PASS | 34 |
| G3 FP≤30/FN≤1/OTHER≤24 | **FAIL** | FP 36；FN 0；OTHER 20 |
| G4 90 valid、zero running | PASS | 90/90、0 running |
| G5 retention loss≤2 | **FAIL** | R126 loss 3；R128 loss 4 |
| G6 confidence 完整性 | **FAIL** | 70/70 applicable Final 元数据被误判缺失；0 firing |

即使忽略实现无效属性，本次也不满足 G3/G5/G6、没有 attributable FP→TP，不能 KEEP。
但因为被测机制从未执行，正式 R131 判定必须来自相同冻结阈值下的修复重跑。

## 5. 系统性修复与重跑隔离

修复位于 `rwkv_lh/runtime/openai_compat.py`：以实际返回正文长度为边界，同步裁掉所有
起始 offset 已在正文之外的尾部 logprob token，并记录
`logprobs_trailing_tokens_dropped`。没有改模型提示、采样、阈值、评分器、数据集、控制器
语义或 deferral 规则。

新增运行时回归覆盖“正文已被后端 stop 裁剪、logprob 仍带停止后缀”的真实形状。修复后：

- focused：19 passed；full：121 passed；compileall passed。
- B01 精确 checkpoint 在线复现中，跨度恢复为 3 个 operation token logprob。
- 修复源冻结为 `Round131_repaired_source_manifest_20260821.json`，source tree SHA-256
  `9a8e7c1a32ccea73e0e6edf37f944e03322e34173982eb7424d0ec443e217f9e`，66 项核对
  zero mismatch。
- 有效重跑输出目录：`Round131_confidence_deferral_repaired_full90_20260821`。

首次输出和 source manifest 保留不覆盖，供失效链路复核。
