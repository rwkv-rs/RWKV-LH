# SEL-2P9-S51 natural Harness route remediation preregistration

登记时间：2026-08-29（Asia/Shanghai），在 S39 + EXE-Z0/G2 当前架构矩阵完成、任何 S51
数据生成、特征提取、Head 训练或指标产生之前。

## 已观察到的根因

- S39 的 source-heldout locked test 为 `842/857 = 98.250%`，但它监督的是显式合成的
  操作序列。
- 固定当前架构矩阵中，RL00/RL01 canary6 都仅 `1/6`，真实联网都为 `0/2`；Executor
  state 并未改变 Selector 的失败集合。
- Full90 的 89 个可运行 case 都留下了 audit；与 R132 旧 13.3B direct route 的首个原始
  function 比较，仅 `7/89` 一致。R132 90 个首动作中 `list_directory=77`，说明真实 Harness
  的成功路径以“发现 -> 读取 -> 写入/验证”为主，而 S39 训练分布偏向直接选择请求中的后续
  修改工具。
- 两条联网 case 均正确完成第一步检索，但 Selector 随后选择 `final_answer`，遗漏仍未完成的
  `write_file` / `write_json`。原始 logits、Executor 输出和完整日志均保留；禁止通过规则改写
  argmax 或修补 RWKV 输出。

## 冻结职责与输入

- 架构保持不变：2.9B Selector 只接收固定 25 个 name/description、不可变请求、边界化进度；
  只输出 Hidden(mean+last concat) + MLP 的一个原始 argmax。
- 13.3B Executor 只在选择完成后接收该工具的完整 schema，并生成参数或最终文本。
- 保持 compact V3 字节协议。菜单在前；不可变 task 是 bootstrap 的最后字段；每步的
  `stage_objective` 位于续写尾部、只由极短 `stage_role` 跟随。不得在 S51 期间更改提示几何、
  类别顺序、工具描述、阈值、温度或 state profile。
- Selector 与 Executor state 独立；S51 首先只测试新的 h64/h128 Head，Selector 使用原生零
  state。只有 Head 无法通过固定门槛，才允许另立协议测试新的 Selector state。

## 固定数据

保留源：

- S28 dataset `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`；
  features `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`。
- S39 dataset `b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab`；
  features `b56e5cefab701128f7217bdecb00f2c1bd64b9505b8be61d9e55a1fc78c13481`。

新增 S51 数据由以下两个互不替代的来源组成：

1. `R132-success`：只读取 R132 `external_passed=true` 的 34 条 case 的 visible request 与
   原始、已执行 action sequence；`results.json` SHA-256 为
   `4ce04752b1969549dd9332a9701fcadb0afd0ad2b9aa43083d7735bf8d3ece3c`。不得读取 hidden
   acceptance 生成标签。固定 canary6：`B01,B02,B10,M03,H10,M12` 全部只进 test；其余
   case 按 `sha256("S51-DEV|" + task_id)` 升序取前 5 个进 dev，其余进 train。
2. `synthetic-natural`：20 个固定通用操作链，每个 split 使用独立实体和独立中英文 frame；
   每个链 train/dev/test 分别生成 20/5/5 条，共 600 trajectories。网络链不得使用 frozen
   live2 的 URL、仓库、文件名或逐字请求。

所有 trajectory 必须 prefix-close：每个真实下一工具和最后的 `final_answer` 都成为一条独立
监督；完整 rendered input 必须与生产 `build_network_selector_input` + compact V3 renderer
逐字节一致。数据集记录 source/version/use/hash/generator，并验证 task-level split 隔离、实体
隔离、零 hidden acceptance、零 Executor text、零 tool results、零参数 schema。

## 特征、训练和选择

- 物理 GPU0；2.9B 原生零 state；每个真实 prefix 一次 forward，同时保存 mean/last；不生成
  文本、不采样，feature shard 不含 label。
- 训练源为 S28 train + S39 train + S51 train；dev selection 同时看三个 dev。训练 loss 对
  每个 `(source,class)` 等总质量；特征归一化只使用 train；seed `1051`。
- 固定容量顺序：`concat-h64`，仅其未通过全部 dev 门时训练 `concat-h128`。其他结构、规则或
  fallback 不允许。
- S28 dev accuracy/macro-F1 `>=99%`；S39 dev accuracy/macro-F1、history/current `>=96%`；
  S51 dev accuracy/macro-F1 `>=96%`，history/current 各 `>=95%`，每个有支持类别 recall
  `>=90%`。portable replay argmax 必须相等且最大 logit 差 `<=0.005`。

## 锁后测试与产品门

Head 在 train/dev 锁定后才读取 S39 test 与 S51 test labels：

- S39 locked regression accuracy/macro-F1 `>=96%`，S28 test retention `>=99%`；
- S51 test accuracy/macro-F1 `>=96%`，history/current `>=95%`；
- 固定 canary6 的完整 route prefix accuracy `>=96%`，且当前 Harness 外部 strict `6/6`；
- frozen live2 route 的四个关键选择必须依次为
  `web_search -> write_file`、`connector_lookup -> write_json`，完整联网 E2E `2/2`；
- 所有选择保留 25 个 raw logits，所有 Executor generations 保留原始 envelope；无后处理、
  隐藏重试、规则替换或修改/删除原始 RWKV 输出。

Full90 的 `mock_api` 是官方 23-operation 产品菜单之外的 benchmark-only operation：必须作为
结构不兼容失败保留，不能把它加入产品菜单。runner 应按通用 per-case exception containment
记录该失败并继续其余 89 条；Full90 只能作为 90 条完整回归报告，不能因结构错误提前中断。

