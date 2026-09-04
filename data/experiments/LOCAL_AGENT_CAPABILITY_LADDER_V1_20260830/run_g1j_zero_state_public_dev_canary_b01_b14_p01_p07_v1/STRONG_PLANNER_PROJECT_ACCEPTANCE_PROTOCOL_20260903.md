# P01-P07 Strong Planner 项目级验收冻结

冻结日期：2026-09-03（Asia/Shanghai）  
原始题目附件 SHA-256：`0252043c5f55745f3650881bf77b077ba04ffd27238332ea321a029578b8c68c`

## 输入身份

| Case | UTF-8 task SHA-256 |
|---|---|
| P01 | `d9441b4740cdf121cd094f16fa231f9f48b3752255be692bfa7f0d34526cfe6a` |
| P02 | `d61b39ed1eaeb71cf0582d487ef81a6ceaa581c9d3c4777da66371c1b479ce4e` |
| P03 | `9f245b354e03198c83921940be85261e9ae12a3041d16fcbddf84d49de1a8eec` |
| P04 | `03c391f7cd5bcc328305e77c63e943de6a2ddcc88215de49162d7d237307ed22` |
| P05 | `5328073c36a938095e53f9f884b21fa5c3e202e056148f89d83d542b2aaf7511` |
| P06 | `a42575979104c6404235a0aed03fc6bb08176431948b5190684050d04a7aa5d4` |
| P07 | `a3b831946fc6d9dd105bd2063ef7e94ace4bddc21c41c1aad2540feba9f29971` |

每个 task 均从用户附件的对应 ` ```text` 块直接提取并先校验附件哈希；输入中不添加实验绝对路径、隐藏检查、参考答案或额外路径强调。

## 固定目录与运行

- 固定母路径：本实验目录下 `strong_planner_projects/`。
- 单次 workspace：`strong_planner_projects/seed_<label>/cases/STRONG-PLANNER-P<nn>-S<label>/workspace`。
- 初始 workspace 必须为空；各 case、各 run label 互相隔离。
- run label 为 `20260902`、`20260903`、`20260904`，不作为模型 seed 参数发送。
- 模型、State、Strong Planner、Stage Checker、prompt、采样、工具菜单和 240 transitions 上限完全沿用 `SUITE_EXECUTION_PROTOCOL_20260903.md`。

## 独立验收

隐藏 acceptance 仅在 Agent 阶段结束后，通过 stdin 送入只读 workspace snapshot 的 bubblewrap verifier；Agent 看不到代码和结果。每题固定包含：

1. 包、README、测试覆盖、必要实现概念和 CLI surface 的独立探针；
2. 运行项目完整 `pytest -q`，但不把 Agent 自写测试作为唯一依据；
3. case 专用黑盒：P01 提交/执行/状态，P02 非法 JSON fail-closed，P03 所有修改命令的 idempotency CLI 合同，P04 真实临时仓库 AST impact，P05 plan 只读性，P06 REST/UI/审计/冲突/浏览器测试表面，P07 真实示例首次构建和零重建 explain；
4. 首次已应用 Agent 文件副作用后强制崩溃，并以同一 run store 恢复；
5. `attempt_started`、无 scope violation、Agent 进程树关闭；
6. Runner 生成 workspace 全文件 SHA-256 清单，作为运行后独立摘要审计的一部分；
7. 非空 RWKV `final_answer`、Final Auditor ready、全部外部检查通过才允许 `full_task_success=true`。

冻结代码：

- fixture：`33eea09e2b3c648a5ff05deceb3af12bce33a41b1c9c77f224f2bac42a0925aa`
- single runner：`65f09705ea1659070236f7f74d9a913e26af3a422468007df19683767e143cc5`
- suite runner：`09cdf442bffbb96481b2f3f8f3164148410d9041a9c1e37e7d37558b4f0dd3d2`

运行开始后不修改验收、阈值或推理参数。基础设施失败单列且不进入能力分母；模型错误、协议错误、错误工具、错误参数、未完成和 transition budget 耗尽均保留为有效能力结果。
