# Round30 E2E-B02 逐链路因果分析

## 结果

- External：PASS；`report.json={"project":"Orion","doubled_count":14}` 且 exact keys 通过。
- Agent：BLOCKED；Strict：FAIL；这是 1 个假阴性、0 个假阳性。
- 请求 14、Task 2、Attempt 2、replan 0；两个 Task 和两个真实 action 都完成。
- Round29 的 None dereference 未再出现，说明协议错误放大器已修复。

## 每一环节

1. Goal 解析为 GC1=读取输入、GC2=创建精确两字段 JSON、GC3=验证值。
2. RWKV 规划 `T1 read-input → T2 create-report`，因果顺序正确。
3. T1 的 `tool/read_file` 外壳透明归一化；Harness 真实读到 Orion/7；Task commit pass。
4. T1 criterion binding 错误地同时选择 GC1、GC2。随后两次 criterion commit 都给出完整
   `decision/bindings/reason`，但没有固定工具名；边界正确拒绝且 correction 正常运行，未中断 run。
5. T2 的 `tool/write_json` 外壳透明归一化；RWKV 使用 T1 observation 计算 Orion/14；Harness 写入并由确定性
   `json_field_equals` 及 RWKV Task commit 共同通过。
6. T2 criterion binding 选择 GC1/GC2/GC3。criterion commit 两次均显式调用正确函数，并给出：
   GC1→`M-T1-A1`，GC2→`M-T2-A1`，GC3→`M-T2-A1-POST-R1`，expected 均为 GOAL。
7. 三组 ref 选择与实际因果链吻合，但每组没有 `reason`。当前四字段 exact contract 在进入 ref scope 校验前整体拒绝，
   第二次重复同样结果。
8. 0 条 CriterionEvidence 导致 Goal obligation replan。第一次输出单 `task` wrapper；第二次回显 capsule；两次均非 Task
   batch，最终 fail closed 为 blocked。
9. 隔离 external verifier 在 agent 进程树关闭后读取 workspace，确认最终文件完全正确。

## 根因与放大关系

- RWKV 层错误：T1 过早把 GC2 绑定给读取 Task；两次纠正仍省略固定工具名；goal obligation correction 失败。
- 接口摩擦 1：criterion commit 没有工具选择，却要求固定 G1i 工具名；裸结构的全部语义字段已存在，仍产生额外失败面。
- 接口摩擦 2：`reason` 不参与 ref 覆盖、scope、digest、lineage 或最终重验，却是 mandatory 字段；缺少解释文本使三个明确 ref
  选择全部丢失。
- 数据结构缺口：final Task 需要引用已声明依赖 T1 的 observation 来证明 GC1，但 actual catalog 只允许当前 T2；这无法表达
  模型已经给出的完整 causal chain。
- 放大器：一个 binding 的非关键字段失败采用 proposal 级 fail closed，随后进入更困难的 goal-obligation 协议，正确产物被放大为
  Strict 假阴性。

不能采用的修复包括：自动给裸对象补固定工具名、给 binding 生成 reason、删除错误 binding 后只保留“看起来正确”的子集、依据
external PASS 反向生成证据。
