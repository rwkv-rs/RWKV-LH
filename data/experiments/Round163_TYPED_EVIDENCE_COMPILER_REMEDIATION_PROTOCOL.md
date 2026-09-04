# Round163：Typed Evidence Compiler 系统性整改与离线重放协议

日期：2026-08-24

## 目的与边界

Round162 Full90 暴露的共同根因不是某个 task 的工具参数，而是强 Planner 生成的
typed contract、RWKV public result、latest evidence 投影和机械 checker 之间语义不闭合。
本轮只修复这些通用数据结构和执行语义，不添加 task_id、suite 分层或固定路径特判。

本轮首先使用 Round162 已落盘的 90 例完整审计做离线重放，不重新调用强模型或 RWKV；
只有离线门槛和完整测试通过后，才允许另行预注册在线 canary/Full90。Round162 的既有
external checker、TP/FP/FN/OTHER 口径与历史结果不得修改。

## 固定数据、来源与摘要

- 来源：`data/experiments/Round162_typed_contract_full90_20260823/`。
- 版本：Round162 typed-contract Full90，90/90 case audit。
- 用途：重放 typed assertion、result capsule、latest evidence、correction signature、resume
  和 terminal invariant；不是新训练数据，也不参与模型微调。
- `results.json` SHA256：
  `883aec29cc7c60e8a1a22aa456a9dd1d2461334addaab75f573256d29bfe8f4c`。
- `Round162_TYPED_CONTRACT_FULL90_GLOBAL_SUMMARY.json` SHA256：
  `a1125a648d681cda8928ea4cc8a751a25a71f038514ae4150bd5f5d0e52f13ac`。
- 90 个 `cases/*/audit.json` 逐文件 SHA256 排序后再次 SHA256：
  `b185b060becded02fde7875e3cb1e887b7f64f056ef2a408bfbe2ed9f7ad512b`。
- 生成方式：Round162 用户明确要求的 frozen Full90；本轮只读，不覆盖原结果。

## 系统性修改范围

1. typed assertion 在进入 frozen contract 前执行 kind-specific 语义校验；本地 DSL 无法
   完整表达的关系标记为 exception-review-only，机械 checker 返回 unresolved，不返回 false。
2. result capsule 必须严格按 action_id 绑定 artifact；无 artifact 的 action 不得继承 atom
   其他 action 的 artifact。
3. latest evidence 以 `(subject, view_kind)` 保存 content、identity/digest、mutation receipt、
   command result 和 graph fact，不能再用单一 path 覆盖不同观察类型。
4. content checker 只能消费 read/mock/bind 等内容观察；write/check/digest 的 stdout 不得伪装
   成目标文件内容。
5. correction signature 使用稳定、typed 的状态投影，并区分缺证据、执行失败、契约矛盾；
   新 correction node id 不得制造“新状态”。
6. resume 只恢复未完成事务；每个 case 必须有且仅有一个权威 terminal state。
7. 强 Planner 默认生成 2–4 个同一因果事务内的 RWKV 操作；执行器仍逐 action 公开结果，
   依赖关系和写后读/检查不可被并行化破坏。

## 预注册离线门槛

以下门槛在运行离线重放前固定，运行后不改评价算法：

1. 完整测试集通过；新增测试必须覆盖 multi-action artifact 绑定、同一路径多视图、非 JSON
   pointer、multi-source transformation、unsupported aggregate、稳定纠错签名和 resume terminal。
2. 对 Round162 全部 90 个 audit 扫描，artifact-less action 继承其他 action artifact 的数量为 0。
3. content observation 不被 write/check/digest receipt 覆盖；Round162 已知 9 个 shadow 场景全部
   由通用 view_kind 规则消除。
4. Round162 已知 42 个不可由现有 DSL 正确表达的 assertion pattern 不再产生 deterministic
   contradiction；必须是结构化 semantic exception/unresolved。
5. 支持的 typed assertion 对同一 capsules 重放两次结果完全一致；不支持的 assertion 不进入
   local-only acceptance 或 local-only rejection。
6. 对证据未变化而 correction node id 变化的序列，第二次签名必须相同并触发 bounded stop；
   不允许用重复强模型调用掩盖 evidence stagnation。
7. terminal/recovery 离线审计必须明确列出 90 例的唯一权威终态；历史追加事件可以保留，
   但恢复后的旧 terminal 不得继续作为当前终态。

## 固定指标与输出

- 继续使用 Round162 的 external TP/FP/FN/OTHER，只做历史结果比较，不回写分类。
- 额外报告：assertion semantic class、local/unresolved 数、content/identity/command view 数、
  inherited-artifact 数、shadow 数、correction signature collapse 数、authoritative terminal 数。
- 离线重放脚本放在项目根目录 `temp/`，以绝对路径执行。
- 结果和分析写入 `data/experiments/Round163_typed_evidence_compiler_offline/`，包含来源、版本、
  用途、摘要、命令、参数、完整指标和未通过项。

Round163 离线通过只表示控制器确定性缺陷已被清除，不等价于模型能力 Full90 提升；在线
收益必须由后续固定代码、固定配置、固定数据的独立运行验证。
