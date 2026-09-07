# R1 角色输入构造与 Selector 身份统一

本子项没有运行 Agent benchmark，因此 Strict、completed、mutation 和终止原因均未新增测量；不据此主张 Agent 能力改善。

根因：Selector decoder 的目标前缀在协议、manifest 校验和 suffix 构造中分别硬编码；Step/Final Auditor 与 Finalizer 的生产输入在 model.py 中手写，而协议模块只承担校验与渲染。不同入口可以各自组装协议且缺少同一构造入口。旧 Selector v2/v3、Step Auditor v2 身份 stub 也仍存在。

实施：在四个当前角色模块中增加 build_prompt_source；Step/Final Auditor 构造器内部调用各自的 build_gap_catalog。model.py 的这些角色及 Executor disclosure 均改为调用所属协议的输入构造器。Selector 网络渲染统一调用 Selector builder；服务 manifest 与实际候选 suffix 均引用 selector_intent_v4.TARGET_PREFIX。各当前协议集中定义 PROMPT_PREFIX，Selector 另集中定义菜单、角色、目标前缀和 endpoint。没有添加模型调用或改变角色职责。

根据 owner 本轮“旧的全部本地清理”的新指令，删除 Selector v2/v3 和 Step Auditor v2 三个 stub，取消旧网络协议的导入和常量。网络入口对任何非当前 schema 通用拒绝，保留旧版本与未来版本的拒绝测试。

测试数据只来自现存公开 unit test：在修改角色构造器前捕获三个公开角色样例的原始渲染 bytes，保存到 role_prompt_wire_baseline.json。该文件记录原测试文件 SHA、捕获脚本 SHA、三个原协议模块 SHA；没有读取 confirmation 或 Holdout。新回归直接读取这份固定数据，经新构造器渲染后逐字节比较，不依赖 temp 脚本。

先失败再通过：

- selector_prefix_red.txt：新增 single-authority prefix 回归先 1 failed（缺少协议 TARGET_PREFIX）；回归通过前同步修复 manifest loader、服务初始化和实际 suffix 构造。
- role_builders_red.txt：三个角色的 wire bytes 回归与两个 Auditor catalog 构造权威回归先 5 failed（缺少 build_prompt_source）。
- role_builders_selector_green.txt：首次聚焦回归 13 passed；随后补充更全面的非当前 schema 拒绝参数。
- role_builders_production_green.txt：Stateful Goal Loop、exact tool handoff、native Selector、role builders 共 78 passed（42.24s）。

追加清理：预算估算原先仍调用旧的 independent Executor 工具披露 renderer。现在 model._executor_prompt_source 读取真实 checkpoint 保留的 durable facts 和 causal history，并连同 Controller execution_state 调用唯一 Executor v4 builder；预算估算与实际工具披露使用同一个来源及 render_generation_prompt。Session 接受经过当前协议构造的 executor_source，不再接受独立角色的通用工具披露 fallback。预算估算只有本地构造和 tokenizer 计数，不调用模型。独立 Selector 模式的 terminal_answer 与 final_answer 工具披露直接拒绝，要求专用 Finalizer / Final Auditor；无独立 Selector 的通用 Controller 接口继续可用。

该追加子项的新回归先 2 failed（executor_entry_budget_red.txt），实施后 tests/test_role_prompt_builders.py 7 passed（executor_entry_budget_green.txt）。统一新 Session API 后，完整定向生产回归共 80 passed / 25.08s（role_builders_production_after_executor_entry_green.txt）。首次使用新 basetemp 时父目录 data/test_runs 不存在，导致 52 个 fixture setup 错误；原始日志保存在 role_builders_production_basetemp_setup_error.txt，创建父目录后原样重跑全部通过，没有改变测试口径。

兼容性说明：三个固定 Auditor/Finalizer 样例的实际角色 prompt bytes 保持不变；清除旧 REQUEST_LAST 身份后，Executor role bootstrap 的 protocol 标签改为当前 v4 模块常量，因此不能声称整个 bootstrap bytes 不变。后续 Agent 对比必须统一使用本轮代码，两臂不得混用旧代码。

全局影响与回归风险：所有现有生产角色输入都经过所属协议构造入口；已有合法输入的字段顺序和文本保持一致，三个 Auditor/Finalizer 样例逐字节固定。删除旧 stub 会使历史脚本的旧模块导入失效，属于 owner 要求的清理边界，不能再以历史协议恢复执行。完整 suite 与全局脚本/数据清理由主代理统一验收，本子项不声称已完成 Agent 级全场景验收。

源码与测试数据 SHA-256 见 role_builder_source_sha256.txt；本文件对应主轮次 PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907。
