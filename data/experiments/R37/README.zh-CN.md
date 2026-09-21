# R37：入口修复与真实 API 管线首批

Agent 级：本轮没有恢复旧评测，Strict、completed、mutation 没有新增可报告值；没有启动训练，也没有重复 zero 基线。

管线级：3 个实际输入边界、5 次 DeepSeek 请求；2 个读取候选通过审核和真实 Harness 执行，1 个 check_command 因初始任务包未开放命令验证而拒绝。估算费用 USD 0.0131244，按官方峰值、全部输入缓存未命中计价，不是供应商最终账单。首批只有 timebook 一个家族，入训数 0。

读取候选经本代理复核：第一个边界按原任务读取 timebook.py；第三个原始生成边界在已经读源码之后读取现有 test_timestamp_offset.py。两个参数与原始文件清单和任务一致，执行成功且文件树未变。审核结果是单人审核，不能称为两个独立审核者。该批生成发生在最后增加生成器代码身份登记之前，只用于诊断；当前导出入口会拒绝未登记生成器身份的包，不补造历史身份。

入口问题：安装入口与批量文档不一致；单题和只读入口先校验环境模型，后应用显式 CLI 模型参数。修复统一配置构建顺序，统一入口同时接受单题与批量；空任务批次拒绝。12 个生产/采集/训练相关 CLI 的 --help 均可运行。

代码补齐：batch、export、freeze；读取/搜索/列目录实际执行；最终回答绑定具名审核和祖先工具执行证据；冻结时再验证，读取证明纳入训练准入；重复生产边界拒绝；公开保护路径与只读约束在冻结时再次核验；任务包绑定生成器 SHA，代码变化时禁止继续付费生成。

首批暴露的公开命令约定缺口已经处理：在封存快照副本运行既有 unittest，观察到 exit=1 和 FAILED，再准备另一个未使用边界 NEXT_BATCH.json。没有重试旧生成或改写拒绝结果；新任务包尚未额外调用 API。

从远端只读取回真实 COLLECTION_IDENTITY、PROJECT_SOURCE、MODEL_SOURCE_PREFLIGHT、REGISTRATION。PROJECT_SOURCE 的实际 SHA 与登记值一致，模型 SHA 与本地源一致；预检记录显示 passed 和 remote_git_used=false。未在服务器调用 Git，没有下载旧实验或模型副本。记录在 data/pipeline/r37/source-attestation/。

完整数据集仍需要更多经过来源审计的家族、固定回归隔离和预登记覆盖。管线的冻结入口会继续执行这些门槛；目前不声称“已有可直接开训的数据”或“Agent 已改善”。

验证结果、源文件 SHA 和本轮产物 SHA 见 RESULT.json、VALIDATION.json、EVIDENCE_SHA256.json；完整日志 FULL_FINAL.log。首次回归的 7 处失败都是入口测试替换旧配置函数，更新到新构建入口后重跑完整回归，保留 FIRST_FULL.log 供核对。
