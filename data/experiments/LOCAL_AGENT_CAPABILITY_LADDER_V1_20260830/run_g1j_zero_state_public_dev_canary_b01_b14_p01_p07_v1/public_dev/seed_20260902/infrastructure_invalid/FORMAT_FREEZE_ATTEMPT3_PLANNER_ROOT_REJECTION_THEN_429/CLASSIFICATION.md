# FORMAT_FREEZE_ATTEMPT3_PLANNER_ROOT_REJECTION_THEN_429

- 时间：2026-09-02（Asia/Shanghai）
- 用例：B01
- seed：20260902
- 分类：`MIXED_INVALID_PLANNER_PATH_CONTRACT_AND_UPSTREAM_SATURATION`
- 能力计分：不计分

第一条完整 Goal Planner HTTP 请求成功（200），但返回 patch 使用绝对 root `/workspace/probe_service`，被 workspace-relative 内核校验拒绝。控制器随后发起一次可见的 Goal patch 修复请求；中转站返回 429，脱敏错误正文指向当前分组上游负载饱和。RWKV 请求数与工具动作数均为 0。

本目录由固定结果路径可恢复移动而来，没有删除证据。没有修改模型、提示、采样参数、State 或输出参数。
