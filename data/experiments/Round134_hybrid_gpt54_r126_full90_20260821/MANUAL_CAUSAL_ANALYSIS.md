# Round134 GPT-5.4 Supervisor + R126 spine Full90 — 终局因果分析

日期：2026-08-22  
协议：`../Round134_HYBRID_GPT54_R126_SPINE_FULL90_PROTOCOL.md`  
结果：`results.json` / `REPORT.md` / `RUN_PROTOCOL.json`  
最终判定：**仅 REJECT“一次静态 Plan + 终局 Final Review”变体；该轮没有测试在线微任务 Planner/Reviewer，不替换 R126 canonical baseline。**

## 1. 结论

固定 RWKV-E2E-90 已完成 90/90、0 running；runner 因 73 个 Strict 失败按约定 exit 2，
不是基础设施中断。最终：

| 指标 | Round134 | 预注册目标 | 结果 |
|---|---:|---:|---:|
| Strict / TP | **17/90** | >36 | FAIL |
| FP | **5** | <=24 | 数值 PASS，但来自 completion collapse，不能视为安全改进 |
| FN | **10** | <=1 | FAIL |
| OTHER | **58** | — | 严重退化 |
| Agent completed | **22** | — | R132 的 64 降至 22 |
| External passed | **27** | — | R132 的 34 降至 27 |
| byte-precision | External **4/5**；Strict **2/5** | 5/5 | FAIL |
| 有效性 | 90/90；0 running | 90/90；0 running | PASS |

GPT-5.4 的一次静态 Planner 能描述正确步骤，但不能改变 RWKV 在 Final 之前的局部
`state -> next action` 吸引子；只在 RWKV 主动提交 Final 后才触发的 Reviewer 又引入双向错误。
因此本轮只否定这个静态变体，**不能外推否定**“GPT-5.4 在线验收每个小工作、再布置下一个
微任务”的方案；后者必须作为独立架构重新预注册和测试。

## 2. 固定配置与审计有效性

- Worker：`rwkv7-g1i-13.3b-20260805-ctx16384`，prompt replay，temperature 0.05，
  max-transitions 200，concurrency 1，full tool disclosure。
- Supervisor：OpenAI-compatible `gpt-5.4`，temperature 0.1；每题一次 plan、每个 RWKV
  Final 一次 review、最多一次返修；无 action 权限、不可见 hidden acceptance、不可改写 Final。
- 运行时间：2026-08-21 15:13:16Z 至 20:35:09Z，约 5h21m53s；systemd 记录 CPU
  51m02s、MemoryPeak 20.7 GiB、swap peak 0。
- 90/90 audit 使用 bubblewrap isolated verifier；90/90 agent process tree 在评分前关闭；
  hidden acceptance 路径均未进入模型 trace。
- 22 个 Agent completed 的 delivered Final 与 RWKV 原始 `final_answer.text` 全部字节一致；
  Supervisor action record 为 0；顶层协议、结果和全部 audit 未发现 credential pattern。
- 全回归：`TMPDIR=/home/chase/GitHub/RWKV-LH/temp .venv/bin/pytest -q` -> **123 passed**。

因此结果有效，退化不能归因于 transport、网络、Verifier 泄漏、Final 改写或 OOM。

## 3. 固定口径分布

| Group | TP | FP | FN | OTHER | Completed | External | RWKV requests | Actions | Rejects |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Basic 30 | 10 | 2 | 8 | 10 | 12 | 18 | 474 | 357 | 71 |
| Medium 30 | 6 | 3 | 2 | 19 | 9 | 8 | 1,615 | 1,491 | 79 |
| Hard 18 | 1 | 0 | 0 | 17 | 1 | 1 | 1,368 | 1,233 | 109 |
| Long-horizon 12 | 0 | 0 | 0 | 12 | 0 | 0 | 1,479 | 1,360 | 103 |
| **Total** | **17** | **5** | **10** | **58** | **22** | **27** | **4,936** | **4,441** | **362** |

Strict passes：B01/B03/B07/B09/B17/B18/B21/B26/B28/B30，M03/M12/M13/M20/M27/M30，
H04。Long-horizon 0/12，且 12/12 interrupted。

Byte cases：B01 TP、B06 FN、B13 OTHER、B19 FN、B28 TP。B19 的 artifact 通过两个
hidden checks，但 Reviewer 连续两次要求 Harness 已提供的实际字节 SHA256 之外再做一次“独立
再哈希”，造成直接假阴性。

## 4. 相对 R126 / R132

| 指标 | R126 official | R132 canonical | Round134 | vs R126 | vs R132 |
|---|---:|---:|---:|---:|---:|
| TP | 36 | 34 | **17** | -19 | -17 |
| FP | 30 | 30 | **5** | -25 | -25 |
| FN | 0 | 0 | **10** | +10 | +10 |
| OTHER | 24 | 26 | **58** | +34 | +32 |
| Completed | 66 | 64 | **22** | -44 | -42 |
| External | 36 | 34 | **27** | -9 | -7 |
| RWKV requests | 未保留原始聚合 | 3,504 | **4,936** | — | +1,432 |
| Actions | 未保留原始聚合 | 3,171 | **4,441** | — | +1,270 |
| Protocol rejects | 未保留原始聚合 | 235 | **362** | — | +127 |

分组 Strict：R126 为 B23/M10/H2/LH1；R132 为 B23/M8/H2/LH1；Round134 为
B10/M6/H1/LH0。FP 下降不是正确率改进，而是大量完成态转成 FN/OTHER。

R132 -> Round134 全量 churn：

```text
                 Round134 TP   FP   FN   OTHER
R132 TP (34)              14    2    8      10
R132 FP (30)               3    3    1      23
R132 OTHER (26)            0    0    1      25
```

R132 TP 仅保留 14/34。Round134 同时引入 plan 和 review，故不能把全部 churn 单独归因给
某一组件；但 Reviewer 记录允许对其直接错误做独立归因。

Round133 progressive B01 canary 首轮 13 requests / 0 actions / 12 rejects / External fail；
r2 为 17 requests / 2 actions / 12 rejects / External pass，但没有完成，因此按协议跳过
progressive Full90。Round134 回到 R126 full-schema spine 后，B01 canary 以 5 RWKV requests /
3 actions / 1 reject Strict PASS，正式 Full90 的 B01 也以 4 requests / 3 actions / 0 rejects
Strict PASS。这证明 full-schema 恢复了接口可达性，但 Full90 的 17/90 证明单题 canary 不能
代表后续 state-transition 质量。

## 5. GPT-5.4 Planner / Reviewer 的直接证据

### 成本与可用性

- 165 次调用全部一次 HTTP attempt 成功：plan 90、review 75；无 transport failure。
- Supervisor token：plan 112,575；review 370,952；合计 **483,527**。Review 占 76.7%。
- plan 平均 11.34s、review 平均 7.21s；串行累计约 26.0 分钟。
- 43 题没有到达 review，20 题一次 review，27 题两次 review。
- 记录了 74 个 review verdict：pass 22、revise 52。M26 的一次 review 已返回，但在统一
  transition 边界后未提交 verdict。

### Reviewer 与 isolated verifier 的判定矩阵

| 最后 Reviewer verdict | External pass | External fail |
|---|---:|---:|
| pass | 17 | **5 false accepts** |
| revise | **4 false rejects** | 21 |

False accepts：B14、B23、M04、M08、M18。False rejects：B02、B08、B19、M11。
另外 6 个 external-pass case 在 review 前即因流程/预算中断：B04、B06、B15、B20、B27、M05。
这 4+6 恰好构成全部 10 个 FN。

27 个二次 review 中，19 个是 `revise -> revise`；其中 3 个 artifact 实际 External pass。
只有 8 个变成 `revise -> pass`，其中 5 个 External pass、3 个仍 External fail。一次在线返修
没有形成可靠纠错器，反而把错误 Final 放行并把正确产物挡住。

结论只适用于 Round134 的终局硬门：它可作为离线 teacher/critic 生成候选理由，但不能单独作为
训练真值；训练标签仍必须最终由 frozen isolated verifier 和可复核的 workspace delta 决定。
逐动作在线 Planner/Reviewer 是否能改变 RWKV 状态转移，Round134 没有提供证据，留待 Round135。

## 6. RWKV 状态转移根因

全量 4,441 个 action 中：

- 仅 **159** 次改变 workspace；4,282 次（**96.42%**）没有 workspace 进展。
- 题内重复 action fingerprint 共 **3,812** 次（**85.84%**）。
- 共发生 **777** 次 action-session rollover；吸引子在 rollover 后继续，故不是单纯上下文长度。
- 18 题超过 100 actions；11 题贴近统一预算。
- 动作分布：read_file 2,326、list_directory 589、read_json 522、write_json 391、
  check_command 377、write_file 185，其余 51。
- 19 题从始至终 workspace change 为 0。

四类系统性失败：

1. **首次落盘前的观察吸引子。** H17 共 201 actions，其中 200 次同 fingerprint read_file、
   0 workspace change、27 rollovers；LH11 共 176 actions，167 次 list_directory、最长连续
   同 fingerprint 164、0 change；H02 共 189 actions、0 change。
2. **写入后的验证吸引子。** M05 artifact 已 External pass，却在 199 actions 中执行
   check_command 163 次，最终 FN；M11 artifact External pass，但 130 actions 中 read_json
   95 次，最终 FN；B24/M14 则在错误 artifact 后重复 read/check 直到中断。
3. **重复 side effect 覆盖。** M21 共 199 actions，write_json 153 次，但仅 3 次 workspace
   digest 真正变化；这类循环可能把一度正确的产物再次覆盖坏，风险高于纯读循环。
4. **短周期而非仅连续复读。** M07 的重复 fingerprint 比例 95.98%，但最长连续相同仅 1，
   说明它在多个动作间交替成环。只加“连续重复一次就阻止”的 guard 不能修复根因。

静态 plan 在开头正确描述任务，却不参与每次 observation 后的决策；review 又只有 RWKV
先发出 Final 才触发，因此两者都不能修复 Final 前的状态吸引子。

## 7. 下一步最小训练方向（本轮未生成数据）

当前 trace 可以作为种子，但不能把原始失败输出直接当正样本。建议下一阶段按固定 E2E90 口径：

1. **State-transition SFT**：样本单位用“可见状态 + 最近 observation + workspace delta +
   未完成义务 -> 唯一下一 action/Final”，优先保留 17 个 TP 与 R126/R132 TP 的真实正转移。
2. **对比/DPO hard negatives**：rejected 直接取本轮相同 fingerprint、无信息增益 read/check、
   以及无 digest 变化的重复 write；chosen 由 frozen verifier 可验证的下一进展动作产生。
3. **Completion absorbing state**：重点配对 M05/M11/B19 等“artifact 已正确但不完成”和
   B01/M13/M30 等“验证后正确 Final”，训练 evidence-sufficient -> Final。
4. **多对象进度状态**：显式监督 processed set / next item / remaining obligations，解决
   M01/M11/H12/LH11 在多个文件间丢失进度的问题。
5. **工具族与副作用约束**：训练 artifact type -> 合法下一工具族；对无 workspace delta 的
   side-effect repeat 赋最高负权重，但不惩罚一次合法验证。
6. GPT-5.4 可以继续测试为在线微任务 planner/critic，但其 verdict 不直接成为训练标签；chosen
   仍必须经 isolated verifier 与 workspace delta 复核。

先做小 LoRA/state-tuning canary，再用固定 Basic30、Medium30、Hard18、LH12 分层复验；不得
因为训练结果修改阈值、相似度算法或 hidden verifier。

## 8. 独立的持久化架构缺陷

Round134 目录约 18 GiB；90 个 SQLite DB 合计 17,483,927,552 bytes，15 个 >=500 MB、
4 个 >=1 GB，最大 LH11 为 1.72 GB。全部 audit 合计 686.6 MB，causal ledger 合计 407.6 MB。

证据表明 checkpoint 每个 revision 都保存完整且不断扩大的 `state_json`：

| Case | Checkpoints | avg state_json | max state_json | state_json 累计 | DB |
|---|---:|---:|---:|---:|---:|
| H17 | 846 | 1.08 MB | 2.16 MB | 917 MB | 924 MB |
| LH11 | 916 | 1.87 MB | 3.75 MB | 1.71 GB | 1.72 GB |
| M21 | 825 | 1.06 MB | 2.09 MB | 878 MB | 885 MB |

这是随 revision 和 state 同时增长的近二次存储放大。它没有造成这轮 OOM，因此不是质量失败
的原因，但会妨碍后续大规模数据生成。根修复应为 event/delta persistence + 有界周期 full
snapshot，并流式生成 audit/ledger；不能通过删 audit 或缩短失败 case 来掩盖。

## 9. 最终处置

- 不保留 Round134 静态 Plan + 终局 Review 变体为新 baseline；R126 canonical 仍是训练前基线。
- 保留 supervisor adapter 为 default-off 实验能力；Round135 另测逐动作在线微任务指导，GPT
  仍不得执行 action、生成业务产物或改写 RWKV Final。
- 本轮只完成本地 Full90、审计和分析；**未生成、扩增或训练任何数据**。
- 下一阶段先修持久化放大，再从本轮 TP/FN/loop trace 构造可验证的 state-tuning seed。
