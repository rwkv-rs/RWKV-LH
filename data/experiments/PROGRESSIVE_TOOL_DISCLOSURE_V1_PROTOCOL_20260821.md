# Progressive Tool Disclosure v1 — 预注册消融协议

## 状态

- 登记时间：2026-08-21（Asia/Shanghai）
- 当前状态：代码与离线回归完成；模型端问题解除前不启动 canary 或 Full90
- 目标：比较 R126 全量工具 Schema 披露与“两阶段工具选择 → 单工具 Schema 披露”
- 禁止事项：运行后不得修改数据集、验收器、阈值、采样参数或评价口径来改善结果

## 固定数据集

来源均为仓库内版本化 benchmark package，由 `scripts/run_rwkv_e2e_benchmark.py --suite all` 按 core30、lh12、extension48 固定顺序装载，共90题。

| 文件 | SHA-256 | 用途 |
|---|---|---|
| `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json` | `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c` | 基础/中等30题可见任务 |
| `benchmarks/rwkv_e2e/rwkv_e2e_30/acceptance.json` | `c4953c556a9ba2e080493f34bb2261db349080542376c4e94f08d5227e0f74cd` | core30隐藏验收 |
| `benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json` | `d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e` | 长流程12题可见任务 |
| `benchmarks/rwkv_e2e/rwkv_e2e_lh12/acceptance.json` | `976e075bcc81780ed38ce7b9fe8c6c19c1b239bb72595ce176308f2760a0cd9f` | lh12隐藏验收 |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json` | `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b` | 扩展48题可见任务 |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/acceptance.json` | `395e1651f52259de7e56a63476504891f136edd2d4dd5a8263064077741ede12` | extension48隐藏验收 |

生成方式：仓库既有固定任务与隐藏验收直接读取，不重新生成；每次运行前复核以上摘要。

## 固定对照

除工具披露模式外，两组使用相同源码、模型、endpoint、采样参数、并发数、超时、任务顺序和外部验收器。

- A（基线）：`RWKV_TOOL_DISCLOSURE_MODE=full`
  - R126兼容的启动时完整 Schema 披露。
- B（实验）：`RWKV_TOOL_DISCLOSURE_MODE=progressive`
  - 第1阶段只提供名称和一句作用简介，模型返回 `select_tool`。
  - 控制器验证名称后，第2阶段只注入所选工具的完整参数 Schema。
  - Schema 位于临时 User/Controller 披露段，不进入 System 工具列表。
  - 参数协议拒绝仅重试已披露工具，不重新选择、不重复 Schema。
  - 成功动作的 observation 进入状态后执行确定性 rollover，后续选择提示不保留旧详细 Schema。

固定运行参数沿用 R126 正式口径：temperature `0.05`、top_p `1.0`、top_k `0`、presence/frequency penalty `0`、penalty_decay `0.996`、Full90 concurrency `1`。实际模型标识、endpoint能力摘要和源码 commit 必须写入运行产物。

## 固定指标与算法

主指标：Strict TP、FP、FN、OTHER，以及90/90有效性。Strict 仅由既有隐藏外部验收器判定，不以模型自述或人工主观相似替代。

辅助指标：

- Agent completed
- model requests（分别统计 selection/action）
- executed actions
- protocol rejections（selection 与 parameter 分开）
- 每题及总 prompt tokens、generation tokens
- wall time、MemoryPeak、SwapPeak
- raw RWKV Final byte exact；使用 UTF-8 原始字节 SHA-256，相同摘要视为相同，不采用模糊匹配

所有结构化产物继续使用既有 JSON/文件 verifier；不得新增后处理改写 RWKV 的 operation、arguments 或 final text。

## 分阶段运行与门槛

1. 离线回归：全仓单元测试必须通过。
2. 固定 canary：`B01,B02,B10,M03,M12,H10`，A/B 各运行一次；任一组 transport invalid 则作废并同条件重跑，不得只重跑失败题。
3. Full90：仅 canary 两组均6/6协议有效（不要求6/6 Strict）后启动；A/B各完整运行一次。
4. 确认复跑：B达到采纳门槛后，同源同参数完整复跑一次。

采纳 B 的必要条件：

- B首次及确认复跑均90/90有效；
- Strict 均不低于 R126 confirm 的34；
- 两次中至少一次 Strict 不低于 R126 official 的36；
- FP 两次均不高于30，FN均不高于1；
- parameter protocol rejection 相对同次A下降至少20%；
- 没有新增作用域、安全、幂等、崩溃恢复或原始字节投影回归。

若未满足全部条件则保持 `full` 为正式基线，`progressive` 只保留为实验能力。模型请求数预计上升，不能用 token/延迟改善替代 Strict 与安全门槛。

## 当前实现验证

- 针对性回归：`tests/test_model_session.py` 与 `tests/test_unified_controller.py`，45项通过；全仓120项通过。
- 已验证：System不包含工具名称/Schema、菜单不含参数、只披露一个精确 Schema、参数拒绝不重新选择、旧 `full` 路径兼容。
- 未验证：真实 RWKV 对 `select_tool` 协议的服从率、Full90 Strict/FP、实际 token 与时延变化。
