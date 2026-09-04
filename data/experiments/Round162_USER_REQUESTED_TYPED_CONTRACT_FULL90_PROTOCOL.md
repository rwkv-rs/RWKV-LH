# Round162：用户明确要求的 Typed Contract Full90 诊断协议

日期：2026-08-23

## 性质

Round161 Stage A 已完整运行 15 例，TP/FP/FN/OTHER=`1/4/1/9`，未通过原预注册晋级门。
用户随后明确要求不要依据局部用例逐项分析或停止，而要运行完整 90 例并从整体寻找共同根因。
因此本轮是**用户明确覆盖 canary 晋级门后的诊断性 Full90**，不是 canonical 晋级测试；
失败结果不得替换 R126，不在运行中改代码或评价口径。

## 固定代码、数据和配置

- 代码与工作树必须与 Round161 正式 canary 的 `RUN_PROTOCOL.json` 记录一致；仅把 plan cache
  切换到新的空目录，防止 15 例预热造成 cache hit 和成本污染。
- Suite：`data/datasets/rwkv_e2e_90_v1/`，runner `--suite all`，固定 90 例
  B30/M30/H18/LH12；case concurrency=4，RWKV atom concurrency=4。
- Supervisor primary=`gpt-5.6-terra`，fallback=`gpt-5.6-sol`，circuit failures=2，
  cooldown=30 秒；validated plan cache 启用但从空目录开始。
- reasoning plan/review=`medium/medium`；transport retry=3；semantic repair=2；
  token limits=`4000/2400`；graph patches/reviews/atoms/stagnation=`8/8/48/2`；
  atom transitions=40；case transitions=200；tool disclosure=`full`。
- GPT 串行；GPT 无工具权和 Final 改写权；RWKV g1i-13.3 是唯一工具操作者/参数生成者/Final 主体。
- 输出：`data/experiments/Round162_typed_contract_full90_20260823/`。

## 固定统计口径

- TP：completed 且 external passed；FP：completed 且 external failed；
  FN：非 completed 且 external passed；OTHER：非 completed 且 external failed。
- 报告 90 例完整性、B/M/H/LH、所有 external checks、terminal reason，以及对 R126、
  Round148、Round158、Round161 的同口径比较。
- 报告 logical/physical/returned GPT、terra/sol 路由、5xx/repair/cache/circuit、prompt/
  completion/reasoning/total tokens、RWKV actions/rejections/overlap。
- 报告 typed assertions 数量/种类/覆盖、local-only reviews、exception GPT reviews、混合 reviews、
  correction signatures、duplicate blocks、latest-state capsule 数量和 terminal completeness。
- 将失败按跨用例共同根因聚类：契约表达、结果可解析性、RWKV 事务执行、纠错状态压缩、
  acceptance/终态、relay/路由。局部 case 只作证据入口，不做特判结论。

## 诊断参考门（不影响本轮是否跑完）

1. 90/90 持久化、running=0、未捕获异常=0。
2. FP<=9、FN<=1；strict TP 与 Round158 的 34 及 R126 的 36 比较。
3. logical GPT<344、total GPT tokens<4,506,270；local review 应显著减少 Reviewer 调用。
4. M04/M08 等旧 FP trap 不得错误 acceptance；所有 local acceptance 必须逐 assertion 可审计。

无论参考门结果如何，本轮必须完整运行 90 例，然后统一分析，不因单例提前停止或改代码。
