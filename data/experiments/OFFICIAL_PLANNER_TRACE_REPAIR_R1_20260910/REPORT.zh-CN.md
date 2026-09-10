# OFFICIAL_PLANNER_TRACE_REPAIR_R1_20260910

Agent 最近完整官方实测仍为 UltraData R5：**Strict 0/3、completed 0/3、mutation 0、动作 1**；1 题角色协议拒绝耗尽，2 题 Planner 输出中断。旧 12 题 REALPROJECT R1 为 0/12、0/12、mutation 0、动作 0。本轮完成工程整改和后端验证，没有新增 Agent 分数，实际角色 optimizer steps 仍为 **0**。

## 已复核根因与完整影响

1. R5 两题都收到 HTTP 200，SSE 自然结束边界为 length；各消耗 32768 completion tokens，其中 reasoning_tokens 同为 32768，正文长度 0。之前的解析器先检查空正文，丢失了失败记录中的停止原因和用量。官方 DeepSeek 默认启用 high 思考，原请求没有显式配置思考强度。HTTP 500 网关故障与本轮输出耗尽是不同问题。
2. 生产注册表有 23 个工具；离线角色输入重建只用了默认 18 个工具。第一题的 12 次 current_time 参数交接因此无法重建。检查全部同类引用后，发现 Executor 标签的接口归一化也使用同一不完整注册表，会误拒五种扩展工具的合法样本。
3. 第一题 Planner 把“外接矩形四条边均有对象”强化为“每一行和每一列都非空”，并把错误算法写入不可变目标及独立推导阶段。可见第 4 个公开样例中，该公式给出 591535028，而题目要求 976668549。此错误未执行成代码，不能声称它解释了每次角色拒绝。

R5 的原始分数、trace、标签及停止边界全部保留。不存在通过修改旧结果使本轮达标。

## 当前修改

角色输入重建和 Executor 标签校验共用同一个不执行工具的 Harness 工厂，通过生产 build_retrieval_actions 构造扩展定义，并复用实际 connector 支持的操作集合。没有复制工具 schema，没有 current_time 特判，不读取 workspace 或创建网络/快照运行时。重建仍核对原始 disclosure 的定义 SHA，不能拿保存的 prompt 当定义权威。

Supervisor 增加按角色配置的通用 request options，并绑定公开配置、实际请求 SHA 和响应缓存。任意提供方的能力参数从配置传递，不按模型名称枚举适配；身份、输入、协议、传输和输出预算不得被覆盖。下一轮 Planner/Stage Checker 均显式 thinking=enabled、reasoning_effort=low；最大输出保持 32768/16384，读取预算保持 600 秒。

在内容解析前记录完整响应 envelope、usage 和 finish_reason。length（或 Responses 的 max_output_tokens 中断）明确记为 generation_limit，不接受空、部分或碰巧完整的 JSON，也不重复发起相同模型请求。缺失 stop、过滤及空自然停止仍按各自协议证据拒绝，不能伪装成任务完成。

Planner 提示补充职责：先产出可执行计划，不先完整求解任务；内部算法思考不单独变成 Harness 动作；不可将猜测的算法、加强的量词或未请求限制写成不可变目标。**这是待实测的语义约束改进，不是数学正确性保证。** 五角色协议及输入 builder 未换版，无额外模型调用或外置判断 Head。

## 验证与部署

先失败后通过：工具重建 1 项、请求策略 18 项、扩展标签 5 项；专项最终 45 passed。完整回归 **1414 passed、0 skipped、226.06 秒**，日志 SHA `58ce6b80ebbce19ee8b759a8f8232e1425e0f5970d5fc258772e1f5998cd6096`。首遍唯一失败来自新测试继承其他测试的环境变量，已隔离，不是放松生产配置冲突校验。

在修改 Supervisor 源码之前，对同一 R5 第一题仅更新允许独立升级的 role_trace 重建器：**14/14 角色输入与原始交接字节一致，14/14 Native 完整输入 token 核验通过**。旧轮原核验只有 2/14 角色输入成功。此核验只证明交接，不改变训练目标或评分；证据 SHA `0eaeaef284d3368c728bd595dc0396a707aa3b6c6c44f1739cc96d1b1726b585`。

最终源码部署根 `/home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910`。项目 131 文件清单 SHA `0953f64292f0a0411ca42f9b8b5f7452af5cec11b8b3f12c90c5976a927434e0`，engine 6393 文件清单 SHA `07bb8f39eba57b513e862bf23dd439e11cd264a03ce1c942678d140466c2b352`，服务完整核验后启动，服务器没有执行 Git。Native 当前 build 为 `0.23.1rc1.dev1942+g67f0c5996+native.4970b89a548fc5b1dffbbdff91c3be2021f3cd953c934d343458b576e48b5c35`。前一份尚未包括下游标签修复的部署/数值证据保留为过程记录，两项 current 服务只使用最终目录。

最终 2.9B 后端核验通过：zero/非对称非零 State × 1/17/128/16384 token，8 项全词表最大误差均为 0；1/17/128/16384 反向的全部 32 层 State 梯度有限非零，底模不变、prompt 直接 loss 梯度为零、独立样本无 State 泄漏。耗时 134.93 秒；runtime SHA `2012b5eefe9e579e757e52e8ac471f9a10ecafc1edd4fb4ae88170fcea31f55d`。数值检查不执行优化器。

## 下一步与未解决边界

下一轮 ULTRADATA_OFFICIAL_COLLECTION_R6 与 REALPROJECT_OFFICIAL_COLLECTION_R3 将重新登记原 3+12 题；旧 R5 及未启动的 12 题 R2 不续跑。固定 family 切分、相似度、评分及 Selector 30 菜单/10 边界和覆盖要求保持不变。必须先看到真实计划、执行及合格角色来源，才能确认此次请求调整改善了运行，并按已有授权开始 StateTune。不能把工程测试或独立数值核验作为 Agent 完成或训练改善。

官方参数依据：[DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)。所有证据路径与 SHA 见 EVIDENCE_SHA256.json；私有保留题集未读取。
