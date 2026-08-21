# R132 empty-pool canonical baseline assembly record

日期：2026-08-21  
依据：`Round132_TERMINAL_COMBINATION_RECORD_ATTEMPT_PROTOCOL.md` §1–§5  
选择：**EMPTY-POOL FALLBACK；不组合任何 R129–R131 新机制。**

## 1. 锁定选择规则的机械应用

- R129 homogeneous decomposition：REVERT / EXCLUDED（Strict 36→28、0 attributable FP→TP、
  completion collapse）。
- R130 order-permutation ensemble：REVERT / EXCLUDED（Strict 33、FP31、FN1、OTHER25、
  byte4/5、因果帮助未证明）。
- R131 confidence deferral：REVERT / EXCLUDED（有效 Full90 35/29/0/26；9 次 firing 全部
  立即再次 Final、0 intervening direct action、0 attributable FP→TP；G3/G5 失败）。

因此 eligible ingredient 集为空。按 §3，R132 不是组合轮，而是当前 best canonical
baseline 的新鲜 Full90；不得新增机制。

## 2. REVERT 后源边界

`scripts/run_rwkv_e2e_benchmark.py` 已恢复为 R130 repaired canonical 的 byte-exact 版本：
SHA-256 `3e0febb547880378845b61fef967ff4aba4b106998d7807f4159095311ac439e`。
它使用 `LongHorizonModel(session, harness=harness)`，不显式启用任何实验变量。

与 R130 order-ensemble 的 REVERT 处理一致，R131 的实验实现和测试保留在 generic
default-off 边界后供复核，不构成 active ingredient：

- `enable_order_ensemble == false`
- `enable_confidence_deferral == false`
- 默认路径不请求 logprobs、不执行 deferral、不执行 K=3

这些 dormant plumbing 不改变 assignment、tool definitions、bootstrap、sampling、动作状态机
或 Final 语义；R132 的 active behavior diff 相对 R130 repaired canonical 为零。

## 3. byte / behavior fidelity

用 R130 repaired B01 的相同 literal request、约束、空 workspace 和当前默认模型重新渲染
bootstrap：

- reference/current transcript SHA-256 均为
  `5225e07a0d686b343072e7c6cb446b04dc80fa5983e1aee4362efedfac922564`
- reference/current chars 均为 9,587
- reference/current local tokens 均为 2,177
- 全部 transcript bytes 相等
- 两个实验开关均为 false

验证脚本：`temp/verify_r132_canonical_prompt_fidelity_20260821.py`。

## 4. 离线 gate

- Full pytest：121 passed。
- compileall：passed。
- 固定 catalog：90/90，registry/definitions↔handlers 由全套测试覆盖。
- R132 active ingredient：空集；无 composition interaction。
- 数据集、模型、采样、阈值、并发 1、max-transitions 200、prompt replay、逐题 worker
  回收均不变。

下一步先生成并 `--check` R132 read-only source manifest，再启动一次新目录 Full90。
