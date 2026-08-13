# Round31 E2E-B02 逐链路因果分析

## 结果

- External PASS、Agent BLOCKED、Strict FAIL：1 个假阴性，0 个假阳性。
- 请求 15、Task 3、Attempt 3。T1 read、T2 write、T3 read-back 均真实执行。
- Round31 compact JSON commit 成功解析；optional reason 和 causal dependency catalog 均未造成异常。

## 链路

1. T1 读取正确。RWKV 仍错误选择 GC1+GC2，并用 M-T1 同时绑定两者；Controller 没有改动选择，生成两条 evidence。
   这是明确的模型语义误判，当前样本因最终产物正确而未形成外部 FP，但必须在完整集统计风险。
2. T2 写入正确 JSON。RWKV 选择 GC2+GC3，但在 compact commit 主动返回 `replan/[]`；Controller 原样保留，没有用
   external 结果覆盖。
3. missing GC3 触发 Goal obligation。RWKV 成功产生最小 Task batch，新增 T3 verification Task。
4. T3 选择 `read_json` 并真实读到 Orion/14。确定性 action/file checks 通过。
5. T3 Task commit 返回 replan：模型认为当前 read-back 与 T2 writer snapshot 是同一产物，没有独立地校验由 input 推导出的期望值。
   这是 RWKV 的谨慎语义决定，不应由规则翻成 pass。
6. failure analysis 继续选择 replan，理由一致。
7. replan 第一次输出当前 T3 的旧 rich Task 对象；第二次输出 `task-batch.v1` 外壳，但 Task 仍含 task_id、action、criteria、
   operation、completion_criteria 等旧字段。两次均 fail closed，run blocked。

## 放大器

replan prompt 的 `FAILED TASK AND OBSERVED FAILURE` 包含完整旧 Task、完整 Attempt、完整 ValidationResult；`CURRENT CONTEXT`
又包含同一 rich ACTIVE TASK；第二次 correction 再注入最多 6000 字符的错误 rich 输出。虽然指令要求五字段 Task，输入示例的旧结构
在 token 数和重复次数上占主导，弱模型复制了输入结构。

这说明单一 Task batch 已成为输出协议，但旧内部结构仍泄漏到模型边界。修复应压缩输入投影；不得把 rich 输出事后裁成五字段，
因为那会删除模型明确输出的 action/criteria 等语义。
