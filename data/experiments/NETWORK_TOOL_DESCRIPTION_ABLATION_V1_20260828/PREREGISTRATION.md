# NETWORK_TOOL_DESCRIPTION_ABLATION_V1_20260828

## 冻结目标

验证普通公共网页检索与已支持结构化对象检索的工具描述边界。实验只比较菜单描述，不执行工具、不改变 RWKV 原始输出、不使用关键词路由或控制器重写。

## 冻结数据

- 数据集：`data/datasets/rwkv_lh_ecra_route_v1/cases.json`
- SHA-256：`7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a`
- 固定子集：全部 `public-web-required` 25 条和全部 `structured-connector` 20 条，保持文件原始顺序。
- 每条只使用原始 `instruction`、空的计数型进度和完整生产操作名称/描述菜单。不得传入工作区清单、工具参数 schema、执行历史正文或工具结果。

## 冻结运行

- 模型：`rwkv7-g1i-2.9b-20260805-ctx16384`；报告必须记录服务实际返回的模型标识和基础权重 SHA-256 `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- 推理引擎：本地 `vllm-rwkv` OpenAI-compatible endpoint。
- state tuning：本轮是 2.9B 基础模型的描述边界基线，不加载 13.3B executor state。后续 Selector state/head 训练必须使用同一冻结输入协议并单独登记。
- progressive tool disclosure：开启。
- sampling：temperature=0.05, top_p=1.0, top_k=0, presence_penalty=0.0, frequency_penalty=0.0, penalty_decay=0.996。
- 每条每个 variant 只生成一次；`max_output_tokens=160`；无重试。生成式选择仅作同模型诊断基线，不冒充最终 Hidden+MLP Selector。
- 运行顺序：先完整 baseline，再完整 candidate；两者使用同一任务顺序与同一生产菜单顺序。

## 唯一变量

Baseline：

- `web_search`: `Search/fetch a public exact URL or the general web and return content-addressed exact evidence records.`
- `connector_lookup`: `Query one structured public source for an exact repository, package, scholarly record, weather observation, or alert.`

Candidate：

- `web_search`: `Fetch an explicit HTTP(S) page, or search ordinary public websites and documents. Use for general web discovery; not for a supported GitHub repository/release/commit, PyPI package, scholarly record, or weather observation.`
- `connector_lookup`: `Query an exact supported structured object: GitHub repository/release/commit (including an owner/repository slug or GitHub URL), PyPI package, Crossref scholarly record, or Open-Meteo weather observation. Use when the requested object and field are structured.`

其他工具的名称、描述、顺序和任务 payload 必须字节一致。

## 原始输出完整性

- 每次返回后先将 `raw_output`、`raw_output_sha256`、原始 token IDs、finish reason、response ID/model、state profile 和完整模型会话事件写入 fsync 的 append-only SHA-256 哈希链，再解析选择。
- `postprocessed` 必须为 `false`。
- 不允许诱导、修正、删除、补齐或改写 RWKV 原始输出；解析失败按失败计。

## 固定指标

- 主指标：按类别 first-tool exact accuracy。
- 边界指标：`web_search` / `connector_lookup` macro-F1。
- 协议登记相似度：`utf8-byte-ngram-cosine.v1`，n=5；预测名称对期望名称的相似度另行记录，exact threshold=1.0，不替代 exact accuracy。

Candidate 只有同时满足以下全部条件才可进入生产描述：

1. 45/45 原始记录完整且均可解析为一个展示过的操作；
2. public-web exact 不低于 baseline；
3. structured-connector exact 至少比 baseline 增加 2/20；
4. 总 exact 至少比 baseline 增加 2/45；
5. macro-F1 不低于 baseline 且达到数据集预登记阈值 0.85；
6. 除两条描述外，A/B prompt 差异审计为零。

指标和阈值在运行后不得修改。
