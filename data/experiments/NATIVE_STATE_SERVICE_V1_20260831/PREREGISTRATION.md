# 13.3B native-state serving v1 预注册

## 固定目标

验证本地 `vllm-rwkv` 推理引擎与实际 13.3B 服务共同实现
`rwkv-lh.native-state.v1`，而不是仅由 RWKV-LH 客户端声明支持。现有 18075 服务在本轮验证完成前
不切换；先在独立 GPU/端口验收，再部署到原服务入口。

## 固定对象

- 引擎源码：`/home/chase/GitHub/vllm-rwkv` 当前工作树中的 native-state 实现；部署副本必须以
  现网 deterministic-cmix-r7 源码为底座并只覆盖已验证的 state 相关文件。
- 模型：13.3B `rwkv7-g1i-13.3b-20260805-ctx16384.pth`。
- served model：先验收隔离名称，最终以 `/v1/models` 与 `/v1/capabilities` 的同一 identity 为准。
- state profile：`EXE-G3-MULTISTAGE-STEP2000`，SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`。
- 固定数据：`data/datasets/rwkv_lh_native_state_service_v1/cases.json`；运行前记录 SHA-256。
- 真实项目母路径：当前 RWKV-LH 源码快照的独立副本，副本目录本身直接作为
  `Goal.workspace_root`，沿用已冻结的 14 个 Action 与 23 个 exact-position checks；live 模型测试
  另行保存原始输出，不能用协议夹具替代。

## 固定调用与参数

1. 能力探针：`/v1/models`、`/v1/capabilities`。
2. 数值等价：每个 case 的 segment 分别经 `/tokenize` 取得 token id；reference 把这些 segment
   token id 按顺序拼接后一次性输入 `/v1/completions`，native 路径按 segment 调用 create 后 append
   或 fork，再 generate。这样评价的是相同 token 序列，不受跨 segment 重新分词影响。
3. sampling 固定为 `temperature=0`、`top_p=1`、`top_k=1`、presence/frequency penalty `0`、
   penalty decay `0.996`、seed `0`、`max_tokens=8`、无 stop。
4. lifecycle：create、append、fork、generate、rollback、commit、显式 import；再创建超过 worker
   cache capacity 的 state，验证被逐出的首个 state 能从非权威 export cache 恢复。
5. 负例：错误 model、错误 cache binding/lineage 必须 fail closed，HTTP 为 4xx。
6. 最终部署后，在原本地入口 `127.0.0.1:29613` 重复 capability、完整 lifecycle 和真实项目测试。

## 固定指标与阈值

- `capability_exact_accuracy=1.0`：protocol、七个 lifecycle flag、`prompt_replay=false`、
  `authoritative=false`、`cache_role=disposable_acceleration`、pending-token policy 全部逐项相等。
- `continuation_token_exact_accuracy=1.0`：4 个 case 的 reference 与 native 原始输出 token id 逐 case
  完全相等；文本仅记录，不参与修复。
- `lifecycle_exact_accuracy=1.0`：commit、rollback、fork、import、eviction restore、parent/binding 拒绝
  全部逐项通过。
- 真实项目固定协议验收仍要求 `23/23`；live 模型运行只按预先定义的项目验收条件计分，不因输出
  临时修改 verifier。
- 任一 hard gate 失败则不切换 18075，也不在当前文档写“服务已上线”。运行后不改阈值、case、
  token 拼接算法或判定口径。

## 解释边界

该实验可以证明 serving 层真实维护 RWKV recurrent tensor state，并证明 state+delta 与一次性同 token
序列的 continuation 等价；不能把它解释为模型已具备完整项目 Agent 能力。WKV export 与内存 cache
始终是可丢弃加速，不是 Goal、Action、Result 或 Final 的 authority。
