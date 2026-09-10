# 独立 AI reviewer two：限定14来源、仅Selector复核

身份：`AI-reviewer-two-/root/waiver_review_two`；2026-09-10。依据 owner 对两个独立 AI reviewer 的授权。不冒充人工签名。未查看另一 reviewer 的结论；直接读取两份原始 SOURCE_REGISTRATION 及其登记的生产工件。未读取 holdout、私有验收或参考答案。

## Agent级背景

本次没有重新运行 Agent 或训练；旧15题 Agent结果保持 Strict 0/15、completed 0/15、mutation 3，原终止原因不改写。下面是历史来源与Selector数据诊断，不是Agent能力改善。

## 决定和替代关系

**accept，但只批准两份下列固定 registration 的14个来源（排除 RP-WEB-02）且 roles 必须精确为 `["selector_intent"]` 的来源身份豁免。** 本报告收紧并替代 WAIVER_REVIEW_TWO.md 中容易扩大解释的整体 accept；不得把旧广义意见用于15来源或其他角色。原草稿保持 draft；新的 accepted waiver 必须明确绑定本限定审阅及外部作用域执行记录。

14个保留来源没有执行 run_command 或 check_command；五项历史 check_command 均集中在被排除的 RP-WEB-02。因此命令入口、check写入丢弃、失败命令scope和超时输出修复，没有作用于保留来源的已执行动作。结合逐Selector边界重建与原始输入token验证通过，支持这个有限集合的来源准入。不能推广到未来来源、其他角色或新模型行为。

## 原始来源身份

- `/home/chase/GitHub/RWKV-LH/data/experiments/REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/SOURCE_REGISTRATION.json` SHA-256 `53b6e4acf718671f380eae2c9c4453778cc10ca8a3641385e35b243ec9836d87`
- `/home/chase/GitHub/RWKV-LH/data/experiments/ULTRADATA_OFFICIAL_COLLECTION_R6_20260910/SOURCE_REGISTRATION.json` SHA-256 `448a3f01231d234c8776883eb0f07545d39e3b3dd11a8a22fbb5ba51f59882f5`

14来源候选注册表须从上述记录逐项无改写拷贝，只删除 RP-WEB-02，再精确pin其完整文件SHA。不得改 source_run_id、project_family、protocol_sha256 或任意artifact路径/hash，不得顺手附加未审阅标签。

## 独立全量事实检查

用独立脚本调用生产 load_source_run 读取全部15来源，随后 extract_source(roles=(selector_intent,)) 在内存中重建。为诊断当前源码，脚本直接传入草稿六项SHA映射；这不是通过 decision=draft CLI准入，也不构成正式waiver使用。未生成数据集目录，未运行pytest、模型或训练。全部源工件SHA、SQLite完整性、因果时间线、模型checkpoint均经过生产加载器验证。

| 来源 | 保存动作类型/数 | Selector可抽取 | 待标签复核 | 本限定范围 |
| --- | --- | ---: | ---: | --- |
| RP-API-01 | search_text 4 | 6 | 6 | accept |
| RP-API-02 | search_text 4, read_file 1 | 6 | 9 | accept |
| RP-MAINT-01 | list_directory 3 | 3 | 6 | accept |
| RP-MAINT-02 | list_directory 2 | 6 | 18 | accept |
| RP-CLI-01 | search_text 3 | 3 | 6 | accept |
| RP-CLI-02 | search_text 2 | 3 | 6 | accept |
| RP-DATA-01 | search_text 2, read_file 3 | 2 | 13 | accept |
| RP-DATA-02 | list_directory 3, search_text 1 | 6 | 6 | accept |
| RP-FULL-01 | list_directory 2, read_file 3 | 5 | 10 | accept |
| RP-FULL-02 | list_directory 1, search_text 1 | 5 | 1 | accept |
| RP-WEB-01 | list_directory 1 | 3 | 18 | accept |
| RP-WEB-02 | list_directory 1, search_text 1, check_command 5 | 21 | 0 | 排除 |
| ULTRA-Code_00001 | write_file 3 | 6 | 6 | accept |
| ULTRA-Code_00002 | write_file 2 | 3 | 21 | accept |
| ULTRA-Code_00003 | write_file 1 | 3 | 0 | accept |

保留14来源合计42个已执行动作，全部记录为 succeeded：36个list/search/read观察动作，6个write_file动作；run_command 0、check_command 0、失败动作0、命令超时0。write_file集中于三个Ultra来源，各3/2/1次，均写main.py；前两题重复写相同内容，不能把6次动作计为6次mutation。写文件是登记的明确副作用，不是check_command隐式写入。本次没有独立重放文件系统，不把“无命令”扩写成已证明任意外部副作用不存在。

RP-WEB-02的 A00003–A00007 五次 check_command 全部 exit 1 / CommandFailed，输出为把ELF当Python解析导致的 null bytes SyntaxError；无超时标记，stdout为0、stderr 115字节。原调用意图是打印Python版本，故旧错误直接属于修复改变的执行语义；即使该来源21个Selector输入字节能重建且单一合同给出自动标签，也不足以支持把整源当当前执行语义等价来源。按整源保守排除，不挑其局部好边界。

剩余14来源共186个Selector菜单lane边界：60条可抽取候选、126条因无唯一合同/已执行推进标签而保留待复核。生产extract_source在该排除点之前已完成checkpoint transcript逐字节比较、input/menu/eligible摘要、模型zero身份、原始suffix解码和server输入token绑定。60条返回样本token_ids_complete全部true；126条排除原因均为标签权威不足，没有缺失菜单、字节不一致或token缺失排除。186是lane数量，不是186个独立任务或186个已批准训练正例。

RP-CLI-02保存的状态为running，符合当时Native create未确认中断；本审阅不把该未返回请求补成完成，也不根据404重发代码推断历史执行成功。仅已经保存且重建通过的Selector边界可作为候选，未确认的Native变更仍是未确认。

## 作用域执行要求

waiver v1 schema不支持source/role新字段，不得伪造字段或修改生产准入器来宣称已有作用域保护。外部审计wrapper方案可以接受，前提是执行前校验：两份原registration SHA、14来源精确集合及逐项记录相同、派生registration完整SHA、六项waiver文件与SHA、roles精确单项selector_intent，并以固定参数调用生产CLI。禁止透传可覆写registration/role/waiver的任意额外参数。输出须记录wrapper自身SHA、命令、来源注册SHA和waiver SHA，核验provenance角色/来源集合，不满足就拒绝。

本意见批准此受限方案；实际wrapper代码与最终派生registration/accepted waiver字节仍须由主任务冻结核对，不能把一张不受作用域约束的accepted waiver单独交给任意CLI使用者当通用通行证。生产checkpoint与token硬校验保持原样。

## 标签、切分和训练门

60条自动候选不是完成训练集验收；126条待复核继续待复核。既有人工或AI标签劳动只有在同一输入、请求、目标与证据hash绑定仍成立时可复用，本次没有完成这些标签逐条复核。角色语义分工和后序Auditor标签权威不在本次许可范围。

排除整源会改变集合和覆盖，必须按既有预注册的scope、覆盖、相似度与固定切分方法重新计算；不能降低阈值或改评分来让新集合通过。旧跨切分污染结论不因本次准入自动解除；现有固定回归身份/覆盖/标签门不改。未通过完整split/coverage/label验证前不得把候选标valid，不创建正式data/datasets版本，不宣称可以训练。

## 可复核证据

- 独立诊断脚本 `/home/chase/GitHub/RWKV-LH/temp/waiver_scoped_review_two_20260910.py` SHA-256 `81777c82db218f2bdab4b2230f2d7890c8f22b0767f123f74c515979b3e5a975`。
- 全15来源动作及Selector计数 `/home/chase/GitHub/RWKV-LH/data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/WAIVER_SCOPED_REVIEW_TWO_EVIDENCE.json` SHA-256 `04f1b6662f94ee4d02e58e59989c9b844f8bc5c229314fc65268de9bceea1f55`。
- 本轮未运行pytest，因此不与主任务的pytest临时目录争用。

## 最终具体产物复核

已独立核对 SCOPED_SOURCE_REGISTRATION.json：source_runs精确等于两份原registration按原顺序拼接并移除RP-WEB-02，其余14条逐字段相同。coverage_scope沿用同一已冻结SHA，没有改阈值。注册SHA `0317d262960128fd43884ee7191c69bb15b5e54d645912446618b4c99366f6f7`。

SCOPED_WAIVER_PROPOSAL.json为不可直接提交的嵌套proposal；proposed_waiver按UTF-8、ensure_ascii=False、indent=2及末尾换行序列化的SHA为 `c3e2bc4d5fbeb4ee99089ed387d38d1ce231035fdcc2697e420506af97aac85e`，与声明一致。六文件路径和frozen/current配对与独立审阅一致，rationale显式仅允许限定14来源Selector。

已读最终 temp/extract_scoped_waiver_r1_20260910.py，SHA `86f47b3765c422940b9e1958fff9996c5bebb910c39e894a163702b9a9e4595a`：无调用者参数入口，使用require/SystemExit而非可被python -O禁用的assert；注册SHA/精确ID集、proposal、accepted waiver及两名reviewer决定/role/registration/waiver/wrapper SHA联锁检查后才启动固定生产CLI，并用独占新文件写入调用证据。运行时不再重新验证原两份注册，是因为派生表的精确SHA已绑定本次逐字段审阅；任何变动需重审。输出provenance和完整split/coverage结论仍由主任务核验，不是wrapper自动认定valid。

**批准这些具体字节对应的受限提取入口。** 本reviewer未运行正式CLI提取、未创建accepted waiver、未修改wrapper或生产代码。批准记录见SCOPED_APPROVAL_TWO.json。
