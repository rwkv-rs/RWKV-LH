# Round25 预注册协议：统一因果状态主干

> 状态：`preregistered_implementation_in_progress_not_run`。本文冻结时尚未发出Round25 RWKV请求，未读取任何Round25
> hidden acceptance。Round24代码基础已作为`fef3a3b`上传；Round25按用户确认把原分轮项统一为一个根因整改。

预注册日期：2026-08-13。唯一结构变量名为`unified_causal_state_backbone.v1`。

## 根因假设

Round23全90题证明，Goal、Plan、action、Task、member、revision、outcome、proof分别维护局部状态，Controller又用单一
`completed`位连接它们，造成旧历史、局部effect和错误revision被当成当前因果事实。Round25不再新增平行状态机，而让全部环节
引用同一个append-only causal ledger和同一个current-state capsule。

## 统一状态

1. 每个Goal criterion由RWKV提供原始用户请求中的精确`source_quote`；Controller只校验substring，不合并、删除或改写criterion。
   取消5项语义上限，保留仅防资源耗尽的24项协议上限。
2. Plan改为最多8个ready-frontier task，不要求一次覆盖全部Goal。每个task由RWKV声明`operation_kind`、`subject_key`、
   `member_key`、`phase_key`、`effect_targets`、`expected_outcomes`、`dependency_outcomes`和`postcondition`。
3. Task只有在direct dependency的实际typed outcome符合RWKV声明的edge时ready。`not_found/invalid/conflict/nonzero/timeout/
   post_effect_unknown`是可观察outcome，不自动等于错误或成功；是否是合法分支由RWKV的task contract决定。
4. 每个Harness artifact写入append-only revision ledger，记录target/hash/task/attempt/outcome及Task commit状态。Controller不得按内容
   选择旧revision、回滚artifact或修改payload。
5. collection/member/phase状态从RWKV task contract和真实attempt/revision确定性投影；未知fan-out先由observation frontier展开。
   单member effect不自动聚合为collection完成。
6. model输入统一为Goal provenance、active task、direct dependency最新commit、typed outcome、member/phase投影、target revision、最新
   failure fingerprint；raw history仍完整审计但不进入current capsule。
7. effect observed、Task postcondition committed、Goal evidence继续严格分层；Goal proof只能使用RWKV声明且运行时可追溯的独立source。

## 不作弊边界

- Controller不得生成task/member/phase/target/outcome edge、criterion、expected值、action argument、答案或final output。
- typed outcome只由真实Harness error/exit/API status机械分类，不参考case、acceptance或输出正确性。
- revision ledger只记录事实，不选择“更正确”revision，不恢复旧bytes。
- frontier扩展和fallback/compensation/lifecycle选择必须来自RWKV raw decision；规则只检查引用和状态一致性。
- 不运行多个候选后按External结果择优；hidden acceptance只在全90冻结后离线使用。

## 固定验证

- schema/store迁移、frontier≤8、完整task contract、outcome edge、collection/member identity、revision append/commit/reject、crash resume、
  unchanged digest、capsule无旧history、atomic action semantic mutation=0的单元/对抗测试；
- 完整pytest、LH-Control-30、E2E90 validate-only和Round18–24历史replay；
- 正式E2E仍使用Round23固定endpoint/model/context/sampling/concurrency8/max transitions200。

## 指标与晋级

- External/Strict/Completed/FP/FN；first producer；zero-execution；frontier size；abstract/compound task rejection；typed branch；member coverage；
  correct revision retained/destroyed；effect/Task/Goal三层；requests/tokens/context overflow/重复digest。
- 只有FP=0、全回归通过、semantic mutation=0，且不劣于Round16 External 24并至少一项Strict/Completed/External严格改善才上传
  为更优版本。否则保留实验并标记`do_not_upload`。
