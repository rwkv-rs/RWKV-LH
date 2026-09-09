# 2.9B 部署与 Native StateTune 兼容验证

Agent 级：本轮未执行新的 Agent 题集，未产生 Strict、completed、mutation 或终止原因的新成绩。最近完整实测仍是 R7 双臂各 Strict 0/12、completed 0/12、mutation 0，终止 strong_planner_unavailable / fixed_plan_exhausted；不能把部署或数值测试写成能力改善。

角色级：当前 Selector 2.9B 服务已经部署，真实 HTTP 请求两次均完成 read_file 选择；每次完整输入 949 tokens、BOS 1，服务身份与客户端一致。纯数值验证 optimizer steps **0**、角色训练样本 **0**；未新建正式角色数据版本。

## 已完成的工程工作

- 用唯一通用转换器 `scripts/prepare_rwkv_vllm_artifact.py` 替换模型专用转换器。`RWKV7Layout` 从权重与模型配置确定层数、head、FFN、低秩尺寸和 State 形状，不通过模型名称分支兼容。实际权重 1062 个，1059 个用于推理，layer 0 的 3 个未使用 value-mix 张量另存且逐值核对；未更改权重值。
- 从本地 Git 历史提取并复用唯一 Native 数值实现、CUDA 内核和独立梯度 oracle；没有恢复旧角色、旧生成器、旧训练驱动或固定三轮额度。训练模型读取当前配置，去掉原先 13.3B 的低秩尺寸假定；只开放 time_state 梯度。
- Selector 原服务固定 FP16 State / 4096 token，与 Native FP32 State 不一致。现在使用 fp32io16，模型上下文从 artifact 读取并拒绝超限；服务传输身份升级至当前 v2，绑定精度及实际上下文。五个角色协议未因模型适配而改版。
- 训练加载检查完整项目源码、engine 清单、模型、编译源、扩展二进制、工具链、Torch/CUDA ABI、GPU 和实际加载库。服务器全程没有使用 Git。
- 更新本地 `.env.local` 中遗留的 Selector v3、旧模型 SHA 和旧 decoder SHA。旧转换器及其字节码删除；本地配置变更只记录非敏感字段。

## 实际模型与验证

2.9B 原始权重 SHA `966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`；转换后权重 SHA `1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b`。模型 32 层、宽 2560、40×64 heads，低秩尺寸 96/96/64/320，FFN 10240，词表 65536，窗口 16384。便携 State 为 BF16 `[32,40,64,64]`，轴序为 layer/head/value/key；服务加载器仅转置一次为 recurrent key/value，运行 State 为 FP32。

预注册范围为 zero / 非对称非零 State × 1、17、128、16384 tokens；比较每一位置完整词表输出，最大允许绝对误差 **0**。八项全部通过。17、128、16384 tokens 完整反向均通过：32 层 State 梯度非零且有限，底模无梯度或变更，prompt 无直接 loss 梯度，独立样本结果相同。最大记录 allocated 显存 30,441,612,288 bytes（约 28.4 GiB）。这里的 `Head` 是冻结模型原有词表输出层的反向包装，不是外置可训练 Head。

第一次运行的全部数值检查通过，但实际加载的 Triton CUDA 工具库与 msgspec 扩展缺少身份登记，整体记为失败。登记这两个真实文件的 SHA 后，保持模型、源码、指标、阈值不变，第二次重跑全部检查通过，用时 137.90 秒。没有放宽未知库拒绝规则，也没有重评分旧结果。

本地回归 **1073 passed、0 skipped，196.81 秒**，包含 Torch / State 和浏览器。先失败再通过的配置回归记录于 `backend_config_red.log` / `backend_config_green.log`；转换器回归见 `converter_red.log` / `converter_green.log`。首次完整回归暴露两个未更新的测试 fixture，补充实际模型上下文及当前服务身份后整套重跑。

## 部署与适用边界

服务 `rwkv-lh-selector-current.service` 使用 GPU 2，本地通过 SSH 转发访问 `http://127.0.0.1:29621`。GPU 0 的现有 13.3B 服务继续运行。完整项目 manifest SHA `63f481fc95bb953a385f5fc9729ced38c50f15512e02fc7e057c3e54694a4575`（118 文件）；engine manifest SHA `841ac0d6bdd1b0a45660583fc12e385f3cfcd1d3300601a276bc4f60a1471522`。

本轮证明当前 BF16 RWKV7、head size 64、batch 1、已封存 Blackwell CUDA 后端的 2.9B 兼容性。其他几何或数值后端须通过同样的适配验证，不自动复用旧 State。模型名变化不要求重写角色架构。

Controller 闭环代码已在 `b2f74b679259d9ea5512c8e7849d45f0534a1b9d` 提交并通过 1061 项回归；真实 Planner 输出、阶段推进和最终任务成绩仍需当前版本的新生产运行。接下来按已有授权收集 Selector trace，满足当前角色的来源、标签、覆盖、固定回归与预算条件后训练。数据抽取器不等于优化器驱动，本轮恢复的是已验证的训练数值后端，尚未新增正式角色优化器 run。

所有来源、失败尝试、冻结身份、实际输出及 SHA 见本目录 `MANIFEST.json`。关键证据为 `MODEL_MANIFEST.json`、`PROJECT_SOURCE_MANIFEST.json`、`COMPAT_REGISTRATION.json`、`NATIVE_COMPAT_RESULT.json`、`SELECTOR_SMOKE.json`、`DEPENDENCY_ADMISSION.json` 和 `full_verified.log`。
