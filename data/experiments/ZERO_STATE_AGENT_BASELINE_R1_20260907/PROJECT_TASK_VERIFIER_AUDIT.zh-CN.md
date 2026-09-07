# 公开项目任务验证器只读审计

日期：2026-09-07。范围仅为 `benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1/tasks.json` 与 `benchmarks/rwkv_e2e/rwkv_agent_v1/tasks.json` 的可见 `workspace_files` 中 `verify_project.py` / `verify_app.py`。未读取 acceptance、confirmation、Holdout 或封存材料；未运行、修改题集或验证器。本报告不推断隐藏评分器的覆盖。

Agent 级：未运行评测，因此无新增 Strict / completed / mutation / 终止原因数字。本报告只评估公开验证器能够支持的能力结论。

## 结论

这 10 + 1 道题包含真实文件修改、Python 函数执行、CLI 子进程、JSON 持久化和 JavaScript 纯函数检查，适合作为固定开发回归与最初闭环基线。它们不足以证明开放项目交付、完整网页可用性、后端服务或长程 Agent 能力。四道 Web 题都没有启动浏览器；Node 验证显式设置 `global.document=undefined`，绕过 DOM 和用户交互。

固定 API 名称和文件位置可作为公开接口合同，不能单独判为缺陷；问题是用 CSS 字符数、源码关键词、DOM id、URL 前缀等代理指标推断行为和质量，以及公开测试样例范围很小。通过这些检查并不证明相应界面已经可操作；反之，功能等价但组织不同的实现可能被固定文件/API 检查拒绝。

## 逐题范围与局限

| 任务 | 确实检查的行为 | 粗糙指标或缺口 |
|---|---|---|
| AGENT-LADDER-L1-FIX01 | 4 组折扣/舍入输入，5 组非法输入，返回 float | README 只检查单词与命令；没有大规模输入、非有限数等覆盖，不能证明全面数值健壮性 |
| AGENT-LADDER-L1-DATA01 | 对给定 transactions 文件重算当前月总额与分类，精确比较 summary JSON | 只验成品数据，不验可复用处理程序；没有新输入、坏数据或重复执行测试 |
| AGENT-LADDER-L2-CLI01 | 真实 CLI add/list/remove；缺文件初始化、标签过滤、JSON 持久化 | 只有少量预置条目；不验删除后再次新增时 ID 是否冲突、损坏数据库、并发写等 |
| AGENT-LADDER-L2-REPAIR01 | 库存扣减/释放、重启读取、余额不足异常不修改持久化字节 | 验证有实际价值；只验单进程特定异常，不覆盖并发预订、进程崩溃或磁盘写失败的原子性 |
| AGENT-LADDER-L3-WEB01 | Node 中搜索/分类、不可变编辑、导入导出纯函数 | CSS >= 900 字符及关键词；静态 id/asset；不验搜索控件、编辑对话框、真实导入下载、localStorage 刷新恢复 |
| AGENT-LADDER-L3-QUEUE01 | FIFO、失败重排到队尾、次数耗尽、ack、重新实例化读取持久化状态 | 不验多消费者互斥、领取后进程死亡的 reclaim、并发、实际 worker 执行 |
| AGENT-LADDER-L4-LEDGER01 | Node 中月汇总、mock localStorage round trip、纯函数增删 | CSS >= 1200 字符、关键字、label 数量不能证明视觉/可访问性；未执行 UI 事件或刷新；JSON.stringify 等式还约束对象键顺序 |
| AGENT-LADDER-L4-TRACKER01 | 真实 CLI create/list/stats，状态筛选、导入导出及优先级负例 | CLI close/export/import 未逐个调用；导入往返主要比较统计，未比每个字段；无服务端、权限或并发 |
| AGENT-LADDER-L5-PACKAGING01 | pyproject 元数据、直接导入 greet 函数、空字符串负例 | sys.path 手动加入 src，不实际 build wheel、安装、调用安装后的 console script；官方来源只验 URL 字符串 |
| AGENT-LADDER-L5-RWKV01 | 至少 3 条资源、两个分类、URL 唯一、Node 搜索/分类 API | URL 仅限定 BlinkDL 前缀、summary >= 20 字符，不验链接可用性或事实真实性；分类断言允许空结果；CSS >= 900 字符；无浏览器 |
| AGENT-V1-WEB01 | 与 L4-LEDGER01 接近的月汇总/mock storage/增删测试，增加静态 form/button 检查 | 根目录普通文件必须恰好 5 个；CSS >= 1200 字符；addEventListener 仅为源码 token；无真实 DOM/事件/刷新；与另一道账本题高度重复 |

其中 RWKV 分类测试只断言筛选结果没有其他分类，不要求返回已知同类条目，因此错误地对分类一律返回空数组也可通过此公开断言。这里是对验证代码逻辑的静态判断，没有制作规避实现或运行评分。

## 未被这些公开验证器证明的能力

- 浏览器：用户实际点击/输入/提交、渲染后 DOM、焦点和键盘操作、真实表单校验、文件导入下载、刷新后数据恢复、资源请求错误、移动视口视觉效果。
- 后端：HTTP 服务生命周期、真实路由/API、数据库迁移和事务、认证授权、多用户隔离、并发、错误响应、安全边界。库存/队列的本地 Python 类不等同这些能力。
- 项目交付：真实依赖安装、构建、安装后运行、跨模块持续集成、大仓库定位与修改。固定目录/API 是小项目接口回归。
- 长程：多次用户需求变更、跨阶段计划延续、长上下文干扰、进程中断恢复、多轮使用后的回归。题号 L1—L5 不能替代这些实测。队列重新实例化测试仅证明被开发软件的部分持久化行为，不证明 Agent 自身 State 的长程保持能力。
- 泛化：同一公开固定输入可以用于开发诊断，但不能直接支撑未见项目上的泛化结论。L4 账本与 V1 账本有明显同类重复，不能视为两个独立项目族来跨 train/dev/confirmation 切分。

## 对当前 baseline 的意义

可以保持冻结题集不变跑双零，结果准确称为“现有 10 + 1 小项目/接口回归”。若目标是全面项目能力，应先独立预注册更符合目标的行为评测，再冻结版本跑两臂。不得在见到此次候选结果后改公开验证器、隐藏评分、阈值再重打分。上面的局限不能用训练 State 或额外模型调用掩盖。

## 可复核来源

提取脚本：`temp/audit_project_visible_verifiers_r1_20260907.py`，仅打印两份授权 tasks 文件里的公开验证器。

| 任务 | 公开验证器文本 SHA-256 |
|---|---|
| AGENT-LADDER-L1-FIX01 | `3da7c7f94a1b5e6afa9ef1e457e9cb8a967a5f93d270cef560a1a8247f5b9301` |
| AGENT-LADDER-L1-DATA01 | `1e6e7d6d52b1f5017629ac07e0748de1e2622650bffb79b72ecfc694d5d37eef` |
| AGENT-LADDER-L2-CLI01 | `9b27bff1d23c4e11937f77bedb96831c4661ea98498bf688a50bb63a9b601a50` |
| AGENT-LADDER-L2-REPAIR01 | `84117cf81e0a1779d28c04638eac658cf360c3f3be74eaf60fcb37bab4054239` |
| AGENT-LADDER-L3-WEB01 | `321e8a37392de382aca48a475acb538673720aa59445783cb53a441b8adb4aac` |
| AGENT-LADDER-L3-QUEUE01 | `cde520fce35d5983c579a5c09b238fde90fd641c291a25df76a2dc96a45213f8` |
| AGENT-LADDER-L4-LEDGER01 | `fa0c9f40b5bbe4e320d05107b11d62356ca123e6b1fda4ff611549c7f5c2625e` |
| AGENT-LADDER-L4-TRACKER01 | `a376229b40dd1aec71cef9cf92405c3c685f1526c6faf8b373fefff7c73df181` |
| AGENT-LADDER-L5-PACKAGING01 | `117bdb2c77df253ce82277e14a712c5deb02abc31c46b346bf7524ed55c5af76` |
| AGENT-LADDER-L5-RWKV01 | `772ebc9651bb0546243eba936a95734b5c755eaee6d4ae8b03da6ebd2c502b69` |
| AGENT-V1-WEB01 | `5b2c0a47141156fa8d68a6ada834152c90dd14a876065fdf9429ba593c604ee3` |
