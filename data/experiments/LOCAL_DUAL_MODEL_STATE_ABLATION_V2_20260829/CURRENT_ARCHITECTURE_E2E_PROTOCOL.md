# 当前 2.9B Selector + 13.3B Executor E2E 协议

登记时间：2026-08-29（Asia/Shanghai），在 EXE-G2-V3-RL checkpoint 评测与当前架构 E2E
产生结果之前。

## 冻结比较

- `RL00`：正式 `SEL-Z0-S39` + `EXE-Z0-V3-RL`。
- `RL01`：同一 `SEL-Z0-S39` + 按完整 dev480 选择的 `EXE-G2-V3-RL` 最早终端全分平台点。
- 不启用强 Planner、旧 State Router、13.3B 工具选择回退、guided/constrained decoding 或输出 repair。
- 两组分别使用新目录；不能重用、覆盖或只重跑失败行。

## 固定输入与 raw 合同

每个实际 Executor generation 的 input checkpoint 都必须满足：不可变当前要求精确出现一次；正常
输入的闭合 `current_requirement` 是最后字段，紧接续写锚点；协议重试则最新 rejection event 位于
要求之后并成为续写点前的直接原因。Selector 保持 S39 V3 字节布局。所有 Executor raw HTTP
response/text/token IDs/finish reason/SHA 与 Selector 全 25 logits 在解析前或 handoff 前原样持久化，
不得修改、删除、替换、隐藏或按结果重试。

## 固定集合

1. 本地 canary：`E2E-B01,E2E-B02,E2E-B10,E2E-M03,E2E-M12,E2E-H10`。
2. 冻结真实联网 2 例：显式 URL→证据→Markdown，以及 GitHub structured connector→证据→JSON；
   数据 SHA-256 `971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708`。
3. Canary 通过后运行完整 90-case 历史集，不删除 `E2E-LH09`。该例需要 benchmark-only
   `mock_api`，不在正式 25 类/23 product operation 菜单内；若失败，必须标成已知结构不兼容，
   不能加特判或由 13.3B 绕过 Selector。

## 判定

- Canary 两组均须 transport/protocol 6/6；比较 Strict、动作数、wall p50/p95 与 handoff mismatch。
- 联网 tuned 组必须 2/2 完成、使用预期 network operation、证据 envelope committed、产物机械通过，
  且逐 generation 输入布局与 raw/25-logit 完整性 100%。zero 组作为质量差分，失败也完整保留。
- Full90 全部运行并如实报告 product-compatible 89 例与 benchmark-only `mock_api` 例；任何新的同类
  失败必须扩展检查，不能改变验收器。
- E2E 与回归通过后才能把选中的 Executor profile 标成产品 accepted；否则保持候选。
