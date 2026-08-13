# Round21 预注册协议：传递性模型写入快照来源

预注册日期：2026-08-13。本文档在任何 Round21 RWKV 请求和实现修改之前冻结。

## Round20 基线与已证实根因

- Strict E2E：`0/90`；External：`17/90`；Completed：`1/90`；FP：`1`；FN：`17`。
- 唯一完成题 `E2E-B02` 是假阳性。RWKV 的 `T2` 先向 `report.json` 写入正确值
  `{"project":"Orion","doubled_count":14}`，`T3` 随后由 RWKV 覆盖为
  `{"project":"project","doubled_count":4}`。
- 四条最终持久化证明把当前 `report.json` 的 action output 与 `T4` 对同一
  `report.json` 的 dependency memory/artifact 只读快照比较。两边精确相等只证明同一错误快照
  自洽，不蕴含 GC1–GC4。
- Round19 的直接模型写入来源规则只检查 expected 的直接 owner 是否为 write；它没有继续追踪
  `model write -> read snapshot -> expected`，因此错误地将其分类为
  `read_only_same_workspace_target_snapshot`。
- Round20 后验全量分析还识别出 23 题具有可直接匹配到外部失败目标的 RWKV 错误 mutation，
  5 题出现正确目标被后续 RWKV 写入覆盖。来源修复不修改这些产物，只阻止循环证据把错误产物宣告完成。

## 唯一结构变量

名称：`transitive_model_written_snapshot_lineage.v1`。

扩展现有 proof provenance 判定，但保留相同失败类别和失败消息：

1. actual 仍由 RWKV 选择，expected 仍由 RWKV 选择；proof engine 不生成 assertion、source、
   selector、transform、criterion 或值。
2. 若 expected 是 dependency memory/artifact 的只读 workspace 快照，proof engine 解析其 owner
   task、对应 attempt 与规范化 workspace path。
3. 若存在较早完成的模型选择 mutation（`write_file`、`write_json`、`append_file`、`copy_file`）
   写向同一规范化 path，且该 mutation 在 expected 快照 attempt 开始前完成，则 expected 具有
   传递性 model-written lineage。
4. 当 actual 也观察同一 workspace target 时，继续使用既有
   `actual and expected share model-written workspace target lineage` 失败类别拒绝证明。
5. 下列情况不得由此规则拒绝：
   - 没有较早模型 mutation 的初始只读 workspace 输入；
   - snapshot 先发生、mutation 后发生的历史基线；
   - actual 与 expected 位于不同规范化 target；
   - 非 workspace 来源、Goal literal、外部独立来源；
   - 无法由现有审计状态证明先后关系的来源。
6. Round20 的 unchanged deterministic recovery 继续只处理相同失败类别、相同 workspace digest、
   相同 verifier task 语义；整份 RWKV proposal 拒绝，不做部分任务选择。

除以上来源图闭包外，不修改 prompt、工具目录、采样参数、预算、任务图、动作执行、最终输出或评分。

## 不作弊边界

- 不读取 hidden acceptance、标准答案或外部 verifier 来影响生成、证明或完成。
- 不按照候选值正确与否筛选 proof；相同来源无论值是否碰巧正确都采用同一规则。
- 不补任务、criterion、selector、transform、参数、答案或最终输出。
- 不改写、排序、替换 RWKV 的 action、witness 决定或 final answer。
- 该规则只验证“expected 是否独立于 RWKV 自己写入的 actual target”这一完成证据不变量。

## 预注册离线重放

对冻结 Round20 的所有 proof-pass assertion 做 score-independent replay：

- 输入只允许 `audit.json`、`event_log.json` 与冻结 RunState；不读 external_passed、reference 或
  standard answer。
- 必须报告总 assertion、原规则通过数、新增传递拒绝数、直接模型写入拒绝数、hash 变化拒绝数、
  每题/每 criterion 结果。
- `E2E-B02` 的四条只读同目标证明必须全部由传递来源规则拒绝。
- 任何没有早期同目标 mutation 的初始只读来源必须保持通过。

## 测试要求

- 单元测试至少覆盖：直接模型写入、模型写入后 read artifact、模型写入后 read memory、
  read snapshot 后才写、不同 target、无可靠时序、symlink/越界归一化失败。
- 完整 `pytest`、LH-Control `30/30`、RWKV-E2E-90 validate-only、Round18 proof replay、
  Round19 obligation replay、Round20 proof-pass replay全部通过并记录摘要与 SHA-256。
- 正式运行固定 endpoint `127.0.0.1:29610/v1`、模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`、E2E-90、30/30/30 分组、既有采样参数和并发参数。
- 运行期继续完整保存 raw/normalized payload、request、event、state、artifact hash 与审计链。

## 晋级门禁

恢复 Round2 后的完整要求，全部满足才允许上传：

- FP=`0`；
- Strict `>7/90`；
- Completed `>7/90`；
- External `>=24/90`；
- 产品测试、LH-Control、E2E-90、边界/异常/历史 proof replay 全部通过；
- output non-intervention 精确成立；
- Round21 运行后不得修改评分口径或阈值。

任一失败则记录 `do_not_upload`，继续下一轮根因整改，不向 GitHub 推送 Round21。
