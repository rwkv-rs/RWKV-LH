# Harness Causal Closure P1/P2 V1 — 结果

日期：2026-08-30（Asia/Shanghai）

## 结论

预注册的 7 类工程闭环门全部通过。该结论修复并取代“整条 Harness 已完全闭合”的旧判断缺口，但不改变
此前 E1 两例 scheduler canary 的窄结论：那两例没有进入 finalizer、联网、`run_command`、崩溃恢复或
State Router 路径。

## 固定矩阵结果

| 缺陷 | 结果 | 可复核证据 |
|---|---|---|
| P1 finalizer 证据 | PASS | 初始 finalizer 依赖全部初始 work；correction 后旧 finalizer 不 ready；replacement 覆盖全部 completed work |
| P1 最终呈现 | PASS | contradicted exact Final 后无 `run_completed`；replacement 通过独立 presentation review 后才完成 |
| P1 出站来源 | PASS | 单文件/总预算、跳过目录、遍历/读取不完整均为 `unknown`，`auto_public` 拒绝 |
| P1 exclusive | PASS | exclusive 始终在隔离快照运行；非零退出写入没有进入父 workspace；成功才全快照事务提交 |
| P2 pending | PASS | 每个恢复成功的 pending 有 `supervisor_call_resolved`；提交/resolve 间崩溃可重放恢复；旧 pending 不触发后续重试 |
| P2 action 半提交 | PASS | 注入只有 start 的状态后恢复为严格 1 start / 1 return，重复投影为 no-op |
| P2 Shadow | PASS | child web action 进入 Router continuation 摘要和 observed route；policy rejection 计数正确，不误标 `FINAL` |

## 全量验证

- 相关回归：`177 passed in 28.74s`。
- 全项目：`uv run pytest -s -q` → `684 passed, 1 warning in 149.12s`。
- 唯一 warning：Python 3.13 在多线程进程内 `fork()` 的既有弃用提示；与本轮链路整改无关。
- `git diff --check`：通过。
- 产品连续性：`127.0.0.1:29610/v1/models` 返回 HTTP `401`；隧道/服务可达且鉴权门生效，未停止或替换产品进程。
- 本轮没有启动模型服务、没有占用 GPU、没有训练 state，也没有修改任何 RWKV raw output。

## 架构影响

1. Finalizer 不再依赖“当前 workspace 足够”这一假设；所有已完成 child result（包括不落工作区的联网证据）
   都通过明确依赖交接。
2. `EXECUTION_EVIDENCE` 和 `FINAL_PRESENTATION` 变成两个独立门；强 Reviewer 只能给 verdict，不能改写 Final。
3. 出站来源从二值“命中/未命中”变成三态；任何扫描不完整都是 `unknown` 并 fail-closed。
4. exclusive 的“调度独占”与“写入事务隔离”同时成立；失败 atom 不再污染权威 workspace。
5. 父 ledger、主动调度和 Shadow 统一折叠 child/恢复事件，不再从不同局部状态推导互相矛盾的结论。

## 后续边界

这轮完成的是工程因果闭环，不代表模型能力或检索答案质量已经提高。恢复完整 E1/E2 消融时仍须使用冻结数据、
固定阈值和原评价算法；只有消融证明剩余误差属于模型残差后，才进入最小 state tuning。
