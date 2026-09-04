# StateTune 下一步

## 1. 冻结训练输入

正式生成数据前，先实现一个由 runtime 和数据生成器共用的 full-serving renderer。训练序列必须等于模型从角色初始 State 到目标输出位置累计消费的完整 UTF-8 token 流，不能只保存其中的业务 JSON。

每条训练记录固定包含：

- `prompt`：完整线上输入。
- `target`：唯一监督后缀。
- `text`：`prompt + target`。
- prompt、target 和完整 text 的 SHA-256。
- prompt、target、完整 text 的 token IDs 与 token 数。
- renderer、parser、tokenizer 和 verifier 的 SHA-256。

固定要求：BOS 为 `0`，上下文长度为 `4096`，不得截断，loss 只覆盖 target suffix，不加入长 CoT。

## 2. 固定各角色格式

Selector：

- 输入必须由 `rwkv_lh.exact_tool_selector.input_protocol` 的生产 renderer 生成。
- 每条因果序列先使用 `render_bootstrap`，再按真实顺序追加一个或多个 `render_step`。
- `canonical`、`rotate_8`、`rotate_17` 三种菜单顺序都要生成；同一语义样本的三种顺序使用同一目标并进入同一 split。
- Head 类别索引始终使用 `NETWORK_EXACT_TOOL_LABELS` 的固定顺序，不能随菜单顺序旋转。
- target 只能由 `rwkv_lh.goal_state_protocols.selector_intent.render_target` 生成。
- 普通可执行 frontier 不生成 `ABSTAIN` target；`final_answer` 只用于已经满足终止条件的独立样本。

Executor：

- 输入必须从线上使用的 clean action State 开始，包含受控因果投影，并以 `rwkv_lh.goal_state_protocols.executor_args.render_generation_prompt` 生成的内容和 continuation anchor 结束。
- target 只能由 `rwkv_lh.goal_state_protocols.executor_args.render_target` 生成。
- target 必须是一个规范 JSON 对象，`function` 必须等于 Selector 已选 operation，`params` 必须满足该工具 schema。
- 不允许换工具、缺省必填参数、Python 字典、Markdown 解释或多个调用。

其余三个角色：

- Step Auditor 使用 `auditor_step.render_prompt/render_target/parse_target`。
- Finalizer 使用 `finalizer_answer.render_prompt/render_target/parse_target`。
- Final Auditor 使用 `auditor_final.render_prompt/render_target/parse_target`。
- 数据生成时仍需保存对应角色在线 generation boundary 的完整输入，而不是只保存 renderer 返回的内部片段。

## 3. 制作 Selector 数据

必须覆盖：

- 23 个可执行 operation 的全部目标类别。
- `observe`、`mutate`、`execute`、`derive_evidence` 四个 phase。
- `read_file/read_json/search_text/file_digest`。
- `check_command/run_command`。
- `write_file/write_json/patch_json/replace_text/append_file/remove_line`。
- `web_search/connector_lookup`。
- 同一步骤的连续多 action 轨迹、工具失败、空搜索结果、协议拒绝和审核缺口。
- 非 JSON 文件在 `read_json` 失败后转向 `read_file`，以及连续无匹配后不再重复 `search_text` 的反例。

每条语义轨迹生成三种菜单顺序版本，但只能有一个固定 operation 标签。三个版本必须共享 `project_family`、split 和父样本关系。

## 4. 制作 Executor 数据

必须覆盖：

- 23 个可执行 operation 的完整参数 schema。
- 每个 operation 的成功样本、参数缺失反例、参数修复和前一步失败后的继续执行。
- 四个 phase 下的全部工具；每条记录保留 phase 标签，以便训练后比较单一 State 和按 phase 分开的 State。
- 同一 handoff 内 operation 恒定；新 action 不携带上一 action 的参数或生成文本。
- `read_file`、`read_json`、`search_text`、写入工具和命令工具的边界参数。

先生成单一 Executor State 所需的完整数据，再从相同冻结源按 phase 派生四份训练视图。不得为四份视图重新划分数据或修改样本。

## 5. 制作其余角色数据

- Step Auditor：同时包含 `continue` 和 `repair`，只引用当前 boundary 可用的 evidence；不生成在线流程不会调用的机械覆盖不完整样本。
- Finalizer：只使用已完成步骤、已提交事实和证据生成 `final_answer`。
- Final Auditor：同时包含 `ready_for_final` 和 `repair`，所有结论必须绑定已有 evidence。
- 五个角色的 WKV 分开训练和导出，不能混合或合并。

## 6. 登记来源并划分数据

每个源样本必须登记：

- 来源、版本、用途和生成方式。
- `source_id`、`project_family`、`source_kind` 和父样本。
- 源文件路径、记录定位符和 SHA-256。
- 输入协议、输出协议和可执行 verifier。

先按 `project_family` 固定划分 train/dev/sealed，再渲染训练数据。确定性反例、父样本和三个菜单顺序版本必须位于同一 split。

相似度固定使用 `utf8-byte-5gram-cosine.v1`，跨 split 最大相似度必须 `< 0.95`。冻结后不得调整算法、阈值或 split。

## 7. 生成前校验

每条样本必须通过：

- renderer/parser round-trip。
- schema 和字段顺序校验。
- 角色职责边界校验。
- operation 与参数执行校验。
- evidence 引用与完成条件校验。
- prompt/target 泄漏校验。
- train/dev/sealed 家族隔离校验。
- 训练 token IDs 与线上 token IDs 逐项一致校验。
- 无截断和 target 起始位置校验。

任一项失败都停止生成，不得跳过失败样本后继续冻结。

## 8. 冻结数据

- 数据集写入 `data/datasets/<dataset_id>/`。
- 来源、生成、校验和泄漏记录写入 `data/experiments/<experiment_id>/`。
- manifest 必须记录数据、renderer、parser、verifier、tokenizer 和所有文件的 SHA-256。
- train/dev 可交给训练流程；sealed 数据保持隔离，在训练完成前不得读取结果。
- 冻结目录不得覆盖写入；任何内容变化都创建新 dataset version。

## 9. 训练与交付

训练期间不得改 prompt、字段顺序、工具描述、类别顺序、split、tokenizer、相似度算法或阈值。

每个 StateTune 产物必须交付：

- 角色和 profile ID。
- State 文件绝对路径与 SHA-256。
- 基础模型 ID 与 SHA-256。
- 数据集 ID、版本和 manifest SHA-256。
- renderer、parser、tokenizer 和 verifier SHA-256。
- 训练配置、随机种子、step 数和完整日志。
- Selector 使用的菜单顺序集合和固定 Head 类别顺序。
- Executor 是单一 State 还是对应某个 phase 的 State。
