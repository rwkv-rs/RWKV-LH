# Harness Causal Closure P1/P2 V1 — 预注册

日期：2026-08-30（Asia/Shanghai）

## 来源与用途

- 来源：用户在当前 Codex 任务中提供的独立只读审查结论。
- 固定缺陷集：4 个 P1（finalizer 证据依赖、最终呈现验收、出站来源 fail-open、exclusive 失败写入）和
  3 个 P2（历史 supervisor pending、child action 半提交恢复、Contract Graph Shadow 投影）。
- 用途：修复完整 Harness 因果闭环的工程缺陷；本实验不评价或训练 RWKV，也不改变任何 RWKV 原始输出。
- 版本：`HARNESS_CAUSAL_CLOSURE_P1P2_V1_20260830`。缺陷集、判定口径和阈值在全量回归前冻结。

## 固定验证矩阵

| 缺陷 | 固定失败注入/场景 | 通过条件 |
|---|---|---|
| P1 finalizer 证据 | 初始 work + correction work + 旧 frozen finalizer | 可运行 finalizer 的依赖覆盖全部已完成 work；旧 finalizer 不进入 ready set |
| P1 最终呈现 | 第一个 exact RWKV Final 被 Reviewer contradicted | contradicted 后没有 `run_completed`；replacement Final 通过后才完成 |
| P1 出站来源 | 单文件预算、总预算、跳过目录、读取失败 | 全部标记 `unknown`，`auto_public` 全部拒绝 |
| P1 exclusive | `run_command` 写文件后非零退出 | 父 workspace 字节不变；写入只存在 atom snapshot |
| P2 pending | supervisor 故障后恢复，随后因 evidence stagnant 停止 | 旧 pending 有 resolved 事件；主动任务不再 retryable |
| P2 action 半提交 | 已有 `attempt_started`、缺少 `action_returned` 后恢复 | 同一 attempt 最终恰好 1 个 start、1 个 return |
| P2 Shadow | 只有 `atom_outcome_committed` child web action | Router 输入和 observed behavior 都包含 child action，不误标 `FINAL` |

## 固定指标与阈值

- 上述 7 类定向门：`7/7` 全过；任一失败即不完成。
- 原始输出完整性：不得新增任何改写、补全、截断、删除、重排或替换 RWKV raw output 的路径。
- 相关测试集：全部通过。
- 全项目测试：零失败。
- `git diff --check`：零错误。
- 产品连续性：`127.0.0.1:29610` 仍可达；不得停止或替换产品进程。

本轮是确定性工程整改，不使用相似度评分；统一判定算法为上述事件、依赖、字节与布尔不变量的精确比较。
运行后不得为改善结果修改这些口径。
