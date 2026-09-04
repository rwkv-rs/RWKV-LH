# RWKV Runtime Stack v1 结果

结论：部署和端到端连接通过；State Router 分类毕业仍未通过，继续停留在 Shadow。

## 部署结果

- 项目内成功从固定 commit 构建 `rwkv` reduced profile；
- native targets 仅 `_rapid_sampling`、`cumem_allocator`、`rwkv7_ops`；
- `unrestricted=false`，TP/PP/DP 均固定为 1；
- Torch 固定为 `2.11.0+cu128`，NumPy 固定为 `2.2.6`；
- 冷启动约 10.23 秒；
- 二次 `prepare` 返回 `reused=true`，约 1.5 秒；
- `rwkv-lh-stack deploy` 已真实执行，主模型和 Router 健康检查同时通过；
- 已存在的 SSH 转发和远端 Stage1 GPU0 unit 均只采用，没有被接管或重启。

首次诊断构建解析到了 Torch cu130。portable identity 按设计拒绝启动，没有把不同 CUDA/Torch
运行时冒充成冻结实验。安装器随后增加 cu128 发行物锁，并重新构建验证。

## 数值等价

正式结果见 `PERSISTENT_ROUTER_EQUIVALENCE.json`：

| 指标 | 结果 | 门槛 |
|---|---:|---:|
| 固定 test | 300 | 300 |
| 离散输出不一致 | 0 | 0 |
| 最大 confidence 绝对差 | 0.0283512 | ≤0.05 |
| 批量吞吐 | 83.61 rows/s | 只报告 |

所有 context、phase、route、network、state profile、abstain、原因、model hash 和 head hash
均与阶段 0 冻结结果一致。

## 端到端

真实链路：

```text
Controller
  -> persistent Router HTTP（60.15ms，deterministic）
  -> 13.3B Stage1 endpoint
  -> calculator(19*29)
  -> final_answer("19*29=551")
```

run `LH-c626b8a873b94699` 完成，revision 13，主模型请求 4 次；工具菜单前后摘要一致，Shadow
全部 influence 字段为 false。结构化记录见 `END_TO_END.json`。

Web 模式也完成实际启动验证：`/`、`/api/capabilities`、`/api/runtime/health` 均返回 200；验证
后只停止 manager-owned Web 进程，Router 和远端主模型保持运行。

## 工程回归

- `uv run pytest -q -s`：362 passed；
- 最终定向回归：20 passed；
- `uv lock --check`：通过；
- `git diff --check`：通过。

## 未通过项

- 阶段 1 固定真实 canary 仍是 route `3/8`；
- 尚无至少 100 条人工/机械审核的有机 Shadow 数据；
- 尚未进入建议模式、菜单排序或 State Profile 注入；
- 13.3B `.pth` 主服务尚未迁入 reduced engine；
- 主端尚无 durable recurrent-state `/capabilities`；
- vLLM 尚无 per-request State Profile 调度和 state bank。

因此本轮只能宣布“运行栈可部署、数值等价、端到端连接通过”，不能宣布“主动式路由达到正式
实验标准”。
