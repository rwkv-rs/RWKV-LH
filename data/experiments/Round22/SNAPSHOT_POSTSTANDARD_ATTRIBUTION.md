# Round22 snapshot 标准答案后归因

## 边界

Post-run only. Hidden acceptance is applied to frozen snapshot bytes in temporary workspace copies after the prestandard synthesis was hashed. No result is fed back into RWKV, controller state, actions, completion, or final output.

## 首次目标写入

- 有直接 path acceptance 的 case/path stream：`65`。
- 第一个 snapshot 已通过全部直接 path checks：`32/65` （`49.23%`）；任一 snapshot 通过：`32/65`。
- 先通过、后被不同错误值覆盖：`1`；后续重写但保持相同正确 bytes：`4`。

该指标只覆盖直接命名目标文件的 file/json/files_equal check，不替代完整 External。

## snapshot 可见链与最终答案

- 当前同目标链 `14`，其中 exact snapshot 进入后继 action prompt `8`。
- 这 `8` 条都保持相同 bytes；最终 External 正确 `4`，错误 `4`。
- 可见链中 prior snapshot 本身通过全部直接 path checks：`0`。

因此 snapshot 能保存 RWKV 已有状态，但不会把错误状态改成正确状态。

## Round21→Round22

- 新增 External：E2E-B02, E2E-B06, E2E-B10, E2E-B18, E2E-B29, E2E-M21。
- 丢失 External：E2E-B04, E2E-B16, E2E-B22, E2E-B26, E2E-LH02, E2E-M11, E2E-M12。
- 新增中有 snapshot prompt：E2E-B02, E2E-B06, E2E-B10, E2E-B18, E2E-B29, E2E-M21。
- 丢失中有 snapshot prompt：E2E-B04, E2E-B16, E2E-B26, E2E-LH02, E2E-M11, E2E-M12。

## 协议碰撞的标准答案后影响

- snapshot 暴露后的 action materialization failure：`29` 题；终止时已有正确外部产物 `4`，仍错误 `25`。
- 已正确的 4 题被阻断完成；仍错误的 25 题被提前截断后续生产/恢复。不能假设它们若继续一定会做对，但该协议终止明确减少了 RWKV 继续尝试的机会。

完整 snapshot、26 条历史链、当前链和逐请求协议失败见配套 JSON。
