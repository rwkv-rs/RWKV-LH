# 本地 13.3B 完整 Planner 输出检查

这次诊断返回了一个完整 JSON 对象，但它还不是可被当前 Planner 契约接受的计划，更不是 Agent 完成结果。完整模型输出、分段对象和错误均来自同一次保存的回复，没有补生成、修补字段或重算历史实验。

用户随后已授权移除 Planner 的五步及步数限制。本报告中的 `GoalPlanPatch.from_model_value` 调用发生在该修改之前；原始合同检查源码 SHA 已保存。最终输出的 **7 个阶段、19 个步骤**只是规模描述，数量本身不作为新口径缺陷。

## 实际输出与解析结果

本次 HTTP 200，`finish_reason=stop`，耗时约 66.047 秒；服务 usage 为输入 1,984、输出 4,876 tokens。诊断将单次上限提高到 8,192；没有因此修改生产 1,800 上限。

完整 `content` 从 `>We need ...` 开始，只有一个 `</think>`，其后紧接最终 `{...}`，结尾完整。此前模板核对表明输入停在 `<think`，生成的首个 `>` 会补全这个跨输入/输出边界的标签；现有 decoder 接收的仅是生成内容，因而看到的开头是 `>`，不是它允许规范化的完整 `<think>` 包装。

| 检查 | 结果 | 限定 |
| --- | --- | --- |
| 全部 content 直接 `json.loads` | 失败 | JSON 前仍有思考文本 |
| 全部 content 交给现有 decoder | 失败 | `supervisor content is not one JSON object` |
| 唯一 `</think>` 后的原样后缀 `json.loads` | 通过 | 仅离线观察，不是生产截取规则 |
| 后缀交给现有 decoder | 通过 | 无 normalization，与 `json.loads` 得到同一对象 |
| canonical 原请求经 `GoalPlanRequest` 构造及回转 | 通过 | 使用保存消息，未发明协议字段或请求场景 |
| 后缀对象交给修改前 `GoalPlanPatch.from_model_value` | 失败 | 首个实际错误：`success_evidence item must be non-empty` |
| 将 patch 应用于真实 RollingGoalPlan | 未执行 | constructor 没有产出合法 patch；未跳过验证器继续应用 |
| 项目执行、完成或 Stage Checker 验收 | 未验证 | 本次没有执行 Agent 工作流 |

## 字段与计划关系问题

以下清单来自原始 JSON 的只读字段/关系核对，不是修补后再次调用验证器的结果。步数限制移除后，这些问题仍与字段、阶段和读写语义有关：

- **19 个步骤的 `success_evidence` 全部是字符串**，合同要求字符串数组。这与实际 constructor 的首个错误对应；没有自动把字符串包成数组。
- **8 个 obligation 全部多出 `success_evidence` 字段**；义务对象的固定字段只有 `obligation_id`、`predicate`、`required_phases`。
- **12 条依赖指向同一阶段**，例如阶段 1 的 S1-2 依赖同阶段 S1-1。当前阶段语义要求同阶段步骤彼此独立，依赖必须指向较早阶段。
- **11 个 mutate 步骤携带非空 `read_roots`**。当前 phase 约束要求观察放在此前的 observe 步骤中，mutation 的 `read_roots` 为空。
- 阶段 4 的 **4 个步骤都写 `server.py`**，阶段 5 的 **3 个步骤都写 `verify_public.py`**，与同阶段无读写冲突要求不符。

顶层五个字段齐全、JSON 大括号完整，并不消除这些问题。没有重命名字段、调整依赖、移动阶段、拆分读写或删除多余字段后再次宣称通过。

完整思考段中还出现“没有现有代码，需要创建 server.py”的表述，而 canonical workspace 已列出 `server.py` 和其他文件；最终计划又安排先读取这些文件。这里保留这种上下文使用不一致，不能把推理中的断言当作真实工作区状态或执行证据。义务是否穷尽原始项目需求、未来能否产生真正的重启/并发/幂等验证证据，本次未验证。

## 思考段与最终 JSON 的 token 长度

已先核实部署 engine 的 plain `TokenizeCompletionRequest` 支持 `prompt`，然后对同一保存文本的精确切片调用 `/tokenize`。共 5 次 tokenization，生成请求为 0。

虽然请求显式设置 `add_special_tokens=False`，返回的每段 token 列表仍以 native BOS `0` 开始，故同时给出接口数和去掉这一个实际观察到的前导 BOS 后的数：

| 原样文本区间 | 接口 count | 去掉各自 1 个前导 BOS |
| --- | ---: | ---: |
| `</think>` 前的思考正文，包含生成开头 `>` | 2,253 | 2,252 |
| 思考正文连同 `</think>` | 2,255 | 2,254 |
| `</think>` 后的最终 JSON | 2,623 | 2,622 |
| 全部生成 content | 4,876 | 4,875 |

最终 JSON 自身的重编码长度已经超过本次仍使用的生产 1,800-token 上限。该事实解释了为什么这份完整输出不能直接当作原预算下可用的返回；它不保证增加预算即可得到合法计划。

本次响应没有返回原始生成 `token_ids`。上表是服务重新编码各段的精确返回值，**不是已证实的采样 token 分区**。分段边界的编码可能改变，输出 usage 也可能含不可见停止 token；不能简单相加或因整段重编码数碰巧同为 4,876 就声称已恢复原生成序列。

## 修改前来源与可复核工件

本次实际调用验证器时记录的源码 SHA-256：

- `rwkv_lh/goal_loop_protocol.py`：`4fa73dc26321d304b812dfbbc09e6a4eeb605c2fd600b2064a7db85567a7991b`
- `rwkv_lh/supervisor_openai.py`：`5ee0e8580b0fb77fd6a6ed95c04b9044034ada7c3c4450c94681ad47c87252e3`

得知步数限制变更后未再次导入生产验证器或重跑旧结果。

- `OUTPUT_INSPECTION_PLAIN_COMPLETE.json`：本次原始完整请求和回复，由主代理保存。
- `PLAIN_COMPLETE_OFFLINE_CONTRACT_TOKEN_AUDIT.json`：全量对象、实际 decoder/constructor 结果、canonical 请求检查和 5 份 tokenization 返回。SHA-256：`e35da21c31aca12d6a59b39110b55e5313b257f973d68f24cca290669eb812ea`。
- `PLAIN_COMPLETE_FIELD_SEMANTIC_FINDINGS.json`：逐项步骤/字段/阶段问题及 BOS 明细。SHA-256：`102943f30308a05be80ca1d515da6bfbb6c252abf1dfa6ede1ca078b6a23dee9`。

没有修改 parser、评分、生产参数、State 或已有实验；本次诊断不属于 baseline，也不用于生成 StateTune 数据。
