# Round56 预注册实验协议：Goal Evidence 选源与语义裁决分离

状态：在任何 Round56 代码修改和模型运行之前登记。

## 冻结基线

- 已上传最佳代码：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`。
- Round46 全量：Strict `31/90`、External `32/90`、Agent completed `55/90`、FP/FN `24/1`。
- Round55 固定 canary 相对 Round46 同 15 题：Strict `6 -> 3`、External `7 -> 4`、FP `7 -> 9`；源码已回退。
- 直接证据：Round55 LH02 只产生 `M-T1-A1`（read requirements），但 17 次 `goal_criterion_evidence_commit` 都输出无 reason 的 `pass`，并选择同一 `actual_ref=M-T1-A1` 与 `expected_ref=GOAL`。

## 唯一架构变量

将现有单次 Goal criterion `decision + source binding` 拆成两个职责单一的 RWKV请求：

1. **Source selection**：RWKV 只从真实 catalog 选择 `actual_ref` 与独立 `expected_ref`，或输出 `replan`。这一步不代表 criterion 已满足。
2. **Semantic adjudication**：仅在选源有效后，RWKV收到一个 fixed criterion、所选 source 的真实内容/metadata、Goal 原文和紧凑 frontier；先写非空 evidence reason，再提交 `supported|insufficient`。
3. `supported` 才允许 Controller 将已验证 provenance 与 raw RWKV semantic reason 一起固化为 CriterionClaim/Evidence；`insufficient` 不生成 claim，原 criterion进入已有 Goal obligation planning。
4. Controller 只检查 schema、枚举、ref 存在、owner/attempt 状态、digest、scope、实际/期望 lineage 独立；不读取 reason 来决定、不根据 path/criterion/action 内容替 RWKV选择或修改 verdict。
5. Goal validation capsule真实装入 selected memory observations；不得只登记 selected IDs 却省略 evidence 内容。
6. 不改 Goal、Task planning、action、Task postcondition、Goal obligation task proposal、final answer、Harness 或 external verifier。

## 为什么不是作弊

- 两次语义选择都来自同一个 RWKV；Controller不投票、不排名、不覆盖 verdict。
- 没有 hidden acceptance、标准答案、case/path 特判或内容规则。
- Source selection 与 semantic adjudication 的拆分只消除一个响应同时承担两种职责造成的模板化偏差；proof仍只做结构与 provenance 验证。
- `insufficient` 不自动生成任务内容，只把控制权交回既有 RWKV Goal obligation planner。

## 固定 Canary（代码前冻结）

| Case | 作用 |
| --- | --- |
| LH02 | 单次 requirements observation 不应支持 15 checkpoints/final config。 |
| H13 | 只读前 4/24 documents 不应支持六阶段 checkpoints/summary。 |
| M16 | 只读 01–03 的部分来源不应支持完整 recovered.json。 |
| M18 | 只读 a.txt 不应支持全递归 digest map。 |
| M01 | 写后同源 snapshot 不应掩盖未保留字段。 |
| M06 | manifest observation 不应证明 files copied。 |
| H12 | 部分 shard observations 不应证明完整 aggregate。 |
| LH11 | directory listings 不应证明 phase checkpoints/summary。 |
| B24 | 修改后的 source snapshot 不应证明 preserve input。 |
| B01 | 正确简单写入控制。 |
| B02 | 正确 read/derive/write 控制。 |
| B10 | coding + test 控制。 |
| M03 | 正确结构迁移控制。 |
| M12 | coding 恢复/FN 控制。 |
| LH05 | 长链正确性控制。 |

## 固定验证与门槛

1. 单元测试覆盖：selection 不等于 supported；insufficient 无 evidence；supported 保留 raw reason；selected observation 内容进入 semantic capsule；provenance变化后失效；Controller不能改 verdict。
2. 完整 offline、LH-Control `30/30`、catalog `90/90`、31 文件架构验收。
3. 固定 15-case canary 后人工逐题检查所有 source selection、semantic adjudication、Goal obligation 与最终外部结果。
4. canary 必须相对 Round46 同组 Strict 不下降，并且 LH02/H13/M16/M18 至少有一项从 FP 转为诚实未完成或真正完成，正确控制不发生系统退化，才运行完整 E2E-90。
5. 上传门槛仍为全量 Strict `>31/90`、FP `<=24`、FN `<=1`，且 raw/delivered final output 字节一致。

