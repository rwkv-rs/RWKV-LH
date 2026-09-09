# REALPROJECT_HANDOFF_COLLECTION_R1_20260910

固定任务 **Strict 0/12、completed 0/12、mutation 0、动作 0**，全部 12 题有原始结果。终止分类：`{"strong_planner_unavailable": 10, "model_transport_unavailable": 2}`。总耗时 801.78 秒。

十题在初始 Planner HTTP 500 处保持 pending。RP-MAINT-02 和 RP-CLI-02 获得计划与工具选择；Executor 首次生成的 search_text 参数使用范围外 path='.'，被正确拒绝，第二次生成前 Native 输入证据与数值 State 边界不一致，按 model_transport_unavailable 中断。原始 run.status 保持 running/pending，不伪装完成。

角色级：Selector 2 次交接 / 6 次菜单求值；Executor 4 次请求、2 次返回，后两次因 Native 状态边界错误没有返回；没有到达审计或 Final。两个已返回 Native 输入 token 和四个已披露 Executor 协议输入重建通过。数值边界核对见 NATIVE_TOKEN_EVIDENCE_FAILURE.json：首次输出提交后，服务器 processed_token_count + 1 比保存的完整 token 数多 2，后续 append 继承偏差；第一处错误发生在生成结果 State 的捕获/发布，不能仅修改计数或跳过证据校验。

Selector 自动候选计数：`{}`；待独立复核：`{"selector_intent": 6}`。候选集 **invalid**，原预注册至少 30 条验证菜单 / 10 个边界、四项覆盖及非空固定切分未满足，optimizer steps **0**。错误工具参数不是自动正例，也不发明纠正标签。后序角色未出现不构成当前角色训练禁令。

源码固定本地提交 `82319f95`，两轮采集期间全部源码不变；五角色独立 zero，Selector 2.9B，其余 RWKV 13.3B，Planner / Stage Checker 为 gpt-5.6-sol。角色采集条件与覆盖 scope 在采集前冻结，项目家族沿用原身份和 80/10/10 SHA 切分，没有为了补 confirmation 改名。两轮共用 scope，可报告同条件下的覆盖缺口；没有创建正式训练数据版本。

本轮继承源码对应的完整工程回归 **1321 passed、0 skipped**；见 ROLE_CHAIN_ROOT_REPAIR_R1_20260910/FULL_TESTS_ATTEMPT_04.log，SHA `0d9191484fb04880c7c5f627261a7d322bf4bf5706a5e2143e406a3f35141e01`。服务器只使用完整上传源码 manifest，没有调用 Git。未读取 Holdout，没有把私有验收或参考实现交给 Agent，没有重评分历史运行。

本轮结果不再修改。下一轮先修数值缓存发布的生成边界，并保留强模型失败的原始流证据；查明其响应类型后才能修改解析，不能放宽为接受未知事件。重新冻结后再采集、训练及验收。完整文件 SHA 清单见 EVIDENCE_SHA256.json。
