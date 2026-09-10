# NATIVE_BOUNDARY_HISTORY_AUDIT_R1_20260910

历史 Agent 结果不变：UltraData R2 Strict 0/3、completed 0/3、mutation 0、动作 9；R3 Strict 0/3、completed 0/3、mutation 0、动作 2。没有新模型调用、标签或训练，optimizer steps 0。

为回答“以前为什么没有遇到”，只读取两轮已封存 trace、SQLite 的 checkpoint 数值元数据，逐文件核验原始 SHA，没有执行退役角色协议或重评分。31 次返回中，22 次能由 durable committed checkpoint 核对父 State、生成 token 数和输出 State，22 次全部为 processed_after - processed_before - returned_token_count = **2**；9 次缺少完整可用的 checkpoint 对，保持未证明。

逐轮计数：`{"ULTRADATA_COLLECTION_R2_20260909": {"generations": 15, "measurable": 9, "drifted": 9}, "ULTRADATA_COLLECTION_R3_20260909": {"generations": 16, "measurable": 13, "drifted": 13}}`。原始逐次证据见 BOUNDARIES.json，SHA `581d56334d8f64913736c5f4ae7b5c3391c81ef5ed511db343ecee0c4761cbf3`。

这证明边界偏移在本轮交接 R1 改造前已经有记录。旧服务缺少生成前完整 token 历史核验，未及时把同类偏移报成错误；不能把“之前没报错”等同于“之前 State 正确”。历史元数据无法独立还原全部已消费张量或确定最早引入的提交，也不能将全部旧 Agent 失败归因于这一项。R2 新规则的真实数值验证另见 NATIVE_BOUNDARY_REPAIR_R2_20260910。

初版审计辅助脚本假设候选 checkpoint ID 等于提交 ID，遇到 KeyError 后改为按 candidate_id 连接已有 committed 事件；没有修改数据或重新调用模型。临时 helper SHA `b3092d585da30380d440a2a80941a789fdd33dd37bba8b42abd839d3f3c68502`。未读取 Holdout，服务器未使用 Git。
