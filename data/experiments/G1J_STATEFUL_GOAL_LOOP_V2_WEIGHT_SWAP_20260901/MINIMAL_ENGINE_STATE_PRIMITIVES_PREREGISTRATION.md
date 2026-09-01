# vllm-rwkv 最小 State 原语与并发验证预注册

- 登记时间：2026-09-01，早于最小 State 原语实现和 G1J 13.3B 推理。
- 目标：让一次请求结束后的 RWKV recurrent State 能被下一次请求恢复，同时不占用活跃调度槽；引擎不实现 Goal、lineage、commit、rollback 或事实账本。

## 固定接口

- 请求读取：`vllm_xargs.rwkv_state_read_ref`
- 请求写入：`vllm_xargs.rwkv_state_write_ref`
- 管理原语：`inspect`、`clone`、`drop`、`capabilities`
- State cache：进程内 GPU 快照；容量按字节硬限制；容量不足失败，不静默驱逐。
- 持久性：明确声明 `process_local=true`、`durable=false`；不得伪装为可跨重启 State。

## 固定正确性数据与指标

- 数据集：`data/datasets/vllm_rwkv_direct_state_continuation_parity_v1`
- cases SHA-256：`2bea618ac9d4ce73a324628c5c3485f5a3b07c6b30324ae458c355bfc2356c60`
- 五个固定 token 序列；不采样。
- 一段式前向与 capture→restore 分段前向的逐 token logits：`max_abs_error <= 5e-4`、`cosine_similarity >= 0.999999`。
- clone 后原 ref 和 clone ref 分别继续相同 delta，必须满足同一阈值。
- drop 后读取必须确定性返回 not-found。

## 固定并发与性能门

- 并发：`1, 8, 32, 64`；固定输入/输出 token 数和 sampling。
- 对照：同一引擎、同一权重、同一参数下 zero-State 普通请求。
- State 快照不得占用 scheduler request slot；缓存 `N` 个 ref 后仍能接收配置的 `max_num_seqs` 活跃请求。
- restore+capture 的 p50 额外延迟不高于对照单次请求延迟的 `5%`，p95 不高于 `10%`。
- 并发 64 的吞吐下降不高于 `5%`；GPU State cache 实际字节数必须等于服务报告值且不超过配置硬上限。

## 失败分类

- State 原语、身份、容量、HTTP 或调度失败：工程问题。
- OOM、GPU 不可用、服务退出：基础设施问题。
- 只有上述门通过后，固定 Goal 数据中的语义选择、参数、审计或汇报错误才属于模型能力候选。
