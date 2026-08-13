# Round22 预注册协议：post-action workspace snapshot 跨任务状态传递

预注册日期：2026-08-13。本文档在任何 Round22 实现修改和 RWKV 请求之前冻结。

## Round21 基线

- Strict `0/90`；External `20/90`；Completed `0/90`；FP `0`；FN `20`。
- 分组 External：Basic `16/30`、Medium `2/30`、Hard `2/30`。
- 历史最好 External 仍为 Round16 `24/90`；Round21 不上传。
- 传递性来源规则拒绝 33 次 `model write -> read snapshot -> expected` 循环证明，同时保留 2 条
  没有较早同目标 mutation 的只读 snapshot；它修复完成可信度，不直接提升 producer 能力。
- 盲态全量分析发现 14 题存在 26 条“依赖任务再次写入同一目标”的链；前一写入在
  dependency memory 中全部只剩 `JSON written` 或 `file written`。
- 解封标准答案后，14 题中 13 题最终 External 错误。B02、B18、M28 可直接确认：RWKV 先写出
  外部目标的精确值；架构只传递成功回执；后继 RWKV 任务再次写同一目标并覆盖为错误值。

## 唯一结构变量

名称：`post_action_workspace_snapshot_memory.v1`。

在现有 `_record_artifacts_and_memory` 边界增加独立、append-only 的 observation memory：

1. 仅对 Harness 已执行成功且产生 workspace artifact 的 mutation action 生效：`write_file`、
   `write_json`、`append_file`、`copy_file`。
2. 保留原 `action_result` memory 及原始输出不变；另建独立 memory，ID 由 attempt ID 确定性派生。
3. snapshot 必须从 action 完成后的真实 workspace path 重新读取，不从 RWKV 请求参数复制；path
   必须经 Harness scope resolution，symlink/越界失败关闭。
4. snapshot 固定包含 schema version、action type、workspace-relative path、observed artifact hash、
   media type、size 与 UTF-8 content。内容上限 20,000 bytes；超过上限或非 UTF-8 时只保留
   元数据，不生成或猜测内容。
5. 重新读取的 bytes SHA-256 必须等于 Harness observed artifact SHA-256；不一致则不创建 snapshot。
6. snapshot memory 归属于实际 producer task，并加入该 task 的 output refs。因此只有任务图中
   已声明依赖该 producer 的后续 RWKV task 才会通过现有 WorkingMemoryBuilder 看到它。
7. 新增审计事件，记录 task、attempt、snapshot memory ID、artifact ID、path、hash、size、
   content 是否包含及省略原因；不得记录标准答案字段。
8. 后继 action type、path、参数和值仍完全由 RWKV 选择。控制器不阻止覆盖，不合并 JSON，不选择
   “较正确”版本，不回滚 RWKV 的写入，不修改 final answer。

除该 observation memory/event 外，不修改 Goal、plan、工具目录、采样参数、proof 规则、恢复预算、
任务排序、动作执行、完成判定或评分。

## 不作弊边界

- snapshot 是已执行 RWKV action 的真实 post-action observation，不是由规则推导的答案。
- 不读取 hidden acceptance、standard answer 或外部 verifier 来决定是否创建、保留或展示 snapshot。
- 每次成功 mutation 使用同一规则，无论写入值后来是否被判正确。
- 不把 snapshot 自动绑定为 expected，不为 RWKV 生成 assertion、criterion、task、action 或值。
- 不修改 RWKV 的最终输出，也不保护某个内容免受后续 RWKV 覆盖。

## 预注册验证

### 单元与边界

- write_json/write_file/append_file/copy_file 成功后创建精确 snapshot；原 action_result 不变。
- snapshot bytes/hash 与 workspace artifact 完全一致；dependency context 同时包含原回执和 snapshot。
- failed action、read-only action、hash mismatch、超过 20,000 bytes、非 UTF-8、symlink 和越界路径
  分别验证；不得崩溃或产生伪内容。
- state save/load、checkpoint restore、并发 run、token projection 与现有 proof/recovery 回归通过。

### 冻结 Round21 回放

- 对 26 条已登记的同目标依赖 mutation 链做 score-independent context replay。
- 报告每条链在新机制下是否能向后继任务提供 exact post-action snapshot；不读取 External/reference。
- B02、B18、M28 只在 post-run 归因中作为已知问题入口，不能写特判。

### 全量回归

- `pytest`、LH-Control `30/30`、RWKV-E2E-90 validate-only；
- Round18 proof replay、Round19 obligation replay、Round20 proof-pass replay；
- 运行期完整保存 raw/normalized payload、event、state timeline、artifact hash 与 snapshot audit。

## 正式实验与评价

- endpoint：`http://127.0.0.1:29610/v1`；模型：
  `rwkv7-g1i-13.3b-20260805-ctx16384`；context 16384。
- 固定 E2E-90，Basic/Medium/Hard 各 30；并发 8；最大 transitions 200；采样参数不变。
- 90 题全部终止前不加载 hidden acceptance/reference。
- 首要能力指标：External 总数与分组、首个正确 target 写入率、正确 target 后续覆盖率、26 条状态链的
  最终结果；同时报告 Strict、Completed、FP/FN，但不要求起步阶段全部做对。

## GitHub 晋级

为了避免把随机回升当架构改进，仍使用现有完整门禁：FP=0、Strict>7、Completed>7、External>=24，
全部回归通过且 output non-intervention 成立。正式运行后不得改门禁。

若 External 或正确状态保留有明确改善但完整门禁未过，则完整记录实验、判定 `do_not_upload`，下一轮继续；
不得仅因局部指标好看上传。
