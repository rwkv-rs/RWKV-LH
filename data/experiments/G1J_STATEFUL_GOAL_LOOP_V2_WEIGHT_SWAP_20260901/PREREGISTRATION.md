# G1J Stateful Goal Loop v2 weight-swap 预注册

- 登记时间：2026-09-01，早于任何 G1J 模型推理请求。
- 目的：在本轮链路整改与全仓库回归通过后，只替换 2.9B Selector 和 13.3B Executor 的基础权重，复用上一轮固定三例数据与判定，定位 G1J 权重替换后的真实链路表现。
- 架构：`rwkv-stateful-goal-loop.v2`；Strong 模型只作为必需 Planner；2.9B 只做独立 Selector；13.3B 保持唯一 Action State 并自行执行 RWKV Audit Fork。

## 固定权重

| 角色 | NAS 路径 | 字节数 | SHA-256 |
|---|---|---:|---|
| Selector base | `/mnt/nas-model/g1j/rwkv7-g1j-2.9b-20260831-ctx16384.pth` | 5,896,273,469 | `966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239` |
| Executor base | `/mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth` | 26,540,868,485 | `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65` |

权重实际位于 `rwkv-8222` 服务器 NAS；本地 WSL 没有 `/mnt/nas-model` 挂载。服务在服务器 GPU 上启动，基准命令仍只从 WSL 项目执行。

## 唯一实验变量与迁移边界

1. 相对 R3，基础权重从 G1I 替换为 G1J；case、顺序、acceptance、相似度、sampling、transition budget、Strong Planner 策略、Selector Top-K 均不变。
2. 为形成严格 weight-swap，Selector 继续使用冻结 S60 requirement-byte-tail MLP head 与 `zero` profile；Executor 继续使用冻结 G3/G6 multi-profile manifest。两者均源自 G1I，因此本轮同时检验“G1J 基座对旧控制 State/head 的迁移兼容性”，不能把失败直接归因于 G1J 裸模型能力。
3. G1J 2.9B 先通过项目登记的 value-preserving vllm-rwkv 容器转换；tensor key、shape、dtype、逻辑值与 source 必须全部通过审计。
4. 不修改或重新训练 S60 head、G3/G6 State，不改变评价阈值，不覆盖 R3/R4 原始失败。

## 固定数据与顺序

- suite：`agentladderv1`
- case：`AGENT-LADDER-L1-FIX01`、`AGENT-LADDER-L4-LEDGER01`、`AGENT-LADDER-L5-RWKV01`
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`
- acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`
- concurrency：1；max transitions：300；tool disclosure：progressive；Selector Top-K：3。

## 固定判定

- 能力门：completed/external/strict 必须同时 `3/3`。
- 架构门：每例 Strong patch ≥1；Action 必须先持久绑定 step；每个 Action Audit boundary 必须 resolved 后才能产生下一 Action；Strong review=0；Audit WKV merge=0；只有一个权威 13.3B Action State。
- 证据门：失败或范围不匹配的 Action/Artifact/Revision 不能完成 plan step。
- 观测门：summary 与 causal ledger 的 action、protocol rejection、Audit accepted/rejected/boundary 计数一致。
- 若服务、显存、挂载或协议 preflight 失败，记录为基础设施/工程失败，不计作模型质量结论。

## 整改前固定对照

- R3：strict `0/3`；Actions `1/11/4`；Audit accepted `0/16`。
- R4 L4：strict `0/1`；Audit accepted `0/3`；最早可证实失败为 Selector 未收到 active Strong frontier，随后 Audit 输出协议失败且失败边界未持久化。

## State Tuning 启动门

本轮不启动训练。只有运行后仍存在可重复的模型输出错误，且错误发生在已修复工程边界之后，才进入 failure→verified correction 收集。当前 v2 correction corpus 仅 `3/2480`，`quota_reached=false`，不能用于正式 tuning。
