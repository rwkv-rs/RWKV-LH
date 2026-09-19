# R23 数据补齐检查点：尚未达到1000条

本轮新增Agent运行0，completed/Strict不适用，不能把离线纠正通过数当作RWKV独立交付成绩。没有启动训练，没有子代理或推理API调用，没有更新GitHub。Owner后续已授权完成数据后训练、测试与报告，授权另见OWNER_TRAINING_AUTHORIZATION_20260919.json。

## 正式库存

起点333条；当前正式636条，新增303条，距1000还差364条。这里的单位是生产调用边界，不是独立项目。共524个来源ID、487种源文件内容SHA。具体包与manifest SHA见CHECKPOINT_INVENTORY.json，后续新增以STATUS.json为准。

新增均为当前Codex亲自编写、审阅的真实RL Code失败边界纠正，使用既有verified_stdio准入。一次语义审阅与真实隔离执行分开，不伪称双独立审核。原始失败候选、失败的纠正候选和未执行样本均保留；没有用相似题、重复读取或改写答案凑数。R23新增不是仓库多文件交付数据，算法写入偏重仍是覆盖限制。

|标签类型|正式条数|
|---|---:|
|executed_read|122|
|independent_review|65|
|verified_coding|4|
|verified_command|59|
|verified_stdio|386|

## 已完成核验

- 636条target-only mask检查通过，最长24555/24576 token，原输入逐token重放；未裁剪上下文。
- 新增303条在最终冻结时重新执行原始失败→修正通过，共9891个修正后固定用例通过；准入器此前另有一次验证。
- 跨包请求/输入checkpoint去重、源文本UTF-8字节5-gram余弦0.9去重、既有回归隔离及R5/R6训练排除SHA检查通过。未读取最终Holdout。
- 超上下文候选留存拒绝记录。另行选择真实较早调用点时，核实当时完整TASK已进入输入；不注入后续观察，不伪造State谱系。
- 模型、tokenizer、当前唯一协议及训练加载器均沿用已登记身份。生产源码和owner五处修改逐文件SHA未变。

公开额外算法检查见PUBLIC_CROSSCHECKS_LATE.json等，检查用例不算训练数据。误判不能根据隐藏预期答案修补；尚未解释的验证失败继续隔离。

## 尚未完成

1000条目标、全量数据冻结、当前候选训练、zero/候选任务对照和最终成品验收均未完成。不能因为库存增长宣称模型能力提升。当前会话结束后没有后台Codex自动写纠正；只有显式启动的验证进程会继续运行。

训练首选一轮、zero初始化、当前State-only优化器和target-only mask，具体数据SHA/step数/时长/预算在最终数据冻结后注册。历史300条一轮75updates约2564.51秒仅作资源参考，不直接外推为保证。服务器只读检查显示GPU0空闲、约621GiB可用；未启动服务或动其他GPU。

成品入口发现独立工程缺陷：pyproject注册的rwkv-lh指向已删除scripts.run_long_horizon，实际--help报ModuleNotFoundError。原始失败见CLI_ENTRYPOINT_RED.txt。下一轮修到现有CodingJob执行入口，并用先失败后通过回归及真实演示核验；不恢复旧角色流水线。

## 证据身份

CHECKPOINT_INVENTORY.json SHA-256：`ff0dc6deded59df1e01831455fd461cca8126612438f6aee3df55316ecd2689c`。最终源码核验和工程全回归另见FINAL_CHECKS.json；该文件生成前不得宣称全回归通过。

本检查点完整工程回归：1894 passed、0 skipped（377.59秒）。生产源码与登记逐文件SHA一致，owner五处修改原字节保持。1000条与训练目标仍未完成。
