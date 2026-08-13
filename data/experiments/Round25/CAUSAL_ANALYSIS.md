# Round25 全 90 题第一断点因果分析

## 冻结结果

- RWKV-E2E-90 v1，Basic / Medium / Hard 各 30；固定并发 8、每题 200 transitions。
- 源码与 dirty diff 摘要见 `RUN_PROTOCOL.json`；模型、运行时与 tokenizer 见 `runtime_doctor.json`。
- Strict `0/90`，External `0/90`，Agent completed `0/90`；False Positive `0`，False Negative `0`。
- 47 题 `not_created`，43 题 `blocked`；全部为 `0 task / 0 attempt`，共 224 次模型请求。
- 因此本轮没有执行 Harness action，也没有实际经过 typed outcome、artifact revision、Task commit 或 Goal proof；不得用本轮
  结果评价这些下游模块或 RWKV 的任务执行能力。

## 从后向前的共同因果链

`Strict/External=0` ← 没有任何 artifact 生产 ← 没有 action ← 没有 Task materialize ← Goal/Plan 模型边界拒绝。

第一断点不是 90 个答案错误，而是三层接口缺陷叠加：

1. Goal v2 要求 RWKV 为每个 criterion 复制 USER REQUEST 的逐字 substring。模型普遍给出了语义正确的原句/短句，但会把反引号
   改成单引号、去掉句号、改变大小写或忠实缩写。Controller 把 provenance 的字节一致性错误地变成 Goal 创建 gate。
2. Plan prompt 已要求 `long-horizon.plan.v3`，但透明外壳 normalizer 的注册表仍只允许 v1/v2。32 题输出了新协议并使用常见
   `task_graph.tasks/nodes` 外壳，却在展开外壳之前被“unsupported registered plan envelope schema”拒绝。这是纯代码接口漏接。
3. Plan v3 又强制每个 Task 重复输出 `required`、`dependency_outcomes`，并把 `operation_kind` 限死为六个抽象词。RWKV 更稳定地
   使用 `read/write/write_file/read_json/check` 等自然动作标签；这些标签只用于状态说明，却被当成执行 gate。协议元数据负担超过
   它对调度的实际贡献。

下游放大方式一致：第一次 contract error 后，修复提示带入长 rejected output，第二次请求更长；但没有降低字段负担，也没有指出
normalizer 自身不支持 v3，因此同一问题重复，最终 `not_created/blocked`。恢复、Task commit 和 proof 没有机会介入。

## 47 个 Goal 第一断点

46 题有 criterion，但至少一个 `source_quote` 不是逐字 substring：

- Basic：B06、B09、B12、B14、B17、B18、B19、B22、B23、B27。
- Medium：M02、M03、M04、M06、M07、M08、M09、M11、M12、M17、M19、M21、M22、M24、M27、M29、M30。
- Hard：H01、H02、H03、H06、H07、H10、H11、H13、H14、H15、H17、H18、LH01、LH02、LH03、LH05、LH06、LH07、LH11。

典型原始证据：B06 把用户反引号包围的 `` `---` `` 写成 `'---'`；B12/H17/H18 在原句末补句号；H07 把
`Run tests with unittest discovery` 写为 `Run unittest discovery`；M19 把 `Use string keys for status codes` 写为
`Use string status keys`。这些 criterion 语义仍由 RWKV 生成，架构不应把展示级字节差异当作 Goal 无效。

唯一不同项是 M15：第二次 Goal 输出没有 `success_criteria` 数组，属于真实模型协议缺失，必须继续 fail closed。

## 43 个 Plan 第一断点

### A. 新协议被旧注册表拒绝：32 题

B01、B03、B04、B05、B07、B10、B11、B13、B15、B16、B20、B21、B24、B25、B26、B28、B29、H04、H08、H09、
H12、H16、LH04、LH09、LH12、M13、M14、M18、M20、M25、M26、M28。

这些题的最后输出均声明 `long-horizon.plan.v3`；主要使用 `task_graph.tasks`，少量使用 `task_graph.nodes`。其中多题已给出
subject/member/phase、effect target、expected outcome 与 postcondition。第一断点是 `rwkv_lh/tool_protocol.py` 仍只注册 v1/v2，
不是 Task 内容错误。外壳展开必须保留 raw/normalized payload，不得生成或改写 Task 字段。

### B. 过度必填/封闭枚举：6 题

- B02、LH08、M01、M26：缺 `dependency_outcomes`；多数还缺 `required`。
- B08：`operation_kind=read_file`；LH10：`operation_kind=read`。

空 `dependency_outcomes` 的语义可以由唯一 v3 协议定义为“无 outcome 条件的普通依赖”，不需要 Controller 向 RWKV payload 填字段。
`required` 也不应在每个 frontier Task 重复：进入当前 frontier 的节点默认要执行，只有显式条件边未选中时 `skipped`。operation 标签
不参与调度，不应使用封闭枚举 gate。

### C. 仍应 fail closed 的真实结构缺失：5 题

- B30、H05、M05：最后输出 tasks 为空。
- M10：最后输出不是 plan schema。
- M16：`task_graph.nodes` 中节点没有全部显式 dependencies，无法无损确定图边。
- M23 的最后错误为 `dependency_outcomes` 值不是数组；它同时输出 9 个节点。该字段若出现必须继续类型校验。

这里 M23 与上列合计按最终错误计为一题，故 Plan 总数仍为 43。

## 下一结构：只保留一个在线协议

1. 在线 Goal 不再要求模型复制 source_quote；criterion provenance 绑定到 immutable `original_request` 的 digest，criterion 的语义文本
   仍完全来自 RWKV。旧 Goal v1/v2 只在 checkpoint 载入时迁移，不构成在线第二协议。
2. 在线 Plan、obligation replan、failure replan 只接受 causal v3；删除 v1/v2、bare-task 和旧 obligation/replan 在线 fallback。
3. v3 Task 的唯一核心是 id/title/description/explicit dependencies/postcondition。subject/member/phase/effect targets/expected outcomes/
   dependency outcomes 是同一 Task 结构内的渐进元数据：出现就严格校验，不出现就不制造字段。普通 dependency 没有 outcome 条件；
   只有 RWKV 显式提供的条件边参与 typed branch。
4. `operation_kind` 改为 RWKV 自由标签或删除，不再参与 gate；真正可执行动作仍只来自后续单工具 G1i contract。
5. “frontier≤8”按同时 ready 的根/边界节点计，不按模型返回的完整有向图总节点数计；不得截断、删改或替模型选择节点。
6. 透明 normalizer 只展开白名单 `task_graph.tasks/nodes` 外壳并保留审计；不得补 dependencies、postcondition、criterion、参数或答案。

Round25 为结构失败实验，标记 `do_not_upload_as_better`。完成单协议清理后必须重新运行全产品测试、LH-Control-30、E2E-90
catalog validation，并以新的 Round26 全 90 题验证；不得从 Round25 hidden acceptance 生成 case 特判。
