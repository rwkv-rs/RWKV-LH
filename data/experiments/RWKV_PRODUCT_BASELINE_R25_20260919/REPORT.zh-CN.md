# R25：真实基线发现分配生命周期缺陷，比较无效

第一任务release-numbers--zero-a--r1读取与回答通过原评分，2次生成、0修改；第二任务创建后generate返回410并按基础设施故障停止，46次未执行。不是RWKV1/2通过率，整组比较INVALID，不能并入后续修复收益。原始输入/输出/token/观察/State及回执已保留，见runs/、FIRST_TASK_REVIEW.json、REQUEST_JOURNAL.sqlite3与COMPARISON_INVALID.json。

首次启动还出现执行环境没有设置模型名，发生于模型调用前；显式将已登记模型名传入systemd后才开始真实运行。没有更换任务、评分、采样或预算。全部推理与Harness执行均在服务器GPU0；engine、源码、模型文件先校验。服务与runner已停止。后续修复及重跑见R26，不能把当前目录当作仍运行。
