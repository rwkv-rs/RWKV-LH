# 当前状态与交接

产品使用 G1k 13.3B、独立 Decision／Executor State 和按需强 Planner。当前两角色均为 zero。架构见 [ARCHITECTURE](ARCHITECTURE.zh-CN.md)，数据与准入见 [PROJECT_ROLE_DATA_PIPELINE](PROJECT_ROLE_DATA_PIPELINE.zh-CN.md)，额度见 [PROJECT_BUDGETS](PROJECT_BUDGETS.zh-CN.md)。源码公开，测试和原始证据由 owner 单独交接，边界见 [SOURCE_DISTRIBUTION](SOURCE_DISTRIBUTION.zh-CN.md)。

## Agent 基线

**Strict 0/120、completed 0/120、独立功能验收 0/120，实际 mutation 4。** 终止原因：单次输出额度 18、输入容量 1、总调用额度 24、墙钟 71、未确认操作 6；其中 2 次 Native 非有限 State、4 次 SSH 中断。

客户端返回 Decision 182、Executor 5484、Planner 0，共 5666。预算预留 5711，生成开始 5672，账本发布 5634（Decision 182、Executor 5452）；32 次返回未发布，39 次预留未开始，6 次开始后无客户端返回。另有 4 次服务端独有完成结果，分别保留，未补写客户端或账本；其余 2 次仍 unknown。

来源为 `data/experiments/ROUND_01/HARNESS_LEDGER_STREAM_20261006/`：12 道开发项目各 128 调用／1800 秒，108 道相关变种各 64 调用／1200 秒。源码、模型、zero State、参数、评分和分母冻结；相关变种不等于独立用户任务，也不是 Holdout。EX-FULL-02-V02–V05 在 SSH 恢复窗口耗尽后提前结束；仅原先未启动的 V06–V09 按同一冻结条件继续一次。未确认操作未重放，原始成绩、STOPPED 和关闭记录未改写。

逐题输入、输出、工具回执、独立验收和人工复核入口为该目录下的 `REVIEW_REPORT.zh-CN.md`、`MANUAL_JUDGMENTS.json`、`REVIEW_MATERIAL/MANUAL_COVERAGE.json`。部分浏览器功能可用不等于完整交付；核对失败须按原题合同，不能把标签缺失误称为金额计算错误。

## 当前实现与验证

当前 Decision v21、Executor v17、Planner v16、Ledger v13、prompt v8；外层仍为 `function/params`。工具合同、当前协议和 State 身份不兼容时拒绝恢复。编码 CLI、Web 和 batch 使用同一 Project 入口；独立只读及离线 Direct 采集保留明确边界。

边界解码策略 v1 只允许当前方向和授权引用，任务建议／交接／验收 ID 按任务关联；无回执时不提供检索生成分支。静态目录及策略绑定 State，实际 grammar 随生产边界变化并逐次留证，运行、精确 token 重放及角色评测共用。Executor 统一 `report_work(progress/submitted/blocked)`，保留三种状态转移，旧交接入口已删除。评测 plan/run 为 v3；本批没有精简完整 bootstrap 工具目录或测得 token／成绩改善。

无生产消费者的旧调度、Teacher、依赖集成、自动接管和非正式审核队列已移除。CodingJob 定义独立于旧执行器，包导入不装载模型。工具与角色输出共用递归 schema 校验；内存及文件生成记录共用身份、顺序和重复检测。正式审核读取的锁、原始 Native 输入、来源与独立审查回归保留。

账本读取、恢复和离线提取采用一致事务内的完整流式验真；这减少读取内存，但尚未解决每事件保存完整状态的累计成本。生成记账分别核对预留、开始、返回、发布与 pending；未知用量不补零。

本次工具边界清理的完整本地回归、耗时及源码清单一致性记录统一见 `data/experiments/ROUND_01/TOOL_CONTRACT_CLEANUP_20261007/FULL_REGRESSION.result.json`，修复前反例与定向失败保留在同目录。公开源码构建和命令入口检查单列，不代替含 Torch、State 与浏览器的本地回归；定向通过也不代表全量通过。

这些工程改动晚于冻结 Agent 基线；本次没有运行新模型、训练或新增角色数据集，没有测得任务成绩或强模型成本改善。

## 未解决问题与优先级

1. **记录成本与数值故障。** 账本的原始 token／完整状态重复保存；Native 回收队列非空时会扫描完整 State 元数据。已停止服务上的主动扫描测量只能说明函数成本，不能当作每题延迟占比。两次非有限 State 发生在生成结果重新物化后的导出，已核验输入链，失败输出未保存；首个异常 token、张量和数值根因仍未确定。保留有限值检查及 unknown，不重放未知请求。
2. **模型不能稳定利用执行反馈。** 120 题主要偏离标注中 Decision 8、Executor 112；偏离点输入 2321–13025 token，中位数 5441。5666 次客户端返回中，5181 次与同题同 lane 上次输出完全相同（Decision 59、Executor 5122）。这些包含连续重复和相关变种，不是独立因果统计。常见问题是混淆工作／操作／回执 ID、反复读取、无依据提交、代码失败不修复及生成内复读。
3. **Planner 输入容量。** 一次待发送输入估算 36518 token，超过预留输出后的 32735 上限，请求未发送；不能记为 Planner 生成失败。跨角色完整事实传递仍需通用修复，不删证据或静默摘要。
4. **工具收敛、模块职责与架构对照。** 文件菜单 14 项候选尚未实施，须先覆盖精确编辑、追加、二进制摘要及证据片段语义；委派／恢复与校验调度入口也待收敛。强模型传输与旧研究策略拆分、不可变证据存储仍待整改。RWKV 单执行器需要与当前双角色在冻结源码、固定题集、预算和独立验收下比较；当前 Planner 实际返回为 0，不能据此宣称节省强模型成本。

RWKV 采样维持 temperature=0.1、输出 1800／4096；既有温度 0、0.3、1 及输出额度候选未证明通用收益，不能统一推广。固定权重下 HTTP 串行／并发提交结果一致，不证明训练采用 fully async；工具续写调查也不是官方训练工具清单或 Agent 能力证明。诊断细节和候选设计留在本地原始报告，不重复写入维护文档。

## 运行及训练边界

既有 Decision 候选有 32 个实际 optimizer steps，资格评测遇到接口与 engine 错误，没有有效合格结果，未保留为生产 State。旧协议来源和训练身份保持原样，不改标复用。新实验须遵循现有授权及预登记。

权重 `/mnt/nas-model/g1k/rwkv7-g1k-13.3b-20260930-ctx25600.pth`，SHA-256 `31799b3f8207e74c1b47f359184ac1c658c927ff697971447f7bf0fd18ae393f`。基线原 2 个和续接 2 个 Native 服务及 SSH 转发均已关闭核验。中间 State 仅在内存，服务重启后旧句柄不能冒称可恢复。

自然语言入口运行真实 Agent；当前终端执行期间阻塞输入，`/stop` 仅停止预览，Ctrl+C 取消运行，会话历史尚无重开入口。[TUI 方案](TERMINAL_TUI_PLAN.zh-CN.md)未实施。静态／标准 Vite 启动和 `check_project` 已有真实安装、HTTP、Chromium机制验证；不覆盖后端、SSR 或自定义构建目录，也不证明模型能自主交付。检查返回时临时服务已停止。

项目命令仅在 WSL UbuntuRecovered 执行。服务器禁止 Git，部署只接收本地冻结清单及源码。owner 负责 push；已有研发改动不并入清理提交。

## 本地证据入口

以下路径相对于 `data/experiments/ROUND_01/`；各目录保留原始记录和逐文件 SHA。

|用途|入口|
|---|---|
|冻结 Agent 基线及登记|`HARNESS_LEDGER_STREAM_20261006/REGISTRATION_02.json`；SHA `e95888b4dc00b930bd421421f16d3783a07034fc32e48e514002b6f67d264a42`|
|实际调用与重复统计|同目录 `ACCOUNTING_ALL_REAL_TRACE_CHECK.json`、`FINAL_OBSERVED_GENERATION_STATS.json`|
|Native 数值与传输限制|同目录 `REVIEW_MATERIAL/DEFECTS_AND_LIMITS.zh-CN.md`、`CONTACT_TRANSPORT_SERVER_OUTCOMES.json`、两个 `*_NONFINITE_FILE_CAPTURE/FORENSICS.zh-CN.md`|
|存储成本和服务关闭|同目录 `NATIVE_STATE_ROWS_POSTSHUTDOWN_PROFILE.json`、`SHUTDOWN.json`、`CONTINUATION_04_SHUTDOWN.json`|
|预算／采样机制实验|`G1K_RWKV_DECODE_20261004/COMBINED_REPORT.zh-CN.md`|
|工具表达调查|`G1K_TOOL_DISTRIBUTION_20261005/STOP_ONLY_20261006/REPORT.zh-CN.md`、`FINAL_MANIFEST.json`|
|清理审计|`ARCHITECTURE_CLEANUP_AUDIT_20261007/REPORT.zh-CN.md`；SHA `c18ee9c94c6ed6f6c37a78e3f81720787ec5731b7f72d2352db9dd1af4a46bcd`|
|工具菜单审核|`TOOL_SURFACE_AUDIT_20261007/REPORT.zh-CN.md`、`SHA256SUMS`|
|本次工具边界清理、回归与构建|`TOOL_CONTRACT_CLEANUP_20261007/REPORT.zh-CN.md`、`SHA256SUMS`|
