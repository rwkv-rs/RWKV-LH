# Round19 预注册：Model-Written Target Provenance Independence

预注册日期：2026-08-13（任何 Round19 RWKV 请求之前）

## 固定依据

Round18 的渐进披露把 witness selection 编译从 Round17 的 `4/39` 提高到 `22/34`，proof/evidence
从 `1/90` 提高到 `6/90`，并首次出现 1 个 internally completed case。但正式成绩退化为 External
`17/90`、Completed `1/90`、Strict `0/90`、FP `1`，不能上传。

score-independent provenance 分析在加载 hidden acceptance/reference 之前确认：

- 250 次 mode 请求产生 160 次合法提交；Runtime 选择 mode 的事件为 0；
- 260 次 binding 请求中 64 次合法；binding prompt 的跨分支字段披露违规为 0；
- 6 题共有 13 条 proof-pass assertion；13/13 都把当前 workspace target/action output 与同一路径的
  dependency snapshot 做 exact equality；
- 唯一 internally completed 的 E2E-B17 先在 T2 根据可见 users.json 正确写出 Ada/Zoe、count 2，
  T3/T5 又覆盖为 Alice/Bob/Charlie、count 3；T7/T11/T12/T13/T14 随后把当前
  active_users.json 与 T3/T5 写入该同一路径时形成的 artifact 比较，五条自一致 proof 覆盖 GC1-GC4，
  obligation 因此清零。

标准答案随后确认 B17 是 FP；raw final 与 delivered final 完全相同，系统没有修改 RWKV final。

冻结依据：Round18 results SHA-256
`ad96b14e3872552dda192d2018719af866334a57ee428070489ff3bb9e2a7693`；progressive analysis
SHA-256 `50237cb254ee843b8206d44b98e388f1b35167b722311528c57d3745c848d866`；completion-lineage
analysis SHA-256 `bb4d854de0e7ee00bf5aa77da65f26f7b3afc378b095cc03f2ccf4986c274e1a`。

## 唯一结构变量

实施 `model_written_target_provenance_independence.v1`：

1. 保留 Round18 的 RWKV mode commitment、分支 binding、source/handle 选择和 exact proof 流程。
2. Proof Engine 在已有 opaque source-ID overlap 检查之后，增加语义 provenance overlap：
   - 从 actual evidence ref 及当前 action 的 scoped target path 得到 actual workspace target；
   - 对 expected dependency artifact/memory，解析其 owner task；只有 owner action 是
     `write_file/write_json/append_file/copy_file` 且其 mutation target 与 artifact/actual target 相同，
     才标记为 model-written same-target lineage；
   - actual 与 expected 命中该 lineage 时，proof fail closed。
3. 由 read-only dependency 捕获的同路径 snapshot 不按本规则拒绝；不同路径的 model-written dependency
   也不按本规则拒绝。这样不把“同路径”本身当作错误，只排除模型输出给自己充当期望值。

该规则只判断证据独立性，不判断值正确与否，不替 RWKV 选择 mode/source/handle，不读取 criterion 文本、
hidden acceptance/reference，也不修改 action 或 final。RWKV 的原始选择仍完整审计；被拒绝后走现有本地
binding revision/recovery。

## 不作弊边界

- 不根据数值相等、标准答案、external 结果或案例 ID 判定 lineage；只使用 action type、scoped path、
  artifact/memory owner 和 immutable audit provenance。
- 不删除 RWKV 字段、不替换 source、不自动改成 Goal literal；不对 B17 或文件名特判。
- 不禁止真正独立的 Goal literal、只读输入 snapshot 或不同目标 artifact。
- proof 拒绝不会把答案改为正确，只会阻止错误证据触发 completion。
- hidden acceptance/reference 继续只在 90 题全部终止后加载。

## 明确不改

- Round18 progressive protocol、prompt、sampling、mode/binding retry 次数不改。
- Goal、plan、priority、action/G1i、recovery、obligation、任务预算、重复任务、catalog 内容、handle
  binding、completion、数据、verifier、相似度算法不改。

## 固定验证

- 新增三类 proof regression：model-write same-target 拒绝；read-only same-target snapshot 保留；
  model-write different-target 保留。
- 全产品 pytest、LH-Control-30、E2E catalog validation 前后全过。
- RWKV-E2E-90，Basic/Medium/Hard 各 30；同一模型/endpoint，并发 8、max transitions 200，sampling 不变。
- 先做 score-independent backward/provenance 分析，再加载 standard answer/hidden acceptance。

### 运行前窄化复核

实现后、任何 Round19 RWKV 请求之前，用冻结的 13 条 Round18 proof-pass assertion 做离线重放。结果为：

- 8 条被本轮窄规则明确判为 model-written same-target lineage：B17 5 条、B25 2 条、H09 1 条；
- 4 条来自非写入 owner，仍通过，证明实现没有把所有同路径 snapshot 一律禁止；
- 1 条因正式运行结束后的 workspace artifact hash 已变化而由既有 hash 规则拒绝，不能用重放判断其
  原运行时 provenance。

该重放不调用模型、不读取 hidden acceptance/reference、不改变 Round18 分数或状态。它修正了最初把
13 条都口头称为“model-written”的过宽分类；本轮变量始终只针对可由 owner mutation action 证明的 8 条。

## 预注册门与 GitHub 晋级门

- Round18 可确认的 8 条 same-target model-write proof 必须归零；任何新 proof-pass 都必须具独立 provenance。
- FP 必须恢复为 0；selection 编译不低于 `22/34` 的结构水平，proof/evidence 单独报告，不以更多为目标。
- 只有 FP=0、Strict >7、Completed >7、External 不低于历史最佳 24、pytest/LH-Control/完整审计全过，
  才允许提交推送。否则保存 Round19 并标记 `do_not_upload`；远端保持 Round2 checkpoint
  `b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
