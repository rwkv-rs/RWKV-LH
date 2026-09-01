# Zero-State 工程解锁附录

登记时间：2026-09-01，在固定真实任务的首次 RWKV/Planner 调用之前。评价数据、参数、阈值和顺序不变。

## 原始 product gate

按当前 `.env.local` 运行 `AGENT-LADDER-L1-FIX01` preflight，在创建运行目录和任何模型调用之前失败：

```text
RuntimeError: RWKV endpoint is unavailable: RWKVTransportError: ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))
```

实际配置对象是 `RWKV_BASE_URL=http://127.0.0.1:29613/v1`，并且 `.env.local` 仍是 G1I Executor + G1I S60/v7 Selector，而不是预注册要求的 G1J + v8。此项归类为 deployment/configuration 失败，不产生模型质量结论。

## 零 State 服务首次失败

G1J 2.9B Selector 权重完成加载后，最早失败记录为：

```text
rwkv_lh/inference/vllm_rwkv_state_profiles_v1.py:115
ValueError: RWKV7 state-profile model artifact mismatch
```

具体错误对象是启动 CLI 强制传入的 G1I `profiles.json.model_artifact`，它与 G1J 2.9B artifact 不同。Executor 的 vLLM native-state loader 也在同一字段上 fail closed。这证明失败发生在 State manifest 身份验证，早于 Selector/Executor 模型输出。

## 最小修复

`network_service.py` 现在允许不传 State manifest，但仅在三个 identity 字段精确为以下值时放行：

- `profile_manifest_sha256 = 00...00`
- `profile_id = zero`
- `profile_sha256 = 00...00`

任一字段非零仍 fail closed。Executor 引擎已有同等 `manifest_path is None -> zero_only()` 语义，启动时只需不注入 G1I manifest，不改引擎代码。

回归：`24 passed in 2.05s`。

## 修复后源码身份

- tracked diff SHA-256: `43f3630dfb0f7e448462d2976387635743fb6966e7f08bfc0b7979e11228b7e0`
- `rwkv_lh/` Python/Web 源码列表聚合 SHA-256: `8997e0d143a6a27a7a97ff4f2c244371fa080b7d0c3e4b7d6071584d15027fba`
- `network_service.py` SHA-256: `8fa8e0c307bca88d1de2e3d39bcf730af6d6c0bb3109bc69806dde37a56f583c`
- 运行脚本 SHA-256: `4bde9ed73bdfd4f21dd43b426c03bd063d53b78c4c294889a9b835b84fc5b4fc`

后续运行名中的 `v7_compatibility` 是强制标记：它用 G1J zero-State S60/v7 Head 排除其他链路失败，但不代表缺少匹配 Head 的 v8 最新产品已通过。
