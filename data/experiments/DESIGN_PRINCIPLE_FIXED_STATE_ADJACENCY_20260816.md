# 固定态模型设计第一原理（项目所有者确立，2026-08-16）

**每次调用一个身份、一个决定、最少的竞争信息；最关键的 literal 内容放在离续写点
最近的地方。**

## 证据链（全部来自冻结 Full90 实验）

正面：
- Round46：phase-local 上下文（~2160 tokens/请求）= 历史最高 31/90。
- Round118 schema 反馈：精确 schema 紧贴重试点，B16/B17 从 24 次拒绝降到 2 次。
- Round119/121：观察指纹与 guard 都是"一个事实一个身份"的机械化。

反面：
- Round50 两阶段调用（身份被拆成两次决定）：31→6。
- Round116 泛化 wrapper（决定前先做元选择）：8/30。
- Round120 step 回显（模型自产内容紧贴续写点）：同一 step 循环 199 次；
  全量投影（竞争信息挤占 literal 请求）：write-first 退化、22/90。
- 分数与每请求 token 数严格反相关（2160→31，6013→12，9047→30，9410→22）。

## 当前实现的已知违背（后续轮次的变量来源）

1. `LongHorizonModel._assignment` 使用 `sort_keys=True`：字段按字母序，
   `immutable_request` 居中、`workspace_manifest` 离续写点最近；instruction 淹没在
   中部。
2. bootstrap 之后，逐字用户请求不再出现；transcript 每长一个事件，它对下一决定的
   影响衰减一分——义务丢失（M06/H18）与提前 Final 的候选机理。rollover 重注
   bootstrap 后行为短暂恢复，是同一机理的旁证。

## Round124 候选：Literal Request Adjacency（草案要点）

- 每次生成的渲染 = 全部事件 + **固定尾块**（逐字 immutable request + 单行调用指令）
  + "Assistant:"。尾块内容全程恒定、确定性渲染、digest 可审计；checkpoint 仍只存
  事件（append-only 权威不变），transcript 是其确定性投影。
- 不新增模型输出负担、不新增字段、不做投影/意图/评审——只改变 literal 内容与
  续写点的距离。
- KEEP 门槛沿用因果归因 + 噪声感知模式；预期直接受益：义务丢失型 FP
  （M06/H18/M23）、提前 Final、rollover 后的漂移。
- 于 Round123 落地后正式预注册并冻结细节。

## 约束不变

Controller 不生成业务内容；literal 尾块只含用户请求原文与恒定指令句；不读隐藏
验收；append-only causal 权威与既有审计不变。
