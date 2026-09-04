# RWKV-LH 当前交接

更新时间：2026-09-04（Asia/Shanghai）

G1J 五个角色数据集已经生成，但尚未训练或选择 State。旧的混合 State、旧 checkpoint、旧 profile、旧兼容运行和旧发布结论均不继承。旧 Selector Head 因 feature 轨迹身份错误已明确淘汰。

当前固定状态：

```text
state_tuning_status: DATASETS_BUILT_HEAD_RETRAIN_REQUIRED
formal_dataset_count: 5
trained_stage_count: 0
selected_state_count: 0
runtime_state_profile_count: 0
```

新的唯一边界是五个独立模型环节：Selector / Intent、Executor-Args、Step Auditor、Finalizer、Final Auditor，外加不调用模型的 Controller Mechanical Evidence Gate。Goal 是持续运行模式，不是全局 State 或控制面。只有 Selector 选择 `final_answer`、Finalizer 生成 candidate 且 Final Auditor 返回 `ready_for_final` 时才能完成。Executor 每个 action 使用干净 State；Selector 只在一个 `(step_id, step_revision)` 内持续 parent WKV，跨 step/revision 和 Final 边界重置。新 Head 的 `persistent-causal-sequences.v1` 必须按这一局部 scope 生成。

最新 baseline 为 `0/20`，选择分布为 `list_directory=1044`、`move_file=80`。下一步不是调 13.3B 参数，而是先建立与 `GoalFrontierStateV1` 完全同分布的 Selector 持久轨迹、训练 Head v2，然后按原固定 Ladder 重跑。

架构整改、精确数据格式、生成算法、切分、训练参数、指标和停止条件统一以 [G1J 分环节 State Tuning 冻结实施协议](G1J_STATE_TUNING_AUDIT_HANDOFF_20260902.zh-CN.md) 为准。未写入该协议的字段、转换、retry、阈值和训练参数不得临场添加。
