# R17：全量 RL 教师纠错已启动

## 任务级状态

Owner 授权的 1024 个独立 RL 来源全部冻结入队，另 5 条 SFT 不计入。启动快照为 2 执行中、1022 待处理，尚无本轮完成/产物通过结果；不是项目 Strict。原 8 个通过产物先重验保留，不制造教师修复收益。最终逐题区分原产物通过、教师修改后通过、失败、中断；通过私有产物测试之后仍需语义审核和训练边界审查，当前训练准入 0。

两条真实轨迹均自主 read_file(TASK.md)，真实工具观察已保存，随后开始第二次生成。首轮输入分别 2872/2871 token，输出各 38 token（其中思考 23）；服务返回精确 token IDs，数量与 usage 一致。原始输入、响应、工具观察及工作区快照在服务器逐题 execution 下，不用摘要替代原件。

## 部署与运行

模型为 Qwen/Qwen3.8-27B BF16，revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，18 分片完整 SHA 校验。GPU 0＋3、TP2、262144 上下文、并发 2，API `http://127.0.0.1:18244/v1`。引擎为冻结 vLLM 0.29.0；没有执行远端 Git。模型身份见 MODEL_MANIFEST.json，服务身份见 LAUNCH_IDENTITY.json、SERVED_MODEL.json。

后台 unit：`rwkv-lh-teacher-1024-r17.service`。
服务器执行目录：`/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916/`。
查看 `outputs/STATUS.json`、`outputs/worker0.json`、`outputs/worker1.json`；逐题结果为 `outputs/runs/<ID>/DELIVERY.json`，完整轨迹在同目录 execution。

该服务独立于本地终端运行，处理至 1024 条完成、基础设施故障、磁盘低于 64 GiB 保留门或人工停止。每题 24 调用/1800 秒、单次 16384 输出 token。SQLite 原子认领、工作区独立；任务预算失败保留并继续，基础设施错误停止新派发。重启遇到未决 running 明确阻塞，不盲目重复执行。不能保证每题修复成功，也未承诺固定完工时间。

旧20题消费者在等待模型阶段停止，零真实生成；其原20边界放入全量队列前20，不重复计数。R16 历史结果保持 13 尝试/11 提交/8 修改/0 产物通过，不按新设置重评分。

## 工程变化与验证

唯一教师输入构造函数保留目标、工具、来源候选和教师自己的完整执行观察，删去模型输入中的冗余审计封装；原件仍保留。按真实教师 tokenizer 检查上下文预算，空内容且思考耗尽分类为任务预算中断。均有先失败后通过回归，日志见 *_RED.txt 和 GREEN_FINAL.txt。

完整回归：1894 passed、0 skipped，330.78 秒。生产工具执行与协议不由教师辅助代码替代。来源恢复分别遵守 R10 的 R12 sealed 索引和 R13 retirement manifest，全 1024 来源文件及工作区身份核验。

本轮同时改变模型、输入与部署预算，后续结果不能用于宣称单一因素收益。教师采用 fresh session，从真实来源快照开始，不宣称与 RWKV 相同输入，不直接导入 StateTune。未启动训练、未创建 datasets 版本、未 push，owner 五处原有修改保留。

## 冻结身份

全量源码与材料 manifest SHA-256：`c0975b59f4da3d73a69773276fe55d5eb0a1c1aae45e6224229dda24467f0773`。
模型 manifest SHA-256：`50f9ad4004ad55a8e40eaacd1d638b407ceb7902eba0673a9809c6b88eeda2f0`。
证据逐文件 SHA 见 EVIDENCE_SHA256.json；实时启动证据见 BULK_LIVE_SNAPSHOT.json。
