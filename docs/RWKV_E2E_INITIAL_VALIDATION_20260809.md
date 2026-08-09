# RWKV-E2E 初版验证记录（2026-08-09）

## 验证边界

这次验证没有向 RWKV 提供答案、Task Graph、动作序列、completion criteria、replan 路径或隐藏验收条件。模型只获得用户目标、隔离 workspace、通用约束和 Harness 能力。

运行环境：

- Endpoint：`http://127.0.0.1:29613/v1`
- Model：`rwkv7-g1i-13.3b-20260805-ctx16384`
- Runner：`rwkv-lh-e2e`
- 详细本地报告：`outputs/rwkv_e2e_basic_repair_v2/REPORT.md`（生成文件，不进入 Git）

## 结果

- Python tests：50/50 通过
- LH-Control-30 Architecture Regression：30/30 通过
- 选定的真实 RWKV E2E 基础题：0/8 严格通过
- 独立隐藏验收通过：4/8

| Task | Agent 状态 | 隐藏外部验收 | 主要失败 |
| --- | --- | --- | --- |
| E2E-B02 | interrupted | PASS | 正确 JSON 被语义交叉验证误拒，随后 replan 生成 replacement cycle |
| E2E-B03 | interrupted | PASS | 正确修改完成后 verifier 协议输出不完整 |
| E2E-B05 | interrupted | FAIL | 删除任务未稳定完成，replan 重用了已有 task id |
| E2E-B06 | interrupted | FAIL | 合并任务未完成，replacement 依赖形成有效自环 |
| E2E-B07 | interrupted | PASS | 正确 endpoint 已生成，但 cross-validation 输出无限扩展并截断为不完整 JSON |
| E2E-B08 | interrupted | PASS | 正确 manifest 已生成，随后推理 endpoint 暂时拒绝连接 |
| E2E-B09 | not_created | FAIL | Goal 请求时 endpoint 拒绝连接 |
| E2E-B10 | not_created | FAIL | Goal 请求时 endpoint 拒绝连接 |

## 判定

当前版本证明了 Controller、SQLite 状态、恢复、scope、Harness、deterministic verifier、request-level temperature 和审计边界可以作为架构基础；它没有证明 RWKV 已经能稳定完成真实长程任务。

尤其不能用 `LH-Control-30 = 30/30` 表示 RWKV 智能成功率。真实 E2E 暴露的主要问题是：

1. 语义交叉验证存在明显 false negative，会拒绝已经通过独立验收的产物。
2. RWKV 的结构化协议可能在低温下继续生成无关字段，最终耗尽输出预算。
3. replan 仍会提出复用 task id 或 replacement-induced cycle。
4. 推理服务的短暂不可用会中断未完成 run，虽然持久化状态仍可供恢复。

因此本版本按“本地实验初版”封存，不标记为生产可用，也不上传 Long-Horizon 代码。
