# Round136 在线 GPT-5.4 可达纠正 canary 协议

日期：2026-08-22

上游：`Round135_ONLINE_GPT54_MICROTASK_SUPERVISOR_PROTOCOL.md` 与
`Round135_ONLINE_GPT54_MICROTASK_CANARY_ANALYSIS.md`。

## 固定改动

Round136 仅验证一个系统性控制器修复：online_microtask 模式提交新的纠正 directive 后，不再被
旧的全局 `identical_failure_budget_exhausted` 立即终止。循环由固定的 2 次相同零进展提前 review、
6-action wave、200 transitions 和 64 directives 继续限界。纯 RWKV 与静态 supervisor 路径不变。

专项测试必须证明 5 次相同失败已累计时，新的 GPT correction 仍能进入 RWKV lane 并产生后续
workspace mutation / Final。不得添加 case id、路径、文件内容或 hidden target 特判。

## 固定运行

- Cases：E2E-B01、E2E-M11、E2E-H17。
- Worker：`rwkv7-g1i-13.3b-20260805-ctx16384`，prompt replay，temperature 0.05。
- Supervisor：GPT-5.4，temperature 0.1，online_microtask。
- full tool disclosure（CLI 显式 pin）；actions/directive 6；max directives 64；max transitions 200。
- concurrency 3；frozen isolated verifier；GPT 无 action 权限、不可见 hidden acceptance、不可改写 Final。
- 输出目录：`Round136_online_gpt54_reachable_correction_canary_B01_M11_H17_20260822`。

## 固定 gate

1. 3/3 有效、0 running、无 supervisor transport/protocol failure。
2. B01 与 M11 均为 Strict TP。
3. H17 至少一次 workspace digest change，且在线纠正后不存在连续 5 次相同零信息 action；其
   External/Strict 结果必须报告，但不能替代前两题要求。
4. 每个 directive 只审一个新 action wave 或 Final；GPT action count 0；Final 保持 RWKV byte-exact。
5. 三题 protocol rejection 合计 <= 6；无题耗尽 64 directives 或 200 transitions。

只有五项全部满足才允许进入 Full90；Full90 晋级门槛沿用 Round135：TP > 36、FP <= 24、
FN <= 1、byte cases 5/5、90/90 有效且无分层 completion collapse。任一 canary gate 失败即停止。
