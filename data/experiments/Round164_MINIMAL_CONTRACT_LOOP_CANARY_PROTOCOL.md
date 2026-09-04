# Round164：Minimal Contract Loop 共同根因在线 Canary 协议

日期：2026-08-24

## 目的

验证简化后的唯一主循环：

`Plan -> deterministic batch -> parallel RWKV transaction -> typed evidence -> Review -> Complete/Correct`

本轮不生成训练数据，不读取 hidden acceptance 调整代码，不修改 external checker。强模型仍固定
为 `gpt-5.6-terra` primary、`gpt-5.6-sol` fallback；RWKV g1i-13.3 是唯一工具参数生成者、
工具操作者和 Final 作者。

## 冻结修改

1. contract scheduler 不再构造或验证通用 `SupervisorStageRequest`；持久化 batch 只包含
   batch id/index、graph revision、node ids 和 request digest。旧 SupervisorStage audit 只作
   resume 兼容读取。
2. 强 Reviewer payload 删除 node graph，只接收 immutable request、未决 obligations、latest
   result capsules 和 workspace manifest。
3. correction Planner 只接收完整 unsatisfied obligations、satisfied obligation ids、紧凑
   node id/dependency/scope ledger 和 latest results；不重复发送旧 objective/checks/constraints。
4. 沿用 Round163 的 semantic exception、多视图 evidence、严格 action-artifact binding、稳定
   correction signature、transaction integrity 和 terminal supersession。

基于 Round162 同一审计的静态估算：392 个 batch payload 由 567,575 bytes 降至 100,409
bytes（-82.3%）；102 个 correction graph projection 由 1,199,988 降至 413,016 bytes
（-65.6%）；106 次 strong Reviewer 可删除 1,069,588 bytes node/process data。以上只是
序列化估算，不作为在线质量通过条件。

## 固定数据与选择

来源：`data/datasets/rwkv_e2e_90_v1/`，版本 v1；生成方式和 visible/hidden SHA256 沿用
Round162 `RUN_PROTOCOL.json`，hidden acceptance 仅由 runner 运行后使用。

固定 21 例，覆盖全部共同根因簇而非 task 特判：

`B06 B07 B08 B11 B14 B18 B20 B21 B25 B28 M05 M09 M12 M19 M21 M29 M30 H08 H11 H17 LH06`

- evidence shadow：B06/B08/B14/B20/M21/M30/H08/H17。
- artifact binding：B07/B20/M09/M12/M30/H11/H17。
- semantic compiler/旧 FP：B18/B21/B25/B28/M05/M19/M29/M30/LH06。
- transaction/finalizer runtime：B07/B08/B11/B14/B18/M09/H11。

Round162 同集基线 TP/FP/FN/OTHER=`3/3/9/6`，external pass=`12/21`；logical/physical/
returned GPT=`143/190/133`，GPT total tokens=`915,738`，RWKV actions=`274`。

## 固定运行参数

- suite=`all`，只选择上述 21 ids；case concurrency=4，RWKV atom concurrency=4。
- max transitions=200；tool disclosure=`full`。
- graph patches/reviews/atoms/stagnation=`8/8/48/2`；atom transitions=40。
- plan/review reasoning=`medium/medium`；transport retry=3；semantic repair=2；GPT 请求串行。
- 使用新的空 plan cache 目录；不得命中 Round162 旧计划。
- 输出：`data/experiments/Round164_minimal_contract_loop_canary_20260824/`。

## 预注册通过门

1. 21/21 持久化、running=0、未捕获 runtime=0、权威 terminal=21/21。
2. strict TP>=10、FP=0、FN<=2；external pass>=12，不通过降低 external 质量换取完成率。
3. B11 不得出现 finalizer/unrecovered-failure runtime；B25/M29/LH06 不得错误完成。
4. artifactless action inheritance=0、non-content shadow=0；所有 completed multi-operation
   mutation 都有 mutation-scope post-verification。
5. logical GPT<=100、total tokens<=700,000；同时报告 physical/returned、terra/sol、cache、
   semantic exception、duplicate stop 和每例分布。
6. strong Reviewer payload node/process fields=0；GPT tool calls=0；Final 与 raw RWKV byte-exact。

任一门失败都保留结果并停止晋级，不修改阈值。通过后才另行预注册 Full90。
