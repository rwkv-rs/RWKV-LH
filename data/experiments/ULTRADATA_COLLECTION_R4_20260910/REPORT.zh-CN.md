# ULTRADATA_COLLECTION_R4_20260910

固定任务 **Strict 0/3、completed 0/3、mutation 0、动作 1**，全部 3 题有原始结果。终止分类：`{"strong_planner_unavailable": 3}`。总耗时 225.44 秒。

首题完成一次目录观察，Step Auditor continue、Stage Checker advance；下一次计划请求 HTTP 500。第二题 HTTP 200 流触发 single choice 协议错误，原始 SSE 事件未保存，不能断言这是合法 usage 事件或服务无输出。第三题初始 Planner HTTP 500。两个 500 的 provider code 均为 do_request_failed。

角色级：Selector 1 次交接 / 3 次菜单求值；Executor 1 次、Step Auditor 1 次，均自然 stop。两个 Native 完整输入 token 与两个协议输入全部逐字节重建通过，原始需求完整。

Selector 自动候选计数：`{"selector_intent": {"confirmation": 0, "dev": 0, "train": 3}}`；待独立复核：`{}`。候选集 **invalid**，原预注册至少 30 条验证菜单 / 10 个边界、四项覆盖及非空固定切分未满足，optimizer steps **0**。错误工具参数不是自动正例，也不发明纠正标签。后序角色未出现不构成当前角色训练禁令。

源码固定本地提交 `82319f95`，两轮采集期间全部源码不变；五角色独立 zero，Selector 2.9B，其余 RWKV 13.3B，Planner / Stage Checker 为 gpt-5.6-sol。角色采集条件与覆盖 scope 在采集前冻结，项目家族沿用原身份和 80/10/10 SHA 切分，没有为了补 confirmation 改名。两轮共用 scope，可报告同条件下的覆盖缺口；没有创建正式训练数据版本。

本轮继承源码对应的完整工程回归 **1321 passed、0 skipped**；见 ROLE_CHAIN_ROOT_REPAIR_R1_20260910/FULL_TESTS_ATTEMPT_04.log，SHA `0d9191484fb04880c7c5f627261a7d322bf4bf5706a5e2143e406a3f35141e01`。服务器只使用完整上传源码 manifest，没有调用 Git。未读取 Holdout，没有把私有验收或参考实现交给 Agent，没有重评分历史运行。

本轮结果不再修改。下一轮先修数值缓存发布的生成边界，并保留强模型失败的原始流证据；查明其响应类型后才能修改解析，不能放宽为接受未知事件。重新冻结后再采集、训练及验收。完整文件 SHA 清单见 EVIDENCE_SHA256.json。
