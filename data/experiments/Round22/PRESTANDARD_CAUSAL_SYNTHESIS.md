# Round22 标准答案前因果综合

## 边界

Frozen after all 90 Round22 cases terminated and before parsing Round22 results, acceptance, verifier-private data, Codex reference answers, standard answers, scorer output, or post-standard attribution. results.json contributes raw-byte SHA-256 only.

## 正向作用：真实状态传到了 RWKV

- 117/117 snapshot 的 content/hash 与 artifact hash 一致，原 action output 117/117 保持不变，且 117/117 未使用 hidden answer。
- 当前同目标 mutation 链 `14` 条；exact snapshot 进入后继 action prompt `8` 条。
- 可见 snapshot 后，后继产物保持相同 bytes `8` 条，改为不同 bytes `0` 条。

## 负向作用：状态格式污染 G1i 输出协议

- action materialization failure：Round21 `8` → Round22 `37`。
- snapshot-exposed tool_action 为 `192` 次，失败 `29`（`15.10%`）；非 snapshot 为 `387` 次，失败 `8`（`2.07%`）。
- 29 个 snapshot 暴露失败全部解析成顶层 `action` 或 `action_type` 外壳，且 29/29 没有进入透明 normalization。模型面对带 `action_type/content/path` 的 snapshot JSON 后，输出模式与唯一 G1i call contract 发生碰撞。

## 放大链

Round21→Round22：model requests `-717`、tasks `-71`、attempts `-231`。Round22 只有 33 题到 witness selection、21 题提交 mode、17 题完成 binding，0 proof pass、0 evidence。协议碰撞发生在后继 action 执行之前，直接截断producer/recovery 链；因此快照既改善局部状态保持，又通过表示格式制造更早的协议终止。

## 解封标准答案前仍未知

- 被保持的 bytes 是否正确；External/Strict/Completed/FP/FN 是否改善。
- 15.10% 与 2.07% 是强关联，不是随机配对实验的独立效应量；任务难度和 prompt 位置仍可能混杂。

## 若门禁失败的下一结构假设

保留内部 snapshot 与审计不变，只把模型可见形式改成与 action schema 不相交的定界观察头 + byte-exact UTF-8 正文；外围元数据不再使用 `action_type/content/path` JSON schema。该改变不改文件值、不替 RWKV 选 action、不修改最终输出，并对所有 snapshot 一致应用。
