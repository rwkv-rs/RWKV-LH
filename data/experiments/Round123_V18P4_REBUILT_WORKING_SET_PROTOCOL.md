# Round123 v18-P4 Rebuilt Working Set 预注册协议（已冻结，2026-08-16）

基线补记：Round122 判 REVERT（GATE5 token 门槛），guard **不在**本轮基础内；
本轮基础 = Round119（Strict 30/36FP/0FN，18.64M tokens）。KEEP 门槛中
"Round122 Strict"以 Round119 的 30 计：Strict >= 28。恒定指令新增两句通用事实
（终局语义：final_answer 文本是完整交付、其后不存在"下文"；多条目工作应边做边写
中间结果文件）——分别针对 UI 实测的聊天尾部吸引子与 RWKV 作者的多级总结建议。

日期：2026-08-16（实现前预注册；运行后不得修改口径、门槛或变量定义）

## 授权与定位

项目所有者于 2026-08-16 确立 RWKV 真实需要的架构循环：**状态压缩 → 删除竞争信息 →
重申当前身份/目标 → 将当前义务搬到末端 → 单步决策 → 执行 → 再压缩**。长期状态外置，
模型输入是不断重构的短工作集，而不是不断 append 的完整历史。

范围边界：本轮只在 prompt-replay 层实现该循环；native RWKV state 与推理引擎深度接入
是项目所有者后续的独立工作。设计必须保证：每次"再压缩"点即未来的 state checkpoint
边界，工作集渲染即未来的 state-prime 输入——传输层可替换，架构循环不变。

## 决策来源

- 分数与每请求 token 严格反相关（R46 约 2160→31/90；append+rollover 线 9000+→≤30）。
- R120 反证：在 append 之上叠加投影（信息更多）→ 22/90；本轮相反：**用重构替代
  append（信息更少）**。
- 义务丢失（M06/H18）与聊天尾部吸引子（UI 实测 "The corrected implementation is
  below"）的共同机理：literal 目标离续写点越来越远。固定尾块使其恒为最近。
- 邻近性第一原理（`DESIGN_PRINCIPLE_FIXED_STATE_ADJACENCY_20260816.md`）。

## 假设

1. 每请求 token 回落至 R46 区间（约 2-3k），全程无 rollover；
2. 逐字请求+约束恒在续写点最近处 → 义务丢失型 FP（M06/H18/M23 型）减少、
   提前 Final 减少；
3. 最近 4 条精确结果足以维持步间连续性（R46 的 task-local 等价物）。

## 精确变更（全局机制，无单题特判）

### C1 每请求重构工作集（rwkv_lh/model.py、model_io.py）

1. 取消增长式 transcript 与 rollover：每次 `next_command`/`terminal_answer` 都从
   `_assignment` 重新 bootstrap 一个 checkpoint（ModelSession 机制不变，逐请求
   transcript/digest 照常审计，明确标注 prompt_replay）。
2. 工作集渲染顺序（固定，从远到近）：
   a. System: 工具 catalog（恒定）；
   b. 压缩世界状态：workspace manifest（现有 256 项/1800 token 上限）；
   c. 工作记忆：最近 4 条完整 exact ActionResult（现有 6000 字符截断规则）；
   d. 若上一事件为协议拒绝/guard 拒绝：其完整事实（含已选 operation 精确 schema）；
   e. **末端 literal 块（离续写点最近）**：逐字 immutable request、constraints、
      恒定单行指令（选择一个操作或 final_answer；final_answer 的 text 是终局输出，
      其后不存在"下文"）。
3. 删除竞争信息：不含覆盖投影、不含模型自产 step、不含历史 catalog；重复计数仅在
   Observation 事实内（Round119 不变）。
4. 指令句新增一条恒定事实（针对 UI 实测的聊天尾部吸引子）：final_answer 文本是
   最终交付，不能引用"下面/如下"的未执行内容。
5. causal 权威、观察指纹、失败预算、终止事务、guard（若 R122 KEEP）全部不变。

### 明确不做

- 不加投影/意图字段/reviewer/Task；不改采样（Round124 变量）；不改工具注册表。
- 不宣称使用了 native state；transport 仍诚实标注 prompt_replay。

## KEEP 门槛（因果归因 + 噪声感知）

1. Strict >= max(28, Round122 Strict − 2)；
2. FN <= 2；90/90 终态完整；
3. 字节精确对照组 B01/B06/B13/B19/B28 至少 4/5；
4. 每请求平均 prompt tokens < 4000（结构性目标，未达即说明重构失败）；
5. 多步代码链对照组 B10/B20/B30/M02/M12/M20 至少 5/6（步间连续性探针）。
期望（非 KEEP 条件）：义务型 FP（M06/H18/M23）改善、Strict > 31（则追加
confirmatory）。

## 前置与冻结

以 Round122 的 KEEP/REVERT 结果为基线（其数字于分析完成后补记于此并冻结）。
其余与 Round118–122 一致：model `rwkv7-g1i-13.3b-20260805-ctx16384`、endpoint
`http://127.0.0.1:29610/v1`、temperature 0.05、max-transitions 200、concurrency 1、
uv 0.12.5、suite all（90）。

## 流程

1. 实现 C1；离线回归：渲染顺序与末端 literal 块、无 rollover、逐请求 digest 审计、
   拒绝事实进入下一工作集、终局路径同构；全量 pytest、catalog 90/90、compileall、
   diff check。
2. 冻结只读 source manifest → Full90 → `Round123_v18p4_full90/` 完整产出（REPORT、
   results、cases、MANUAL_CAUSAL_ANALYSIS 含 token 分布、义务型 FP 逐题核对、
   三向 flip）。
