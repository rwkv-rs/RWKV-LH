# 本轮证据封存

REPORT.zh-CN.md、评测SUMMARY/TASK_REVIEW、冻结登记和清理汇总可直接阅读。完整6749个文件（输入、原始输出、token、State谱系、工具结果、原始失败、审核中间错误、请求账本、脚本与日志）封存在四个EVIDENCE.tar.gz.partNN中；每块不超过40 MiB，避免单文件超过GitHub限制。SEAL.json登记各块、完整压缩包及逐文件清单的SHA。

在独立空目录中按part00、01、02、03顺序拼接，核对完整包SHA后解压；不要覆盖已有证据。完整包SHA：2f65d7a78747379f66860b20e48e730b67070c0085f183e10791f1c5824b88fb。包内EVIDENCE_MANIFEST.json可逐文件核对。原始文件仍保留在当前本地工作区，不依赖解包才能审核。

冻结runtime/source含owner原有未提交修改，故完整源码副本保留本地、没有绕过owner边界塞入本次提交；包内保留逐文件源码身份清单。基础模型及candidate.pth不进Git，候选本地路径与SHA见报告。所有正式训练数据已经由前一数据阶段独立提交，本包不重复放训练数据。

评测SQLite请求账本只读integrity_check两份均ok。报告SHA见SEAL.json。本轮仅本地提交，不执行push。
