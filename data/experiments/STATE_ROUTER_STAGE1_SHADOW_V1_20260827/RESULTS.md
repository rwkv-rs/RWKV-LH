# RWKV-LH State Router 阶段 1 Shadow 结果

- 日期：2026-08-27
- 状态：基础设施完成；固定 canary 分类失败；Stage 1 未毕业
- 本地引擎：`/home/chase/GitHub/vllm-rwkv@67f0c5996c50dca0ad779da545cb491527de988f`
- 冻结代码 manifest：69 文件，SHA-256
  `d2b9201d84f4bb81a71f9d547931c736c03f5a439e50228833847a4d643f0833`
- canary cases SHA-256：
  `cf650d5c2af0011012c0d88780efc597c90ff392542e9b313d99408911426d53`
- 正式 `results.json` SHA-256：
  `c078b641f21e3387e7352b1d20ca97fb37e954fd93b64cf67415efefd1270e48`

## 结论

Stage 1 的 default-off immutable policy、共享 Controller 接入、独立旁路进程、失败隔离、逐 run
JSONL、文件锁、digest、CLI/Web/主动任务入口和只读 Web 可观察性均已完成。Shadow 对主模型、
工具菜单、工具参数、Controller 状态、Network Gate、Contract Graph 和 State Profile 的影响
字段全部为 false。

固定真实 canary 没有达到 route 门槛：route accuracy 为 `0.375 < 0.75`。因此不得标记
Stage 1 毕业，也不得进入 Stage 2。network `0.875` 和 OOD `1/1` 通过不能覆盖 route 失败。

## 正式指标

| 指标/门槛 | 结果 | 判定 |
|---|---:|---|
| route accuracy ≥0.75 | 3/8 = 0.375 | 失败 |
| network accuracy ≥0.875 | 7/8 = 0.875 | 通过 |
| OOD abstain =1/1 | 1/1 | 通过 |
| prediction/outcome pairing =8/8 | 8/8 | 通过 |
| tool-menu digest unchanged =8/8 | 8/8 | 通过 |
| cross-run mixing =0 | 0 | 通过 |
| Shadow causal events =0 | 0 | 通过 |
| all influence=false | true | 通过 |
| record digest valid | 16/16 | 通过 |
| Router prediction errors | 0 | 通过 |
| Controller exceptions | 0 | 通过 |

高置信、非弃权覆盖只有 2 条，2/2 正确；样本量不具备正式结论意义。Router 与主模型实际行为
agreement 为 1/8；预注册已规定主行为不是 ground truth，因此只报告、不用于分类 accuracy。

## 全 8 条审计

| case | expected route/net | Router route/net | abstain 主要原因 | 主行为/状态 |
|---|---|---|---|---|
| 001 | final / no | final / no | — | final / completed |
| 002 | local / no | abstain(local) / no | context conflict | local / completed |
| 003 | local / no | abstain(connector) / no | low route、phase、route/net | local / completed |
| 004 | deterministic / no | abstain(deterministic) / no | phase conflict | deterministic / completed |
| 005 | web / required | abstain(mixed) / required | low route/margin、context | web / completed |
| 006 | connector / required | abstain(deterministic) / no | context、phase | mixed / interrupted |
| 007 | mixed / required | mixed / required | — | connector / interrupted |
| 008 | abstain / no | abstain(abstain) / no | route-head abstain、context | web / completed |

所有 Router input 均由同一机械投影生成，8 条都是 fresh/无 action 的调用前状态。结果没有用于
改写标签、阈值、PCA、head、模型或输出解析。

## 根因和影响范围

阶段 0 在固定 test 上为 `0.996667`，但真实措辞 canary 只有 `0.375`，证据支持输入分布漂移，
而不是 Shadow 旁路写入或 Controller 行为改变：

- 6/8 触发 ABSTAIN；机械 context/phase facts 正确覆盖冲突 learned head；
- 4 条含 context-head 冲突，3 条含 phase-head 冲突，2 条 route confidence 低于冻结阈值；
- local、deterministic、web、connector 五类边界均出现弃权或候选误分，问题不是单用例特判；
- network 唯一错误是 connector case 006 被建议 `network_not_required`；
- 高置信非弃权只覆盖 final 和 mixed，不能外推到其他 route family。

安全回退按设计生效：所有冲突输出均为 `ABSTAIN + S_base`，没有对主模型披露 prior，也没有
改变菜单或 Network Gate。代价是当前 Router 不能承担建议模式所需的覆盖率。

## 主 Controller 的独立观测

这些行为不是 Router 标签，也没有反馈进 Router：

- case 005：`web_search` provider unavailable，主模型仍给出当前版本型 final；
- case 006：connector 首次成功后重复相同 query，后续被 egress policy 拒绝，最终因
  `identical_failure_budget_exhausted` interrupted；
- case 007：未先读取本地 `input/package.txt`，直接查询错误 package，随后重复调用并
  interrupted；
- case 008：歧义请求仍尝试三次 web，再返回澄清型 final。

它们说明 Stage 1 的差异日志有价值，但也说明“主模型实际行为”不能替代人工/机械真值。上述
问题需单独预注册修复，不能借 Shadow canary 改 Controller 或对这 8 条做特判。

## 实验封装审计

runner 生成的原始 `ARTIFACT_MANIFEST.json` 错误包含 SQLite 物理 DB/WAL/SHM。数据库关闭和
复核的 WAL checkpoint 会改变物理 hash，因而该 manifest 保留为失败证据，不覆盖、不声称
有效。`results.json` 与 Router JSONL 未发生漂移；16 条 Shadow 记录内置 digest 全部通过。

正式结果冻结后已系统修复未来 runner：它会生成按表/行排序的 `LOGICAL_STATE_MANIFEST.json`，
并从稳定 artifact manifest 排除 DB/WAL/SHM。该修复只改变实验封装，没有改变 Router、产品
Controller、数据或指标，也没有重跑本次 canary。canary 当时的 69 文件原文已保存为
`FROZEN_CODE_ARCHIVE.tar.gz`，SHA-256
`64829120e091710f103b64680175db19557cb62149a2544c051f1097ced4da6d`；当前修复后代码登记在
`POSTCANARY_CODE_MANIFEST.json`，SHA-256
`f2d0395159b28f9e2ab915cd3e6c82cea95ec1de2029dd610302e35b186074e8`。

补充审计使用 SQLite `mode=ro` 对 8 个数据库做逻辑表摘要，8/8 `integrity_check=ok`，并把
物理 SQLite 文件从稳定 artifact manifest 排除：

- `CANARY_LOGICAL_STATE_AUDIT.json` SHA-256：
  `2bfd8d5a4acd82f8052f886b467a835f02ba2f67bcda4157baa6ddbef3b52109`；
- `CANARY_STABLE_ARTIFACT_MANIFEST.json` SHA-256：
  `0d6f17e8880cc28c7f5b91924128abe772a80111354eac60d395d6948755a087`；
- stable files：33；SQLite 由逻辑审计覆盖，不再使用物理文件 hash 充当语义身份。

## 下一阶段约束

Stage 1 正式毕业仍要求至少 100 条去重、有审核标签的有机 Shadow 轨迹，并在采集前另行冻结
来源、去重、切分、人工/机械标签和评测口径。达到预注册的高置信 route、OOD 和错误未弃权
门槛前，Stage 2、菜单排序和 State Bank 均不得启用。

## 证据入口

- `PREREGISTRATION.md`：运行前冻结协议
- `FROZEN_CODE_MANIFEST.json`：69 个实现/数据/artifact 文件 hash
- `FROZEN_CODE_ARCHIVE.tar.gz`：canary 当时 69 文件原文；用于脱离 live worktree 复核
- `POSTCANARY_CODE_MANIFEST.json`：只含稳定 SQLite artifact 封装修复的当前代码
- `CANARY_LOGICAL_STATE_AUDIT.json`：8 个 SQLite 逻辑摘要和原 manifest 失败审计
- `CANARY_STABLE_ARTIFACT_MANIFEST.json`：排除物理 SQLite 后的稳定 artifact hash
- `../STATE_ROUTER_STAGE1_SHADOW_CANARY_V1_20260827/results.json`：固定指标与逐条结果
- `../STATE_ROUTER_STAGE1_SHADOW_CANARY_V1_20260827/runs/*/state_router_shadow/*.jsonl`：原始旁路记录

预 canary 全仓回归为 `356 passed in 40.13s`；聚焦回归为 `31 passed in 2.24s`；本地真实
Router smoke 为 18.0s。最终复核结果登记在 `VERIFICATION.md`。
