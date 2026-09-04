# G1J 全 zero State 基线：next-state 整改后 B01 重跑预注册

登记时间：2026-09-03（Asia/Shanghai）  
性质：架构污染整改后的首次真实 Agent 基线重跑；不是训练、Head 训练或 StateTune。

## 固定对象

- 用例：`PUBLIC-CANARY-B01-S20260903`。
- 固定输出母路径：`data/experiments/LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_g1j_zero_state_public_dev_canary_b01_b14_p01_p07_v1/public_dev/seed_20260903/`。
- 运行前该 seed 目录只含空 `cases/` 目录，没有历史结果、数据库或工作区。
- runner：`temp/run_g1j_zero_public_canary_baseline_v1.py`，SHA-256 `ab44d4537ad2df6fb01ef9d0dd457e7be4bda8409d706f75c6102f3b256280b2`。
- 扩展 fixture：`temp/g1j_public_canary_fixtures_v1.py`，SHA-256 `3f335bb8f5057d4547b090a4fcc21ce586f96bf7a2f95a47030b4ad57225b80d`。
- 最大 Goal transitions：240。
- 网络策略：offline；不得向公网发送工作区内容。
- Planner：`gpt-5.6-sol`；Stage Checker：`claude-opus-4-6`。
- Strong 请求只使用 `json_object`；不发送 temperature、seed 或 reasoning 参数。
- Planner cache 关闭；fallback 关闭；semantic repair 0；runner 内 transport retry 固定为 1。
- Selector：G1J 2.9B + 既有固定 Head；Executor、Step Auditor、Finalizer、Final Auditor：G1J 13.3B。
- 五个角色的 State profile SHA-256 均为 64 个 `0`；不得加载任何训练 State。
- 唯一生成续写格式：`PromptV1` + `**Tool Call:**` + ` ```json`；不得混入 `Assistant: ```json`。

## 本次全局整改边界

1. Selector 首边界从 zero State 启动，后续边界只继承上一 Selector checkpoint；禁止跨角色 WKV。
2. 保留 `selector-intent.v1` 外层 JSON 字段和 Head 标签顺序；当前 Planner step、该 step 的最新 Harness action/result、最新 audit feedback、真实 completed stage 数和当次 eligible 工具名/描述，统一编码在 `GoalFrontierStateV1` 的 `stage_objective` 字符串中。
3. Executor 参数协议拒绝后复用已经消费的 selection 和已披露 schema；不得重新调用 Selector。
4. Step/Final Auditor 当前问题显式要求输出全部六个语义字段；转换层仍不得补造缺失字段。
5. 不添加 B01 路径、答案、启动入口、端口或测试命令特判。

## 代码身份

- `runtime_projection.py`: `1048136fda5b0aa77640d9d1cb87ce011a51d3c465427fb501ec0a79daa0e9d3`
- `network_client.py`: `0ebf3f20817b1c9ea1ba6ca0579000fbec9398ad46f43b55cd06911bd9c2bdaf`
- `network_service.py`: `587903da2d61df6f8a12ff703154d42456b89e5b7923c2d80b2ddc8da297cb2e`
- `model.py`: `33def87ce3758f2c9eebdc3ee65758ea64447df8161ad9c932f2aa64d91c2c2c`
- `stateful_goal_loop.py`: `1e7d59c368c72b9ac0ac3c31d5de54cfe7c4a0b686fb9d99b6f2d1d862ae49f0`
- `auditor_step.py`: `5dcd2e7e3fed5ffa13cfb3dc848a81eb0f5308b6c65efd7ae9c8af008420d9af`
- `auditor_final.py`: `0c5df6d431a92ad09c95c98ddea209da2e680f48246f13ac9d2042fe7024ca21`

## 运行前门槛

- 定向 next-state、服务 continuation、格式、Goal loop 回归：55/55 通过。
- 全工程首轮：811 通过、1 个过期的 Planner v1 测试断言失败；代码已经使用 v2，断言已更新为 v2，必须在基线结论前完成全工程重跑。
- 远端服务源码 SHA-256 必须与上方 `network_service.py` 相同。
- live parent probe 必须同时满足 parent digest 相等、token position 增长、checkpoint parent 绑定、zero profile 不变。

## 固定评价口径

B01 的语义通过条件在运行前冻结，沿用 runner 中的原评价函数，不按结果修改：最终回答必须同时包含 `probe-service`、`probe_service.cli:main`、`8127`、`python -m pytest -q --strict-markers tests`、`README.md`、`pyproject.toml`、`probe_service/settings.py`，并同时报告 README 中 `7000` 与实际项目配置/代码之间的冲突。

有效完整通过还要求：

1. RWKV 原生生成非空且通过只做信封归一化的调用；
2. 真实工具作用于固定 case workspace；
3. action observation 和 audit feedback 可追踪进入后续状态；
4. rolling plan 的所有 step 与 stage 均由合法 Step Audit evidence 完成；
5. RWKV Finalizer 显式生成非空 `final_answer`；
6. RWKV Final Auditor 返回合法 `ready_for_final` 后才允许 `status=completed`；
7. 外部 checks 全部通过，且上面的语义 token/conflict 检查通过。

主要分数是固定二值 `full_task_success`。诊断指标固定记录：各 operation 计数、Selector 父状态绑定率、同 step 重复 observation 比率、Executor 协议拒绝数、Auditor parse/accept 数、完成 step/stage 数、Finalizer/Final Auditor 是否到达。不得在看到结果后改变通过阈值。

本次不是相似度优化或 StateTune 消融，能力通过不使用主观相似度。数据隔离沿用数据集登记的 UTF-8 byte 5-gram cosine，train/dev/holdout 最大允许相似度 0.95；不得将本用例或运行轨迹写回 train/dev。
