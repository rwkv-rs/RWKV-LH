# Round61 预注册协议：post-Task Goal-effect binding

## 假设

Round60 证明 Task-local evidence handoff 能修复 B01、M03、M12，但把 criterion 数组加入主 Task batch 会扰动弱模型的执行规划，并且模型常把所有 `satisfies_criteria` 留空。恢复五字段执行 Task，在一个 Task 已有真实 action observation 且 Task postcondition 已由 RWKV commit 后，再用独立小请求让 RWKV声明 Goal effect，可保留执行质量并获得局部 evidence 关系。

## 结构改动

1. 恢复初始 plan、obligation extension、failure replan 的五字段 Task batch；不允许 criterion 字段进入执行规划协议。
2. 每个成功 Task 调用一次 `task_goal_effect_binding`：输入 immutable Goal criteria、Task contract、真实 action result、确定性 checks 与 Task commit；输出恰好 `reason,advances_criteria,satisfies_criteria`。
3. Controller 只验证 criterion id 已知、数组去重以及 satisfies 是 advances 的子集；不得补 id 或改写关系。协议失败时保持空绑定并走全历史兼容 fallback，不把 Task 或 Goal 改成 pass。
4. 继续使用 Round60 的正文/metadata 分离与 Task 因果闭包即时 adjudication。

## 不作弊边界

- Goal effect 由 RWKV 在看到真实 Task observation 后声明；Controller 不按 action/path/text 推断。
- Task pass 不是 Goal pass；每个 satisfies criterion 仍必须经独立 RWKV Goal adjudication。
- 不读取 external acceptance，不更改 RWKV action、final answer 或 Goal verdict。

## 验证门槛

- 离线门槛与固定 15 题不变。
- 固定 15：B01/B02 Strict、Strict `>=6`、FN `<=1`、FP `<=7` 才运行 full90。
- full90 上传：Strict `>31`、FP `<=24`、FN `<=1`。
