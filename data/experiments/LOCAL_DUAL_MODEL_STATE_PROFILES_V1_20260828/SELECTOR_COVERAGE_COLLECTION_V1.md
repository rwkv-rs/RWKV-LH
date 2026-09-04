# Exact-Tool Selector Coverage Collection v1 — 预注册

## 状态

- 登记时间：2026-08-28（Asia/Shanghai）
- 状态：fixture 采集清单已生成并冻结；runner、40-case preflight 和正式模型采集尚未开始
- 上游候选池 manifest：`a2d78fcefecabdbe4a9638fc2112580e9d69994053f40ef307c11cc33f0c9a38`
- 上游 coverage：`522cdfa3a9a82fee5f2613c315381f4fe826a23853f1ce2f8e191c381ce4b9fa`
- 固定 menu digest：`d3b4f283db156f883d012d9d05f5b2e0d8f3bae8ddd7c42c8af8d6a9671e3d2e`
- fixture 清单：`data/datasets/rwkv_lh_exact_tool_coverage_v1/cases.jsonl`
- fixture generator SHA-256：`342886d2bebc225d7da4be6fbe0b80c7447135d2d75248daad0b0298a7df00e8`
- fixture cases SHA-256：`665705b6fe24f415bae2383128968786c128364ae6ef46562b53bd06534f1cd8`

本协议只补充可验证的事实来源，不放宽 `LOCAL_DUAL_MODEL_STATE_PROFILES_V1_20260828/PROTOCOL.md` 的任何训练、split、去重、指标或原始输出门槛。

## 已确认缺口

现有可审计池去重后 1002 行、49 个语义 family。20 类正式 test 均未达到每类 30；其中以下 5 类总计仍为 0：

- `ABSTAIN`
- `append_file`
- `delete_file`
- `move_file`
- `search_text`

旧 `web_search`、Round71 重规划、通用 agent mix、生成式 `select_tool` 数据和 order-ensemble 选优输出不得映射或计入。

## 固定采集拓扑

```text
frozen fixture + mechanical expected operation
        ├─ SelectorInput(task/stage/progress/menu descriptions only)
        └─ expected operation -> 13.3B Executor(full one-tool schema + target)
                                      └─ raw output append-only commit
                                             └─ parser derived view
                                                    └─ Harness execution + verifier
```

fixture 的 expected operation 是外部预注册真值，不由待训练 2.9B 或 13.3B 自标。13.3B 不重新选择工具，只按已提交 operation 绑定参数；这与正式 selector→executor 边界一致。

## 数据规模与 split

- 为避免现有类不均衡，固定为 20 类各 300 个独立语义 family，共 6000 个 family。
- family ID 在生成时按既有 `sha256(family_id) modulo 10` 固定选择为 train/dev/test = 240/30/30；不得采集后移动 split。
- train/dev/test 使用三个分别登记的 surface/template bank；同一模板实例、路径、内容、命令、证据文本或反事实对不得跨 split。
- 正式入池前继续使用 `utf8-byte-5gram-cosine.v1`、同 label 阈值 `0.95`。去重后任一类 test 少于 30，整批不得冻结。
- 先运行每类 2 个 family 的 40-case preflight。preflight 只验证合同和执行器，不计正式指标；正式 6000-case 运行使用全新 family ID。

已冻结清单本身的 Selector projection 已用同一算法做类内全量审计：6000 输入、6000 保留、0 删除，全局最高相似度 `0.908844765343`。这只证明 fixture 清单不会在既定去重口径下坍缩，不代表任何一行已经通过 13.3B Executor、Harness/verifier 或可以进入训练池。

## 类别事实与 verifier

- 18 个 Harness operation：13.3B 原始输出必须解析为已提交的同名 operation，参数通过 schema，Harness `success=true`，并由 operation-specific verifier 复核 workspace/result 后才产生正标签。
- `final_answer`：fixture 起点已经具有完整且通过摘要验证的完成证据；13.3B 原始 final text 必须非空、逐字交付、三段 SHA 一致。不得修复、截断或替换。
- `ABSTAIN`：仅来自机械边界集合（缺少必要可观察信息、请求超出冻结 menu、互斥目标无法唯一选择、未授权/不安全范围）。不调用 Executor，不伪造 `raw_output`；记录 `raw_output_applicable=false`、边界规则 ID 和规则输入摘要。
- `search_text` 与旧 `web_search` 完全分开。fixture 只搜索冻结 workspace 内 UTF-8 行，verifier 校验有序 locator、分页 union、token bound 和零 workspace mutation。
- `append_file`、`move_file`、`delete_file` 是非幂等/破坏性动作，只在每例独立临时 workspace 执行；执行前后 digest 和路径存在性必须完整记录。
- `run_command` 只允许 fixture 自带的 argv、`shell=false`、固定 cwd/env/timeout；不得下载或访问 fixture 范围外路径。

## 原始输出硬合同

1. 禁止 guided/constrained decoding、grammar、`allowed_token_ids`、`bad_words`、`logit_bias`、隐藏重试和 output repair。
2. 每次 Executor response 的原始文本、token IDs、finish reason、sampling、model/profile/engine identity、UTF-8 bytes/SHA 必须在解析前只追加提交。
3. parse/schema/Harness/verifier 失败保留原始记录并显式拒绝；不得覆盖或删除。
4. 允许重新采集一个失败 family，但它必须是新的 attempt causal record；旧 attempt 继续保留且不能计为正标签。
5. Selector 训练行只引用通过的 attempt；完整 trajectory 文件同时保留全部失败 attempt。

## 运行前门槛

- 只能使用协议固定 SHA 的 G1i 13.3B Executor 与已验证的本地 `vllm-rwkv` build/profile manifest。
- server 当前正在运行的 ReproBench 2.9B 进程不属于本实验，不得停止、重启、抢占或借用其未验证 endpoint。
- fixture generator、runner、verifier 和 engine diff 各自登记 SHA；fixture 全量生成后先冻结 manifest，再允许任何模型请求。
- 40-case preflight 必须达到：raw retention 100%、operation handoff 100%、Harness+verifier 100%、forbidden decoding field 0、workspace 隔离 100%。

## 完成条件

- 6000 个 family 全部有终态；失败/重试记录完整。
- 去重、family split 和跨 split 污染检查通过。
- 每类正式 test 至少 30，且 train/dev 非空。
- `--freeze` 成功生成 train/dev/test，所有文件和 generator/runner/verifier/model/profile/engine 均有 SHA。
- 冻结后才允许提取 2.9B Hidden/WKV 特征、训练 MLP/state 或开始 F1/F2 消融。
