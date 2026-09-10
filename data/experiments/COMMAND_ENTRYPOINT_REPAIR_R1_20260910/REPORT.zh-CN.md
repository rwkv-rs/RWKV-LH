# COMMAND_ENTRYPOINT_REPAIR_R1_20260910

最近完整 Agent 观测保持原成绩：REALPROJECT 官方 R3 **Strict 0/12、completed 0/12、mutation 0、动作 43**；UltraData 官方 R6 **Strict 0/3、completed 0/3、mutation 3、动作 6**。本工程轮没有重评分、没有新 Agent 运行，optimizer steps **0**。原 WEB-02 的终止原因仍记为重复失败预算耗尽。

## 根因与修复

`ActionHarness._run_command()` 将项目 venv/bin 中找到的所有可执行文件都包装成 `python executable ...`。Python 二进制、其他原生程序、Shell 脚本均不满足这个假设；即使是 Python console script，原实现也丢失 shebang 的解释器参数。WEB-02 中合法 `python3 -c ...` 被解释为读取 ELF 二进制，产生空字节语法错误，这是 Harness 缺陷。

当前实现先解析实际可执行路径，只在 shebang 明确绑定当前 Python 解释器时包装 Python 脚本，并保留其解释器参数；其他项目可执行程序直接执行。项目绝对入口和符号链接使用相同的身份判断。沙箱映射项目可执行路径并提供对应运行时、只读依赖与 PATH；`check_command` / `run_command` 共用这一实现。没有增加 python3、模型名或题目路径的特判，也没有改变角色、协议、评分或停止规则。

## 验证

当前 18 项行为回归在 Git 的修复前 Harness 上验证为 **14 failed、4 passed**，旧源码仅在内存加载，没有保存旧实现副本。修复后入口和隔离专项共 **25 passed**；全套 **1432 passed、0 skipped、227.48 秒**，包含必需 Torch / State 与浏览器验证。

最早的测试草稿错误假设项目安装了 pydantic，已改用 pyproject 声明的 requests，并用修正后的同一测试重新核实修复前失败；原始两次日志均保留，最终采用 `RED_PYTEST_CORRECTED_FIXTURE.log` 和 `TARGETED_PYTEST_FINAL.log`。未降低断言。

将 WEB-02 原始动作参数原样交给当前生产 Harness，在独立工作区的真实 bubblewrap 中执行：修复前 failed，修复后退出码 **0**、输出 `python3 3 13 11`。此为工程复验，不是 Agent 重评分或角色训练样本。见 `PUBLIC_COMMAND_PROBE.json`。

修复发生在 WSL 本地 Agent 命令执行层。推理服务器继续使用已核验的 e7c455b6 上传源码及原 manifest 身份；本轮未修改服务器文件或冒称新部署。此前数值边界与模型兼容证据保持各自冻结身份，新 Agent/训练运行仍须登记其实际客户端源码与服务端身份。

## 单独保留的 Native 未确认请求

CLI-02 的 Native create 请求 `NR-912a82290ad4bd0a7059d08b43c4f01cd23840e446a94126df0248801910009d` 在原服务日志中查询回执得到 404，本次只读复查仍为 404。原模型 trace 没有该请求的详细传输事件，因果日志只有最终 unknown 异常；当前 `_native_request()` 的异常处理未保留最初失败原因。因此尚不能确认具体连接错误、服务端是否曾接收请求或无记录的原因。没有重放该请求，也没有把 unknown 改成成功或未执行；此项仍未解决。

同一服务时间窗还含更早的 State 不存在日志，没有相同请求身份，不能强行绑定为此请求的根因。最初系统 journal 查询无权限，改用服务实际所属的 user journal 后取得日志，没有提权写入或服务器 Git。

## StateTune 后续

3+12 题合并的 81 条自动 Selector 标签已达到登记覆盖并有三个非空切分，仍存在 113 对跨切分相似度超限及 126 条待复核。候选未冻结为正式数据集。Owner 已授权训练；尚待答复的是纠错标签是否允许两次独立官方 DeepSeek 离线复核替代当前双人人工要求。未获得该变更答复前，不冒充人工签名，不修改相似度门槛或旧轮评分。

各文件、测试日志、原始工程探针、辅助脚本与源码的 SHA-256 见 `EVIDENCE_SHA256.json`。代码和证据本地提交，由 owner push。
