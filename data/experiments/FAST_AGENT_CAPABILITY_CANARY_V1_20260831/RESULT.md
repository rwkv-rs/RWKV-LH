# 快速 Agent 能力 Canary V1 结果

运行时间：2026-08-31 06:57–07:12（Asia/Shanghai）

## 结论

预注册发布门未通过：`agent_completed=0/3`、hidden external acceptance `0/3`、strict
E2E `0/3`。因此当前整体 Agent 不能称为第一正式版本；只能把当前最佳配置部署为实验预览，
供手工测试和下一轮模型残差采样。

这不是服务或强 Planner 故障。三题实际完成 242 次 13.3B RWKV generation、227 次 2.9B
Selector handoff、73 个已登记 Action 和 21 次 Supervisor 请求；Supervisor transport failure
为 0。失败点集中在真实轨迹中的 operation 选择、对应参数生成、多写根事务覆盖和完成边界。

## 固定结果

| 任务 | profile | completed | external | strict | RWKV | Supervisor | Action | protocol reject | 终止原因 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| L1 bug 修复 | G3 | 0 | 0 | 0 | 38 | 4 | 10 | 24 | `contract_graph_correction_repeated` |
| L4 个人记账网页 | G3 | 0 | 0 | 0 | 66 | 6 | 24 | 36 | `contract_graph_evidence_stagnant` |
| L5 联网资料项目 | G6 | 0 | 0 | 0 | 138 | 11 | 39 | 84 | `contract_graph_evidence_stagnant` |
| 合计 | task-level | **0/3** | **0/3** | **0/3** | **242** | **21** | **73** | **144** | — |

三个 task 的 profile switch 均为 0；离线题使用 G3，联网题使用 G6。0.4B Shadow 没有启动、
没有调用、没有进入输入或指标。

## 因果发现

### L1：小型 bug 修复仍未闭环

- investigate atom 没有选择 `read_file`，而是选择 `date_diff`、`calculator`。
- mutation atom 选择 `write_json` 写 `pricing.py`，权威工作区最终得到 JSON 对象而不是可执行
  Python；这份错误写入被完整保留，没有被 Controller 修复。
- README atom 重复选择 `file_digest` 读取不存在文件，未创建 README；没有成功执行
  `python verify_project.py`。
- Reviewer 正确判断只有 `pricing.py` 写入证据，五项义务均不足，最终 fail-closed。

### L4：中型项目没有覆盖多写根

- 三轮 mutation atom 都稳定出现 `make_directory` 后重复 `write_json`；虽然偶有
  `write_file`，但未覆盖 `index.html/styles.css/app.js/README.md`。
- exclusive/snapshot transaction 正确拒绝不完整批次，父工作区最后只保留原始
  `verify_project.py`，没有把半成品当作成功。
- Reviewer 三轮都基于 workspace manifest 和 result capsule 判定证据不足，最后以
  evidence stagnant 终止。

### L5：联网内核有效，但“检索→项目”未闭环

- 7 次 `web_search` 全部成功，分别返回 5/5/5/4/5/4/3 条 evidence；落盘 12 份
  `clean.txt` snapshot，Reviewer 明确看到了 BlinkDL 公开页面证据。
- 1 次 `connector_lookup` 的 provider unavailable 被显式记录，没有伪造成功。
- mutation atom 先越界尝试创建未声明的 `assets`，Harness 产生 ScopeViolation；随后反复
  选择 `write_json`。atom snapshot 内一度出现 `data.json`，但其余五个写根未覆盖，
  整个失败事务未合并到父工作区。
- 后续 correction 对缺失文件多次选择 `file_digest`、`search_text`、`web_search`，还把
  `date_diff` 用于文件读取目标；没有转入正确的多文件创建。
- 最终父工作区只含原始 verifier。检索证据可用，但没有 `index.html/styles.css/app.js/
  data.json/README.md/SOURCES.md`，hidden verifier 如实失败。

## 非干预与闭环验证

- 242/242 个 `model_session_generation_returned` 的外层 raw、嵌套 raw、UTF-8 byte 数和
  SHA-256 一致，且 `postprocessed=false`；完整性失败 0。
- 227/227 个 Selector handoff 都等于 eligible labels 上的原始 logit argmax，
  `postprocessed=false`；后处理或替换 0。
- 三题都没有交付空 final 之外的替代答案；Reviewer/Controller 没有补写业务文件或改写模型文本。
- P1/P2 整改的 fail-closed 行为在本轮真实暴露：不完整 snapshot 未合并、Reviewer 看见联网
  evidence 但没有据此放行、运行没有被错误标记 completed。

本轮 source manifest 在第一个模型请求前写入。运行开始后只修改了未被 benchmark 调用的
部署管理、Web UI 和文档路径；benchmark runner、Controller、Supervisor、Selector、
Executor、Harness、retrieval 与 hidden evaluator 在三题期间没有修改。由于工作树不是提交态，
本结果定位为预注册诊断 canary，而不是完整 10 题正式发布实验。

## 产品判断与下一步

1. 本地联网检索和 evidence 交接继续满足第一版“组件”定位；它不能代替 Agent 项目闭环。
2. 当前最佳可运行预览固定为 `gpt-5.4-mini + S60 zero + G3/G6`，但 UI 必须展示
   `0/3 diagnostic canary`，不能展示为正式版本。
3. 下一轮模型优化应围绕真实轨迹残差构建约 2K 的独立数据：read/investigate 与
   calculator/date 的边界、`write_file/write_json` 效果边界、缺失文件的 create/read
   边界、多写根持续推进与 `final_answer` 边界；不得把 Ladder 原题或 hidden verifier 放入训练。
4. 先用固定 zero/tuned × G3/G6 最小联动消融证明改善，再保留最少 state；不恢复 0.4B Shadow。

## 证据身份

- 预注册 SHA-256：`efe73b13f45e1df83d7d608f9151e8b3a7291af7095b8c4d1cb959a8a4ea6d51`
- `results.json` SHA-256：`7e9a22f4bff2b90912533ceb5b93cbf7a24bdff8e4d63871f5802c1c4b49faef`
- 自动报告 SHA-256：`f52407e975a045d4b0640770db741daa90bff59f2979a54d46a49e4df6a71f69`
- run protocol SHA-256：`1485caa768c81cdb7219a4ac3a13acc3eac9af5094330b19af60004702e6f34e`
- runtime doctor SHA-256：`1c892657abcb62e1d3eef3790c77022fbadcffe3438f09f5e240a555cc6a35dc`
- source manifest SHA-256：`52bcde0c608d41ffff146896e264fc36fc606273f3e3310e3319e6581b1598d1`

运行结束后，最佳 13.3B 服务仍在远端 18075，旧产品 18070 健康；本地 Selector 仍在物理
GPU0，未发现 `train.py` 进程。GPU1/2 未由本轮使用。

最终部署回归：`uv run pytest -s -q` 为 `706 passed, 1 warning`；唯一 warning 是既有
Python 3.13 多线程进程内 `fork()` 弃用提示。stack 状态确认 Selector/Web/worker 均由当前
manager 精确拥有，进程/健康拓扑中不存在 0.4B Router；Web、capabilities、runtime health、
topology 和旧 29610 服务烟测均通过。实验预览地址为 `http://127.0.0.1:8766`。

部署后的第一次真实 Web POST 暴露并修复了 Supervisor `.env` 跨命名空间污染；修复后运行
`UI-20260830-233140-0dadf4` 以 2 次精确 Selector argmax、2 次未后处理的 13.3B raw
generation 和 1 次成功 calculator action 原样交付 `4`。完整失败/修复/成功证据见
[`DEPLOYMENT_SMOKE.md`](DEPLOYMENT_SMOKE.md)。该烟测只证明部署链路闭合，不改变本报告
三题 `0/3` 的能力结论。
