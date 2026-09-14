# R1：原子编码纠正进入统一freeze

本轮没有新Agent推理任务，Strict/completed/mutation不适用。真实旧失败候选重新验证：原样强模型补丁保持不变，原工作区测试exit=1，修改后exit=0；这是纠正标签的执行证据，不是RWKV独立完成或新能力分数。新训练步数0，未出版正式数据版本。

## 工程增量

已有离线验证器只产出validated_candidate，正式direct freeze只接收读取/回答，无法将真实编码纠正纳入统一训练。现增加verified_coding标签，只支持原RWKV写入边界的write_file/replace_text，仍沿用生产协议和输入构造器。

freeze核对封存验证报告与源run、模型、输入文本/token、State边界、request、原样target和审核记录完全一致；重新执行原快照红→绿，拒绝仅标成功但实际未通过的报告。结果随数据封存为coding_validation.json，训练加载核对其SHA与数量。编码覆盖下限必须显式注册。外部检查及审核不进入input或target。

新增回归覆盖：绑定错位、checksum变化、源内容变化、旧成功报告重新验证失败、非原子编辑目标拒绝、freeze封存和训练加载拒绝篡改。先失败的6项记录在RED.log；局部36 passed。全量结果在FULL_TESTS.log，最终结果以交接追加为准。

## 真实来源与边界

复用R2的同一原样补丁及双审核，不重新索票。原RWKV来源RWKV_EXPLICIT_EDIT_R1_20260914/runs/atomic-2/execution；纠正生成来源RWKV_VERIFIED_CORRECTIONS_R1_20260914/recovery/effective_edit。归属仍为强模型纠正、MAINT/train；同一问题的14个关联run不算14独立来源。

当前只完成原子修改标签通路，不支持从任意读取/停滞边界自动生成编辑标签，不包含测试反馈后续多步标签；强模型语义审核仍有漏判，结构校验无法替代人工事实核对。当前原始失败不改，原数据128行不改，52行引用提案不等于新数据已发布。

## 训练准备检查

本机GPU0为16GB 5070 Ti；远端rwkv-8222的GPU0为96GB RTX PRO 6000，UUID GPU-1faf7f09-25f4-2515-b707-6e0766aa841d，检查时现有EngineCore约39GB。历史训练UUID实际是该服务器GPU1，不能复制旧启动参数。远端只执行了nvidia-smi只读查询，没有Git、部署或启动训练，也未停止现有进程。

下一步围绕统一多缺陷训练：补有效修改及真实测试反馈的不同来源，按已有家族隔离复核，再冻结数据、当前完整源码清单、GPU0运行一致性、一个候选预算及固定验收。历史128条训练NO_KEEP保留；不得把旧State直接继续训练当zero对照，也不靠堆同一来源变体增加覆盖。Owner已授权自主继续，无需重复许可，但正式训练注册必须具体并在运行前完成。

补充来源覆盖审计：对获准现有库存中的12个可重建编码run逐个重放，仅2个write_file/replace_text边界。详见CODING_SOURCE_COVERAGE.json；计数不是独立问题数或成功率。当前原子修改通路的覆盖不等于已覆盖“反复读而不修改”这类工具选择边界，后者需要单独构造可见证据完整的纠正与回归，不能由程序把read改成write。

首遍全量测试受到我并行启动定向测试的干扰，导致共享basetemp中的SQLite文件丢失，原3项失败保留于FULL_TESTS_INTERFERED.log。最终源码固定后单独重跑；不改SQLite生产实现或放宽测试。详见TEST_INTERFERENCE.zh-CN.md。

最终补充快照封存门：freeze还要求原before快照每个文件列入同一源清单，不能只靠报告中一个可另行提供的快照总哈希。SNAPSHOT_RED.log保留先失败回归；GREEN_FINAL.log为37 passed。补全真实源快照逐文件清单后重新运行（SEALED_CODING_REGISTRATION、REAL_RESULT_SEALED），原样补丁仍exit 1→0。此前记录保留，不以新结果改写旧证据。

最终验证：1725 passed、0 skipped，318.89秒，GPU0，最终源码固定后完整执行。较进入本轮前1710项新增15项。两次中间失败原日志及执行原因保留。owner五处差异SHA仍为314ca524bbb1e4fc28460409f1068222f29f1819cb410d025edefe64c8f796e0，未覆盖或纳入源码提交。生产协议/input builder未改；本轮只增离线训练准入逻辑。证据逐文件SHA见EVIDENCE_SHA256.json，原始文件打包于EVIDENCE.tar.gz。
