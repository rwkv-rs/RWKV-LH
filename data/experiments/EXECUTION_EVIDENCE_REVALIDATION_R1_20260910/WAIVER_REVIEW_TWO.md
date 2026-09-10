# 独立 AI reviewer two：来源等价豁免复核

日期：2026-09-10。身份：`AI-reviewer-two-/root/waiver_review_two`。依据 owner 明确授权两个独立 AI reviewer；不是人工签名，也没有代替语义标签复核。独立审阅，未与 reviewer one 交流。未读取 holdout、acceptance 或私有题答案；未改生产源码或 waiver。

## 决定

**accept，仅限精确 SHA 对的历史 trace 来源准入豁免。** 六文件变化不要求退役现有五角色协议或改变 RWKV State 序列/模型语义；可以把旧执行事实作为旧执行事实交给当前抽取器继续校验。此决定不承诺新旧执行行为等价，不确认旧标签为正确，不证明 15/15 已通过实际重提取，也不授予训练/数据集冻结准入。抽取中的不一致必须拒绝，不能再通过 waiver 覆盖。

被审草稿 SHA-256：`b5c21e4788f63775da30974279a0954eedc0c999b38a18e6367cd447cbdfdff0`。本地 HEAD b3e89de6。逐项计算工作树 SHA 全部匹配 current pin；通过本地 git show 核验 frozen pin：六项均与 fdce0843 中文件匹配，harness **不**匹配 ca5b2edf，故完整审阅包含 fdce0843→ca5b2edf 的命令入口修复以及 ca5b2edf→b3e89de6。

| 文件 | frozen SHA-256 | current SHA-256 |
| --- | --- | --- |
| `rwkv_lh/harness.py` | `cbfb8348485e9dbc4c92425fc3eccd77693fbbe9c4c4749eeebd0159316cf193` | `b2501cfe0853a94755143d6b742333e710abcf29728b4c6dc98b1970ab7d98b5` |
| `rwkv_lh/stateful_goal_loop.py` | `5d1bec0798bc49b394285bf8d6e270155d343d2c9f09010ab127251f0e469441` | `9c40a80635b23b11059f86541a006a39ddff9a1b15f66a47fe2d541baeb8f105` |
| `rwkv_lh/supervisor_openai.py` | `4efdecc5a24973439f2c02ac7568bace4f9ec3dba441cf2d7107083b2a588b5b` | `52b264b5f65983d191797d62bf41fbda2782d75a9b66960b693f3d15b5eff22a` |
| `rwkv_lh/runtime/openai_compat.py` | `ffb2a85c598e49f27813a45acfae5b5764b89ca28c8520b348199bf7113a8cbb` | `a1d8543adacdc2f0096800979e72b5895dc385a4e1b52a29ed1744170444dddd` |
| `rwkv_lh/runtime/protocol.py` | `8cd5c491e65ba2d1026e411d024f4d885e7660b93393ddab2b5dfe7e9e7bee1e` | `6ba115856f7b5d7e5b8751b462e8326b795509619040781f15067628cc8ea056` |
| `rwkv_lh/runtime/settings.py` | `0a4987a92bb13b9f09e84f062c007897904fa64faf890745a13491bd83a4d459` | `2184d0c55eb4d58637296f6a57ed90c195b993abb959bf944aa286a30807320d` |

## 逐文件判断

1. `harness.py`：accept for admission。审阅包含 Python console script / native executable 区分、解释器参数保留、venv/PATH/沙箱路径映射、check_command discardable workspace、失败/超时结果及部分 stdout/stderr。执行效果明确改变，尤其旧 check_command 可能持久写入，新版会丢弃写入；因此不能声称旧执行结果等同当前结果。其结果仍是可追溯生产事实，旧失败不能变成功，旧副作用不能抹去。工具说明改变如果影响某边界输入，checkpoint byte rebuild 应拒绝对应样本。本轮只放开文件身份代理。
2. `stateful_goal_loop.py`：accept for admission。已执行但失败的 run_command 也检查 write scope，移除 success early return。控制器对旧事实的完成判定可能改变；不改变已冻结因果事实、角色协议常量或模型 State 算法。旧 auditor 通过记录不具有语义标签权威，不能依赖本 waiver 继续把旧漏检视为正确。
3. `supervisor_openai.py`：accept for admission。删除两处未调用 env helper；接受 finish 后无内容尾帧，拒绝新增文本/finish reason 改变；输出耗尽在原 retry_attempts 中同预算重试；review/directive 默认预算翻倍。新生成轨迹和分布可能改变，历史已记录 Planner 输出仍可作为真实上下文。不是 Planner 新旧采样结果等价证明。
4. `runtime/openai_compat.py`：accept for admission。connect-only HTTPAdapter 重试、mutation Connection: close、首次异常审计、收据查询和同 prepared request 有界重发均属传输与恢复。没有改 token 构建、State commit/rollback 合同或模型参数。核查 native_request_recovery.py 的 _claim 在 invoke 前事务登记，重复 request id/digest 不启动第二次执行，unknown 禁止重执行。注意两次 404 只证明查询时目标 journal 无记录，不能绝对证明在途请求永远不会到达；安全依赖同 journal 的去重和部署身份连续性，不是等待次数本身。不得将任意网关 404 或换 journal 当作完整未执行证明。
5. `runtime/protocol.py`：accept for admission。新增 RWKVRequestNotRecorded transport 异常类，未改 State 请求数据结构、角色协议或 token 算法。其“never executed”文案有上述时序/服务身份前提，不可扩大解释。
6. `runtime/settings.py`：accept for admission。新增 native_resubmit_attempts 配置及角色继承。默认 2 在客户端是包含首次 POST 的总尝试数，最多一次重发，不应描述成两次额外重发；对已冻结 trace 的输入字节和角色目标没有直接改写。

## 准入器和标签边界

审阅 role_trace_dataset_v1.py：read_equivalence_waiver 要求 decision=accept、两个不同非空 reviewer 字符串、已 pin 文件哈希、严格字段、唯一条目、非空 rationale/evidence refs，并拒绝 vocab、五角色协议模块及 scope 外文件。_validate_frozen_scope 只允许 exact frozen/current pair；source manifest 自身身份仍验证。CLI 要求文件与独立 SHA 同时给出。source/run、协议身份、SQLite/因果时间线、checkpoint transcript、原始 generation、server input token 和 State 证据的下游校验仍执行。

该验证器不认证 reviewer 人员身份，也不读取 evidence refs 证明其内容；本报告提供可审计 AI 身份与范围。直接调用内部 load_source_run 并手工构造 waiver mapping 不经过文档 parser，不能把该 API 用作扩大授权的入口。

Executor 正例仍要求真实成功动作和对应 wire arguments，失败动作不能经复核变成成功；Auditor/Finalizer 语义正例仍要求独立、逐边界复核。已有 Selector 人工/AI 标签劳动是否可复用，必须保持边界、输入、目标与证据绑定，本 waiver 不给其自动背书。当前切分污染、训练覆盖及数据冻结门均不变。

## 验证及局限

独立运行 `.venv/bin/python -m pytest -q tests/test_role_trace_dataset_integration.py -k waiver`：**4 passed、42 deselected、8.90s**。这是定向选测，无 skipped，不是全套回归或真实 15 题准入结果。测试覆盖精确 hash 配对、无 waiver 拒绝、不可豁免路径及 provenance；实际历史 trace 重提取由主任务执行并单独留证。

未执行模型评测或训练；无本轮 Agent 指标、无角色能力增益结论。源 trace 准入与样本准入分开报告；若任何当前输入字节/目标合同不匹配，应原样拒绝而非追求“全部保住”。
