# Round51 预注册实验协议：精确 `tool_name` 键名归一化

状态：在任何 Round51 代码修改和模型运行之前登记。

## 冻结证据

- 已上传最佳代码：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- 工作分支：`chase/g1i-tool-protocol`
- 已上传完整基线：Round46 full90，Strict `31/90`、External `32/90`、FP `24`、FN `1`
- 直接父候选：Round50 两阶段 RWKV 工具选择，Strict `6/90`、External `11/90`、FP `8`、FN `5`
- Round50 results SHA256：`b400075a1639162e2f5d9af08247ba9698a0a394a8a98b4373e3bcc3ff9280f8`
- Round50 run protocol SHA256：`6d6d398b20b764feaaa53ba00f3a16a2c3b0bb66a7079f86dfdbda3a5ae2ffb8`
- 冻结 Codex reference SHA256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
- Round50 观察：62 题在 action materialization 终止；49 题最后一次协议错误均为字段集合恰好 `tool_name,arguments` 的语义完整调用被拒。

## 唯一架构变量

透明工具格式注册表新增一个精确 wire form：

```json
{"tool_name": <原值>, "arguments": <原值>}
```

转换为：

```json
{"name": <原值>, "arguments": <原值>}
```

只改键名，两个值对象按原引用语义进入既有 canonical validator。归一化必须记录 raw payload、normalized payload、各自 digest、固定 transformation 名和新的 normalizer version。

## 明确不改

- 不接受 `tool_name` 加平铺参数、`input_parameters`、缺失 arguments、多个调用名或额外字段。
- 不从上一阶段自动补 name，不从 schema 猜 name，不补/删/改 arguments。
- 不修改 RWKV 的工具选择、参数、Task、criterion、evidence binding、final answer 或最终产物。
- 不新增规则来判断任务答案，不读取 hidden acceptance 后在线改策略。
- 不修改 Round50 两阶段选择的 prompt、预算、温度、目录顺序或恢复逻辑。

## 因果假设

若 Round50 的主要下降来自接口接缝，则新增别名后：

1. 精确 `tool_name,arguments` 输出应产生 `model_protocol_normalized`，而非 unknown-field error。
2. 对同一调用，归一化前后的工具名和 arguments 必须完全相同。
3. Strict/External 应显著高于 Round50；若仍低于 Round46，则说明两阶段结构本身或其他链路仍是主要瓶颈。
4. 扁平参数、未知工具和语义错误应继续 fail closed，不能因本改动成为通过。

## 固定验证

1. 单元测试：新增正例、额外字段/扁平字段/冲突字段反例、raw/normalized 审计链接；运行完整 offline suite。
2. LH-Control `30/30` 与 catalog validate-only `90/90`。
3. 31 文件确定性架构验收。
4. 固定 E2E-90：`--suite all --max-transitions 200 --concurrency 8`，输出到 `data/experiments/Round51_full90`。
5. 运行 `scripts/analyze_rwkv_round.py`，同时与 Round50 父候选和 Round46 已上传最佳比较。
6. 逐题检查所有非 Strict 案例、所有相对 Round46/Round50 改变的案例和全部 FP/FN；脚本汇总不代替人工因果判断。

## 保留与上传门槛

候选只有同时满足以下条件才替换并上传当前最佳：

- Strict E2E `>31/90`；
- FP `<=24` 且 FN `<=1`；
- Basic/Medium/Hard 分组完整报告，没有通过隐藏验收特判获得的提升；
- offline、LH-Control、catalog 和 31 文件架构回归全部通过；
- 所有 delivered final output 与 raw RWKV final output 保持原政策下的字节一致；
- 精确别名以外的协议形状继续拒绝。

若未达到门槛，则回退 Round50 两阶段代码和 Round51 别名代码，保留实验数据与分析，不把失败候选上传为最佳架构。
