# Round22 盲态生命周期与状态快照分析

## 边界

Generated after all 90 Round22 cases were frozen and before parsing Round22 results, acceptance, reference answers, standard answers, verifier-private data, or post-standard attribution. results.json is read only as raw bytes for SHA-256.

## 生命周期

- Round21→Round22 模型请求：`2636` → `1919`；任务：`795` → `724`；attempt：`766` → `535`。
- Round22 terminal status：`{"interrupted": 11, "blocked": 73, "missing": 6}`。

## Round22 snapshot 数据链

- snapshot：`117` 次 / `59` 题；省略事件：`0`。
- snapshot content/hash、artifact hash、原 action output 不变、audit 不含正文、未用隐藏答案：`117/117` / `117/117` / `117/117` / `117/117` / `117/117`。
- 有 snapshot 的模型请求：`733` 次（snapshot-request exposure `1055`）/ `58` 题。
- 同目标依赖 mutation 链：`14` 条 / `8` 题；snapshot 进入后继 action prompt：`8` 条。
- snapshot 可见后，后继产物保持相同 bytes：`8`；改写为不同 bytes：`0`。

## 盲态发现的协议副作用

- action materialization protocol failure：Round21 `8` → Round22 `37`。
- Round22 snapshot-exposed tool_action 请求为 `192`，其中失败 `29`（`15.10%`）；未暴露 snapshot 的请求 `387`，失败 `8`（`2.07%`）。
- 这是强关联而非单独的因果证明；逐请求 prompt/raw/parsed/normalized 哈希及拒绝字段见 JSON。

这只说明真实状态是否进入模型输入以及后继 RWKV 是否保留 bytes，不判断该值是否正确。每个输入、raw output、parsed payload、normalization 和 artifact 的哈希关系见配套 JSON。
