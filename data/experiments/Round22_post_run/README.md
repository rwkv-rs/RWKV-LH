# Round22 post-run 验证记录

## 来源、版本与用途

- 数据集：`RWKV-E2E-90` v1，Basic / Medium / Hard 各 30 题；资源路径与摘要冻结在 `../Round22/RUN_PROTOCOL.json`。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`，本地 OpenAI-compatible endpoint；采样、并发和上下文参数见同一协议。
- 唯一结构变量：`post_action_workspace_snapshot_memory.v1`。成功写入后从真实 workspace 回读，保留原 action output，并只向直接依赖任务投影可审计 snapshot。
- 用途：检验真实 workspace 状态传递是否改善长链任务；标准答案、hidden acceptance 和 Codex reference 只在 90 题全部冻结后用于评分和后验归因。

## 生成与验证

1. 运行前：全量 pytest、LH-Control-30、E2E90 catalog validation、Round18/19/20 历史 replay，以及冻结的 Round21 26 条状态链 replay。
2. 正式运行：90 题、并发 8、每题最多 200 transitions；运行期间没有改代码、改参数、重启、补跑或修改 RWKV 输出。
3. 评分前：冻结 `BLIND_ANALYSIS_BOUNDARY.md`，仅从事件/请求/快照链生成盲态生命周期分析和预标准答案因果综合。
4. 评分后：固定 scorer 比较 External/Strict，并将 hidden acceptance 只作用于冻结产物和冻结 snapshot 的临时副本；结果没有回流模型、controller 或 final output。
5. 运行后：pytest `252/252`，LH-Control `30/30`，历史 replay 全部通过；`gates.json` 判定 `do_not_upload`。

## 结果

| 指标 | Round21 | Round22 | 变化 |
| --- | ---: | ---: | ---: |
| External | 20/90 | 19/90 | -1 |
| Strict | 0/90 | 0/90 | 0 |
| Completed | 0/90 | 0/90 | 0 |
| FP | 0 | 0 | 0 |
| FN | 20 | 19 | -1 |
| 模型请求 | 2636 | 1919 | -717 |
| prompt tokens | 6,461,359 | 4,490,644 | -1,970,715 |

难度分组为 Basic `17/30`、Medium `1/30`、Hard `1/30`。历史最佳 External 仍为 Round16 的 `24/90`。

## 结构作用与缺陷

- 117 个 snapshot 覆盖 59 题；content hash、artifact hash、原 action output 不变、审计事件不含正文和未使用 hidden answer均为 `117/117`。
- 8 条 snapshot 真正进入后继同目标 action prompt 的链全部保持原字节，证明真实状态传递成立；但这 8 条最终 External 为 4 对 4，snapshot 只保留模型状态，不会替模型纠错。
- 65 个可用直接 path acceptance 复核的 case/path stream 中，首个 snapshot 已写对 `32/65`；其中 1 个后来被不同错误值覆盖，4 个被相同正确字节重写。
- 模型可见 snapshot 使用了与 G1i action schema 相邻的 JSON 字段。snapshot-exposed tool_action 失败 `29/192`（15.10%），未暴露时为 `8/387`（2.07%）；action materialization failure 从 Round21 的 8 增至 37。29 个暴露后失败中，4 题外部产物已正确但无法完成，25 题仍错且后续生产/恢复被截断。
- 全轮只有 33 题进入 witness selection、17 题完成 binding、0 proof pass、0 CriterionEvidence、0 completed；19 个 External 正确题全部是假阴性。

因此，本轮验证了“真实状态快照”这一内部机制，但否定了当前模型可见 JSON 表示。它没有达到上传门槛，不能作为更优版本推送 GitHub。

## 完整性摘要

- 原始 `results.json`：`5dab26b4663ec340b29f3fadba8bd641c85b59ebd861c61e581e615ede981288`
- 标准答案前因果综合：`061cba5c26c4286b14982926f598b4928cbe593a9d201bcf2015efc027da4acb`
- snapshot 标准答案后归因：`23ad0c9849f98161fc25a4d9129ed3518493d9cdc43c770b2ea807e4d63c5416`
- pytest JUnit：`d5cd87aa99ca936b1c17c92c66cb6be632da8c1cf0bee3d0a6d2c49ebd803d21`
- LH-Control 结果：`a5b5d84e4b29a230649d2df17fbab1c2fc513854c8c91c203c490277daf2ad34`
- 所有核心分析文件的路径、字节数与 SHA-256 统一登记在 `../Round22/analysis_integrity_manifest.json`；该 manifest 在本文件写入后重新生成。
