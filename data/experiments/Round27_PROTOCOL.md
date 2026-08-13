# Round27 预注册协议：单一最小 Task batch 与读取驱动扩展

> 状态：`preregistered_implementation_in_progress_not_run`。冻结时未发出任何 Round27 RWKV 请求，也未读取 Round27
> hidden acceptance。证据仅来自完成后的 Round26 全 90 题 event log。

预注册日期：2026-08-13。唯一结构变量为 `single_observation_driven_task_batch.v1`。

## 假设

Round26 的 89 个任务物化前失败来自一个过宽且重复的接口，不是 89 个独立模型能力缺陷。将 initial plan、Goal extension
和 failure replacement 统一为同一个最小 Task batch，并把真实 action observation 放回下一轮状态胶囊，应该首先恢复
`list_directory/read_file/read_json` 与后续动态扩展；Controller 不生成任务、文件摘要、动作参数、期望值或最终答案。

## 唯一在线 Task 结构

- 三种入口只接受同一个 envelope：`schema_version=long-horizon.task-batch.v1` 与 `tasks`。
- 每个 Task 恰好五个模型字段：`local_id`、`title`、`description`、`dependencies`、`postcondition`。
- required、priority、retry policy 是固定运行策略，不再要求 RWKV 重复声明；action 和 verifier 仍在 Task ready 后由 RWKV
  通过唯一 G1i action commit 决定。
- operation/subject/member/phase/effect/expected/dependency outcome 不再出现在 Task batch。实际 action、path、outcome、artifact
  revision 和 dependency output 由运行时按原始观察记录，不改写 RWKV 的语义输出。
- 初始 batch 只描述当前输入已知的下一因果前沿。依赖未知读取结果的成员任务必须等 observation 出现后再扩展。
- task_graph.tasks/nodes 仅作为预注册透明 wire wrapper；若带 edges，必须与每个 Task 的 dependencies 完全一致且无条件，
  才能无损展开。raw/normalized payload 与 digest 全部保留。
- G1i 的 `tool`/`arguments` 作为已观察到的等价 wire alias 透明归一为 `name`/`arguments`；不选择工具、不修改参数。

## 读取驱动状态

- Goal extension capsule 必须包含最近完成 Task 的真实 action type/arguments/outcome、完整可用 output、artifact refs 和截断标记；
  不再把所有 action observations 排除。
- `list_directory` 提供稳定排序、递归、截断与可继续游标；成员只来自 Harness 实际观察。
- 扩展按小批次进行，已完成历史不可修改；同一 observation 可产生多个独立 ready Task。
- Task 完成后由 RWKV 单独绑定它直接满足的 Goal criterion；空绑定是合法的读取/准备结果。Controller 只校验 ID 子集，
  不补 criterion，也不把 Task 成功当 Goal 完成。

## 最终目标结构验收

在固定大型代码项目快照上，只给自然语言目标和工作区：Agent 必须先发现源文件，再为每个文件建立独立读取/总结工作，
保存每文件 RWKV 摘要并汇总。验证文件清单覆盖率、一文件一摘要、无遗漏/重复、依赖证据可追溯、局部失败恢复、真实并行度、
聚合集合一致性；摘要文本不得由 Controller 或脚本生成或修改。

## 固定验证

- 完整 pytest、LH-Control-30、E2E-90 validate-only。
- 新增单一 Task envelope、旧 envelope 拒绝、无损 wrapper、G1i alias、action observation capsule、目录分页、动态 fan-out、
  criterion 后绑定和并行 ready frontier 回归。
- 先做固定小型读取链 canary，再运行 E2E-90；主指标仍为 Strict/External/Completed/FP/FN，另报告 Task、Attempt、read action、
  dynamic extension、parallel frontier 覆盖。FP 必须为 0；未优于既有最佳版本不得上传为更优版本。
