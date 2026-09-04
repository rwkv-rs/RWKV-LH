# Round77 short7 manual causal analysis

## Frozen result

- Strict `0/7`; External `2/7`; Agent completed `3/7`; FP `3`; FN `2`.
- B01 and B02 produced the externally correct workspace but were blocked by the Goal-frontier protocol.
- B10, M03 and M06 were reported complete without the requested workspace mutation.
- The preregistered gate failed. No fixed15 or full90 run was started and this architecture must not be uploaded.

The conclusions below were obtained by reading each Task transition, action observation, protocol error, Goal-frontier decision and external verifier result in order. The aggregate report was used only to freeze the counts.

## Per-case causal chain

### E2E-B01 — external success, agent blocked

1. T1 first chose `read_file(greeting.txt)` before the output existed. This was an RWKV action-selection error and the deterministic verifier rejected it.
2. Recovery chose `write_file(greeting.txt, "Hello, RWKV-LH!\n")`. The Harness executed it and exact-content verification passed.
3. T2 and T3 used the real post-action evidence to complete without another redundant read. The final workspace was correct.
4. The Goal-frontier capsule did not carry the passed exact-content check or the post-action snapshot content. It carried the write arguments, success flag, artifact hash and completed Task labels, while its prompt explicitly said an action-success flag alone was insufficient. RWKV therefore asked for another verification Task even though the lower layer had already verified the exact bytes.
5. Its nested `task_batch` contained `tasks` but omitted an inner `schema_version`.
6. The converter inherited the outer `long-horizon.goal-frontier-step.v2` version and then rejected it as an unsupported Task-batch version. Three semantically usable `continue` outputs were rejected, so the run blocked.

Earliest error: wrong initial RWKV action. Strict-result cause: verified evidence was lost in the Goal projection, followed by a nested Task-batch format conversion defect.

### E2E-B02 — external success, agent blocked

1. T1 correctly read `input.txt` and observed `project=Orion`, `count=7`.
2. T2 correctly selected and executed `write_json(report.json, {project: Orion, doubled_count: 14})`. The exact JSON and key-set external checks passed.
3. Downstream create/verify Tasks correctly reused the real post-action observation.
4. Goal frontier accurately repeated and recomputed the observed input/output values but did not receive the passed exact-JSON/key-set checks from the Task layer. It chose `continue` for an extra verification.
5. Its nested `task_batch` again omitted only the inner protocol version. The same outer-version inheritance rejected the first and third responses; the second response used a single Task object instead of a `tasks` array and was also rejected.

Earliest error: missing verified-result projection made another verification appear necessary. Strict-result cause: common nested/single Task-batch representations were not converted to the one internal envelope.

### E2E-B10 — agent false positive

1. T1 read only `test_slug.py`; it did not read `slug.py` and did not run tests.
2. T1 then falsely completed the two-file inspection after observing only one file.
3. T2's first response entered a long repetition claiming the test file was written; it hit the 850-token output limit and its recovered structure contained invalid repeated evidence refs.
4. The retry falsely claimed the existing implementation already passed tests, citing only the test-file read. No mutation action occurred.
5. The first Goal-frontier response correctly noticed that the implementation was missing and proposed a new implementation Task.
6. That correct recovery response used a single nested Task object and was rejected by the format boundary.
7. On the protocol retry, RWKV changed the semantic decision to `finish` and invented that tests passed. The controller accepted the second semantic answer and produced a false positive.

Earliest error: RWKV prematurely completed a multi-file observation Task. Amplifiers: repetition degeneration, then a format-only rejection forcing semantic resampling that flipped a correct `continue` into an unsupported `finish` claim.

### E2E-M01 — agent blocked, workspace unchanged

1. T1 correctly listed `services/`.
2. T2 read `services/api.json`. Its next output copied the displayed `committed_action` history into the response while also returning `decision=complete, action=null`.
3. The generic tool-call scanner treated the historical `committed_action` as the selected output action and rejected the complete decision as containing an action. Two retries then echoed `task_decision` instead of `decision` and were rejected.
4. Recovery read `services/web.json` but skipped `worker.json`, then falsely completed the all-files inspection Task.
5. T3 produced a substantively valid `write_json` for `services/web.json`, preserving its unrelated `theme`. It also supplied the common explicit flags `overwrite=true` and `create_parents=true`.
6. The runtime implementation already behaves that way for `write_json`, but its declared action schema omitted both flags. Action materialization therefore blocked before executing the correct write.

Earliest interface error: the Task-step converter scanned causal-input echoes as output actions. RWKV error: it later skipped one service file. Final block: declared `write_json` schema and actual runtime behavior were inconsistent.

### E2E-M03 — agent false positive

1. T1 correctly read the original `users.json`.
2. T2 falsely claimed the dependency had already produced the migrated JSON, while its cited observation visibly contained the old `users/fullname/active/legacy_note` structure.
3. The first Goal-frontier response correctly compared the real action observation with the claimed Task status, stated that no migration action occurred, and proposed a repair Task.
4. The repair batch omitted only its inner protocol version and was rejected by the converter.
5. The protocol retry changed to `finish` and trusted the false completed-Task narrative. No write occurred and external JSON equality failed.

Earliest error: RWKV incorrectly interpreted the source read. Amplifier and final FP cause: format rejection discarded the correct independent recovery decision and semantic retry trusted an unverified Task claim.

### E2E-M06 — agent false positive

1. The initial plan omitted the required manifest-production Task and instead planned to read `package/manifest.json`, even though the initial manifest showed that output did not exist.
2. T1 correctly read `selection.txt`, observing only `alpha.dat` and `gamma.dat`.
3. T2, T3 and T4 each completed from that same read-only evidence while inventing that copies, `package/manifest.json` and verification already existed. No copy, manifest write or verification action occurred.
4. The first Goal-frontier response correctly noticed that no copy or manifest action existed, but its reason looped until the 4200-token limit and never formed a complete JSON object.
5. The protocol retry received the same capsule plus a formatting correction. On this second semantic sample, RWKV followed the unverified `completed_task_history` and returned `finish`.
6. External checks showed `package/` did not exist.

Earliest error: incomplete/invalid Task planning. Amplifiers: repeated Task postcondition overclaim, output degeneration, whole-decision retry, and a final authority capsule that exposed model-declared completion history alongside real observations.

### E2E-M12 — agent blocked, workspace unchanged

1. T1 and T2 correctly read `math_utils.py` and `test_math_utils.py`.
2. T3, T4 and T5 each falsely completed from the original broken source observation. No source write and no test command occurred.
3. Goal frontier correctly noticed that the action observations contained only reads and chose `continue` to apply the fixes/run tests.
4. The first response wanted the already-completed T3/T4 Tasks to execute again and therefore returned `task_batch=null`. The protocol has no reopen transition and requires new Tasks, so this was correctly rejected.
5. The next two responses did create replacement Tasks, but omitted the nested batch version.
6. The converter inherited the outer Goal-frontier version and rejected both usable repair frontiers, blocking the run.

Earliest error: RWKV treated observed broken code as proof of repaired code. Strict-result cause: nested Task-batch format conversion rejected the later correct repair direction.

## Cross-case attribution by layer

### RWKV semantic errors

- Five cases overclaimed a Task postcondition from evidence that visibly did not establish it: B10, M01, M03, M06 and M12.
- B10 and M01 show the same multi-object continuation failure: RWKV performed one `read_file`, then claimed an all-files observation Task was complete. M01 recovered once but skipped the remaining worker file.
- M06's Task DAG omitted a required producer and planned to read an output that did not yet exist.
- B01 chose a read of a not-yet-created output before recovering.
- B10 and M06 each produced a correct high-level recovery decision that degenerated through repetition or was later semantically reversed on a protocol retry.

These errors are real model limitations. They should remain visible in the metric; the controller must not rewrite their actions, arguments, evidence or final decision.

### Format/interface defects

- B01, B02, B10, M03 and M12 all reached a useful Goal-frontier `continue` whose Task content was lost because the nested batch omitted only its own protocol version or used the single-Task representation.
- M01 exposed a second conversion bug: a generic recursive scanner interpreted an echoed historical `committed_action` as the selected action of a `complete` response.
- M01 also exposed a mismatch between the advertised and implemented `write_json` arguments.
- Protocol retries resample the entire semantic decision. B10 and M03 flipped from correct `continue` to false `finish`; M06 flipped after a repeated/truncated correct diagnosis.

These are project defects. Fixing them does not choose an answer or alter an action's semantic fields; it makes common surface representations reach the one internal structure.

### Authority/state-boundary defect

- Goal frontier independently corrected the false Task status in B10, M03 and M12 when it attended to action observations.
- M06 first corrected the false Task status, but after output degeneration its retry trusted `completed_task_history`. That history was generated from the same RWKV claims under review, so it is not an independent evidence source.
- B01 and B02 expose the opposite projection error: real deterministic checks and post-action snapshot contents that passed at the Task layer were absent from the Goal-frontier capsule. The Goal model was asked to demand observable verification without receiving the already-observed verification results.

The final completion layer currently receives too much unverified narrative state and too little verified evidence state.

### Prompt and generation observations

- Task-step prompts used about `3035–4395` local tokens even when the active Task state was only a few hundred tokens, because all registered action schemas were repeated in full.
- This remains below the 16384-token context limit, so context overflow is not the cause. It is a measured signal-to-noise concern, not yet a proven root cause.
- B10's Task step hit its 850-token generation limit through repetition. M06's Goal step emitted 23612 characters and hit its 4200-token limit through repetition. B10's final answer also hit its generation limit.

## Frozen standard-answer comparison

The Codex reference file was frozen before the first RWKV run and was forbidden from runtime model input. Comparison is based on the final workspace and the referenced observable checks, not on textual similarity.

| Case | Frozen observable target | Round77 final workspace/output comparison |
|---|---|---|
| B01 | Exact `greeting.txt` bytes with one newline | Workspace exactly correct; agent blocked after success. |
| B02 | Exact two-key JSON `{project: Orion, doubled_count: 14}` | Workspace exactly correct; agent blocked after success. |
| B10 | `slug.py` no longer raises `NotImplementedError`; unit tests pass | Workspace unchanged and tests fail. Final prose described plausible code but never applied it. |
| M01 | Three preserved service JSON files updated plus exact summary | All three service files remained original and summary was absent. A correct web update was proposed but rejected before execution. |
| M03 | Schema 2 records with renamed fields and no `legacy_note` | Workspace remained original. Final prose invented a migrated document and even included `legacy_note: null` while claiming the field was removed. |
| M06 | Only alpha/gamma plus exact digest manifest in `package/` | `package/` did not exist. Final prose used placeholder digest strings and unsupported completion claims. |
| M12 | Correct non-mutating functions and passing tests | Source remained original; external unit tests failed. |

## Problem boundaries for the next user-authored change

1. Common nested/single Task-batch surface formats do not reach the one internal Task-batch structure.
2. Task-step conversion cannot distinguish the selected output action from causal-history action objects echoed by RWKV.
3. `write_json`'s advertised arguments and action materializer disagree.
4. Task-local deterministic checks/post-action evidence are not preserved into the final Goal decision, while unverified Task completion narratives are preserved.
5. Formatting failure triggers a new semantic decision rather than preserving the original decision fields, enabling correct recovery decisions to flip.
6. Multi-object Tasks depend entirely on RWKV remembering which members remain; one successful member read is repeatedly mistaken for whole-Task completion.
7. Repetition at the Task and Goal layers can destroy an otherwise correct decision before JSON completion.
8. Goal recovery can identify a falsely completed Task but the protocol exposes only `finish` or creation of new Tasks, not an explicit repair/reopen relation.

These findings do **not** justify answer rules, hidden-acceptance access, output rewriting or a format whitelist. They define the observed failure boundaries for the user's next implementation.

## Historical positive and negative controls

Round77 的七题不能只在本轮内部解释。使用已冻结的 Round46、Round50、Round51、Round52、Round53 full90 记录逐事件对照后，可以把“当前回归”和“长期未解决问题”分开。

| Case | Round46 | Round50 | Round51 | Round52 | Round53 | Cross-round conclusion |
|---|---:|---:|---:|---:|---:|---|
| B01 | Strict pass | FN | FN | Strict pass | Strict pass | 模型和 Harness 都曾完成过；Round77 block 是链路回归。 |
| B02 | Strict pass | blocked | Strict pass | blocked | Strict pass | Round77 已产生正确工作区，失败位于完成边界。 |
| B10 | Strict pass | blocked | blocked | blocked | Strict pass | RWKV 能在读到源码与测试后实现并运行测试；Round77 的单读后整 Task 完成是回归入口。 |
| M01 | FP | blocked | Strict pass | blocked | FP | 结构能解，但成功轮需要逐文件读写并使用 43 次模型请求，稳定性仍差。 |
| M03 | Strict pass | FN | not created | blocked | Strict pass | 当前无写入 FP 不是能力上限；正确 repair 被协议边界丢弃。 |
| M06 | FP | FP | FP | blocked | blocked | 五轮从未 Strict pass，是稳定复现的长期结构缺陷。 |
| M12 | Strict pass | blocked | blocked | blocked | blocked | 旧链路证明模型会修复两个函数并跑测试；当前读后假完成及 repair 无法落地是回归。 |

### B01、B02、M03 的成功对照

- Round46 B01 的实际动作是 `list_directory -> write_file -> read_file`；B02 是 `read_file -> write_json -> read_json`；M03 是 `read_file -> write_json -> read_json`。
- 三题均把生产和可观察验证作为独立 Task，最终工作区真实正确。
- Round77 B01/B02 已用自动 post-action check 得到正确工作区，却没有把这些 check 投影给 Goal。也就是说，当前结构删掉了独立验证 Task，却没有把替代它的自动验证证据接到最终完成层。
- Round77 M03 的 Goal 已从真实 read observation 识别出迁移未发生，证明 Goal 层有纠错能力；错误发生在 repair batch 的表示进入内部 Task batch 之前。

### B10 的成功对照与一个不能误读的偶然因素

Round46 B10 的任务与动作链是：

1. T1 独立读取 `slug.py`。
2. T2 独立读取 `test_slug.py`。
3. T3 写入 `slug.py`。
4. T4 执行 `python test_slug.py`，exit code 0 且输出 `OK`。

这证明当前 RWKV 在同时看到源码和测试后能够生成可通过测试的实现。Round77 T1 只读了测试文件就完成“两文件检查”，后续没有获得相同的信息条件。

但 Round46 的成功还包含一个不可当成正确架构的偶然因素：T3 第一次生成的是 `tool/arguments/reasoning` 外壳，代码内容不能合并连续空格；严格协议拒绝整个响应后，第二次语义采样改成了更好的实现。该成功不是“严格拒绝格式更好”的证据，而是格式重试偶然改变了代码答案。透明格式转换后，正确链路应当是保留第一次动作语义、让真实测试失败，再由 RWKV 基于失败 observation 修正；不能靠格式错误重新抽取一个更优答案。

### M12 的成功对照

Round46 M12 的实际动作是：分别读取 `math_utils.py` 与测试文件，两次写入相同的完整正确源码，然后运行测试并通过。它说明：

- RWKV 已展示过修复 `safe_divide`、修复 `median` 和运行测试的能力。
- Round77 不是“模型不会写这段代码”，而是 T3/T4/T5 将原始破损源码误当成已完成结果。
- Round46 两个修复 Task 各自整文件写入且内容相同，存在重复写入；它只能作为能力正对照，不能原样恢复成目标结构。

### M01 的成功对照

Round51 M01 使用了 11 个 Task：列目录、分别读取 api/web/worker、分别写回三个文件、创建 summary，再执行三个读取验证。实际三个 service JSON 均保留了无关字段并正确更新，summary 也正确，最终 Strict pass。

这说明 M01 不是参数推导能力不足。Round77 将“三个文件全部读取”放进一个 Task，将“三个文件全部更新”放进另一个 Task；第一次单文件读取之后，全 Task 完成判断完全依赖 RWKV 从自然语言 postcondition 记住其余成员。成功轮与失败轮的核心区别是成员进度是否在结构中显式存在，而不是 JSON 更新算法不同。

### M06 的长期失败对照

M06 在五轮 full90 中从未通过，动作链反复表现为：

- Round46/53：T2 的标题是复制全部选择文件，但实际动作直接写 manifest；没有复制任何文件。
- Round50/51：T2 最多只复制 `alpha.dat`，随后就完成“复制全部文件”；`gamma.dat` 缺失。
- Round52：所有 Task 都重复读取 `selection.txt`，没有 producer。
- Round77：计划本身漏掉 manifest producer，随后所有写入/复制 Task 从同一 read observation 假完成。

根因不是 SHA256 计算；多轮模型都能给出 manifest 值。根因是一个 `copy_file` 原语一次只能复制一个成员，而 Task postcondition 表达整个选择集，系统没有把 `alpha.dat/gamma.dat` 的成员进度作为可见结构保留下来。模型每做完一个成员或只看到 selection，就容易把集合 Task 当成完成。这个问题也直接覆盖目标验收场景“读取大型项目后逐文件处理”：只要成员集合仍只存在于自然语言里，文件数量增加会放大同一错误。

## Source-path mapping of the observed defects

以下是问题在当前实现中的实际落点，不是修改方案或测试特判：

1. `controller.py::_goal_frontier_capsule` 只投影 Task 标签/status、latest action、action output、artifact path/hash。Task 的 deterministic validation results 与 `post_action_workspace_snapshot` 内容没有进入 Goal capsule。因此 B01/B02 的精确检查虽已通过，最终层看不到。
2. `tool_protocol.py::_task_batch_candidates` 把外层 `schema_version` 递归继承给内层 `tasks`。Goal 外层版本是 `long-horizon.goal-frontier-step.v2`，所以一个仅省略内层传输版本的合法内容会被标成错误的 Task-batch 版本。现有单元测试还明确要求 `{tasks:[...]}` 必须失败，测试口径与五个真实 E2E 输出冲突。
3. `tool_protocol.py::_task_step_candidates` 与 `_tool_call_candidates` 对候选对象递归扫描。`complete` 判断因此会把提示/历史中回显的 `committed_action` 当作本次选中 action。现有 complete converter 测试只覆盖 `action=null`，没有覆盖带历史 action 的真实 capsule echo。
4. `harness.py` 用英文描述字符串推断 JSON Schema 类型，而运行时再用另一套手写验证。已经观察到 `read_json.start_char` 被广告为 `string`，但执行器把它作为整数 offset；`write_json` 运行时总是覆盖并创建父目录，模型常输出相应显式 flags，但声明 schema 又把它们判为 unknown。接口并非真正单一来源。
5. `model.py` 的 Task-step 与 Goal-frontier 循环在协议失败时重新调用完整语义请求。它没有冻结第一次已解析的 decision/reason/tasks/action，所以格式纠正可以改变任务语义。B10、M03、M06 已真实发生 `continue -> finish` 或代码答案变化。
6. Goal-frontier 的 `finish` 响应没有 evidence refs。Task-step complete 至少要求 RWKV 选择 evidence refs，Goal finish 却只有自然语言 reason，因此最终完成声称不能绑定到具体 observation/check；M06 的无证据 finish 就由此直接通过。
7. Goal 可以识别旧 Task 假完成，但只能 `finish` 或新增 Task，不能表达“原 Task 的 postcondition 未成立，需要继续/替换该 Task”。M12 第一次正确纠错返回 `task_batch=null`，暴露的是状态转换词汇缺口，而不只是格式问题。
8. 当前 planning prompt 同时要求“最小 DAG、不要把 batch 操作拆成大量 Task”和“每个 Task 是一个 immediate semantic step”。`read_files` 是真实批量读取原语，但 `copy_file`、`write_json` 仍是单成员原语。M01/M06 因而生成集合 Task，却没有与之对应的集合写/复制 action 或结构化 member ledger。

## Order of problems exposed by the evidence

在不替用户决定具体实现的前提下，回归验证应按以下依赖顺序解释结果：

1. 先确认纯格式表示能够无语义改写地进入唯一内部结构；否则正确 recovery 仍会在执行前丢失。
2. 再确认 Goal 能看到 Task 已完成的真实 check/snapshot，并且 finish 能引用具体证据；否则 Task 层修对也会在最终层被误判。
3. 再验证多成员 Task 的未完成成员不会只靠自然语言记忆；M01、M06 和大型项目逐文件处理都依赖这一点。
4. 最后才评估 RWKV 自身的动作选择、代码质量与重复生成。否则格式/状态丢失会继续把模型可纠正的错误放大成 FP、FN 或 block。

当前单元回归通过只能说明现有代码符合现有测试；它不能否定以上问题，因为至少两个错误行为（缺 inner schema 必须拒绝、complete 对象不存在历史 action echo）正是测试覆盖缺口或错误预期。下一轮必须继续使用同一 short7，并额外保留 Round46 B10/M12 与 Round51 M01 的动作链作为正对照，避免只降低 block 却引入新的假完成。
