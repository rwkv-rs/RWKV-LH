# Round60 预注册协议：Task-bound evidence handoff

## 假设

Round59 的五个 FN 都发生在执行结果已经外部正确之后。根因不是缺少真实 evidence，而是 Task 与 Goal criterion 的关系没有沿执行链保存，图结束时才让 RWKV 对全历史重新检索、重新理解。让 RWKV 在规划 Task 时同时声明 criterion 关系，并在满足型 Task 完成后立即用其因果依赖闭包做 Goal adjudication，可减少证据污染与重复语义漂移。

## 唯一结构改动组

1. `MemoryEntry` 将 action 的 `observed_content` 与 `observation_metadata` 分开持久化和送模；旧 marker 只在历史 state 读取视图中透明拆分。正文、metadata 值均不得被改写。
2. Task batch 每个 Task 增加两个紧凑数组：`advances_criteria`、`satisfies_criteria`。关系由同一次 RWKV 规划输出；Controller 只校验 Task/criterion id，不生成、不补全、不排序语义关系。
3. 一个 `satisfies_criteria` Task 经 RWKV Task postcondition commit 后，立即对尚未完成的已声明 criterion 调用 RWKV Goal adjudication。输入 source catalog 只含该 Task 与其递归依赖闭包的真实 observations，而非所有历史。
4. 图关闭时的全历史 adjudication 仅作为未绑定 criterion 的兼容 fallback；Task-local adjudication 失败不改写成 pass，也不阻止后续 Task 提供新证据。

## 不作弊边界

- Controller 不根据 action 名、路径、criterion 文本或内容相关性绑定 Task 与 criterion。
- Controller 不把 Task pass 自动提升为 Goal pass；Goal supported/insufficient 仍由 RWKV 原样决定。
- Controller 不选择 actual/expected refs、不修改 reason/decision/binding，也不读取 hidden acceptance。
- 因果闭包来自 RWKV 声明的 Task graph 边，不是语义筛选；闭包中全部真实 source 均展示。

## 验证门槛

- 离线：pytest、LH-Control `30/30`、catalog `90/90`、31-file 架构验收全通过。
- 固定 15 题不变；B01、B02 均 Strict；FN `<=1`；FP `<=7`；Strict `>=6` 才运行 full90。
- full90 上传门槛不变：Strict `>31`、FP `<=24`、FN `<=1`。
