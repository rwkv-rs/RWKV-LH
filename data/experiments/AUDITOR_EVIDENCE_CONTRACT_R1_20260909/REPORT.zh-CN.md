# AUDITOR_EVIDENCE_CONTRACT_R1_20260909

Agent 最新实际结果保持 UltraData R2 **Strict 0/3、completed 0/3、mutation 0、动作 9**，全部 `identical_success_budget_exhausted`。本轮工程测试没有新增 Agent 分数；修复后另行冻结 R3，不重评分 R1/R2。

角色级原 R2 为 Selector 九次交接 / 27 次菜单求值、Executor 九次、Step Auditor 六次，后续角色未调用。六次审计都有完整观察，却选择 root-unproved。原始输入重建 SHA、输出及反馈见 R2 `CONTRACT_COMPARISON.json`。本轮没有训练，optimizer steps 为 0。

## 根因与全局影响

Step Auditor 的 gap catalog 无条件列出每个 read/write root，并用否定陈述描述候选缺口；Final Auditor 同样无条件声称回答遗漏结果、缺乏证据。生产只校验审计选择的 gap 是否在目录里，而角色数据校验另有 `_validate_step_gap_facts` 拒绝机械矛盾。因此同一个错误输出在生产被接纳、反馈到下一次选择，在数据链却被拒绝。

这是所有任务共用的审计输入及验证不一致，非 UltraData 路径或题型问题。原 Controller 的 REPAIR 留在同一步行为正确；错误事实通过反馈形成重复动作。目录观察完成只证明已观察范围，不证明业务步骤或最终目标完成；修复不把工具成功自动转为 continue。

## 当前实现

1. Step Auditor 统一升级为 `auditor_step_v5.py` / auditor-step.v5；删除旧模块与旧字节码，更新生产、数据、脚本、测试和当前文档引用。Final Auditor 仍只有 `auditor_final.py` 一个入口，升级为 auditor-final.v4。
2. 两个 renderer 明确标记 `catalog_semantics=possible_unmet_conditions`，说明目录项是待判断的条件；phase、root、最终候选的条件改为规范性表述。RWKV 根据真实 evidence_records 判断是否满足。完整的空结果可证明被观察资源为空或没有匹配项，仍受实际观察范围约束。
3. Step 共享协议根据同一份可见证据排除与已证明 read/write root 事实矛盾的候选 gap，并拒绝模型强行输出这些 gap。使用已有作用范围判定；成功、完整性和投影状态必须支持完整观察。命令成功不证明任意文件已读取，失败、截断、完整性未知、不同 root、投影不完整保持可报告缺口。
4. 原数据侧独有校验删除；生产和角色标签共同调用协议 `validate_source()`。语义成功条件仍可产生 REPAIR，独立标签复核仍必需；Controller 不改写模型裁决、不生成替代回答、不增加裁判模型。
5. 机械矛盾使用既有协议错误路径：保留原审计边界和已提交动作，将校验错误交给该审计角色重试。回归验证两次审计属于同一边界、第二次输入含修复反馈、只有一次 Selector 交接和一次实际工具执行，Planner 只调用一次。

本轮没有改变 Selector/Executor/Finalizer 协议、角色 State、模型权重、三菜单规则、Planner 计划规模或各类预算。Native 跨角色 checkpoint 前置依赖尚待独立整改，没有将它声明为本轮已解决。后续角色的实际能力仍需 R3 观察。

## 验证

- 最初红测夹具为 list_directory 提供了不合法的空字符串输出，先在投影层失败；原日志 `RED.log` 保留。补成合法结构化结果后，原生产代码为 **11 failed、6 passed**，记录在 `RED_CORRECTED.log`；不将夹具错误冒充根因证据。
- 修复后相同定向集 **17 passed**；进一步补充完整性未知及不完整投影边界，最终纳入完整测试。
- 协议、角色 builder、角色标签、五角色 trace 重建、数据集集成、协议清理以及 Controller 闭环：**200 passed，121.38 秒**。
- 完整 `.venv/bin/python -m pytest -q tests/`：**1162 passed，0 skipped，175.93 秒**。使用 frozen uv 环境，selector-runtime / benchmark-web / dev 和 Playwright Chromium 完备；没有跳过 Torch、State 或浏览器测试。
- 仅更新发生协议变化的两个审计 wire fixture；Finalizer 原 prompt 字节保持不变。它们是公开单元测试输入，不是正式角色回归集、训练标签或真实用户 trace。

原始评分和生产 trace 保持冻结。新角色输入协议不能用于重放旧注册数据；R3 通过现有 runner 独立采集。工程回归证明本轮契约与恢复不变量，不证明 RWKV 语义准确率或完整 Agent 验收。最终 SHA 清单见 `EVIDENCE_SHA256.json`。
