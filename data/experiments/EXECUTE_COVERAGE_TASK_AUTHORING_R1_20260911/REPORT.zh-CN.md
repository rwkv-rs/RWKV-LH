# 轮次 A 任务定稿与执行入口

作者验证本身不产生 Agent 成绩；后续轮次A为Strict 0/4、completed 0/4、mutation 0，取得真实execute来源而非开发完成。此前命令采集未取得成功命令覆盖，不能据单元测试声称项目已具备自主建项目并完成交付的能力。轮次 A 已完成并按采集主判据KEEP，成绩以该轮封存结果为准；本作者验证不训练，optimizer steps=0。

用户指定 162e60ee、c6b46d01 已 push，远端 chase/rwkv-goal-loop-v2-cleanup 到 c6b46d0185b4b5c8e6df358128b20ad46d0776ad。冻结源码完整回归1464 passed；定稿后隔离工作区全套1464 passed，见PYTEST_ISOLATED_CORRECT_ROOT.log；另有环境失败记录TEST_ENVIRONMENT_FAILURES.json。

NEW-DIAG-01 是缓存TTL到期边界修复；NEW-DIAG-02 是保留先见顺序的库存增减聚合修复。两题均预置可运行模块、4个公开测试、恰好1个真实失败；要求先运行 python run_tests.py 定位，再修复并产生退出0的 TEST_REPORT.md。参考实现与私有探针均不进入 Agent workspace。原 RP-CLI-01 / RP-WEB-02 任务对象与验收对象保持完全一致。

使用既有 benchmark SuiteDefinition / SUITES / load_suite 注册四题；原 freeze_project_benchmark 命令固定12个RP任务，不能无改动地注册此四题套件，因此通过现有运行器注册API及独立MANIFEST冻结。未修改 rwkv_lh/、scripts/、tests/，没有角色协议重写或题目工具特判。audit_binding.py 仅在私有验收前把真实 action_finished 事件绑定到本次作者探针，随后调用原隔离验收器；在首次生成前与任务、验收一并SHA冻结，不影响生成或角色数据。

V3作者验证共15变体：2参考通过，13非参考拒绝，包括未运行伪造报告、语义错误、改公开测试、嵌套conftest、报告篡改。运行使用真实Harness命令及隔离只读workspace验收。作者事件只是来自这些作者进程的验证夹具，绝不充当生产trace训练来源。AI reviewer one复核证据后接受有限声明下采集，未独立重跑。

限制：最终tests/helper SHA及真实stdout精确匹配不构成每个中间时刻不可篡改证明；临时改helper/tests再恢复的历史尚无独立文件身份attestation。本轮Strict不能扩称恶意项目全历史防篡改安全通过。保留初审、V1/V2和V3记录，不以失败变体重新计分掩盖验收演变；正式采集只使用定稿V3。

轮次 A 固定四题、Executor1800、并发1、每题1800s、总7200s、200 transitions、native resume1、pending resume0。524次公开跨题比较无>=0.95重叠；所有四题按既有哈希切分落train，未重命名家族。原角色覆盖scope字节保持不变，最新owner授权扩展任务成员，训练30行/10独立边界等门不减。KEEP需要成功命令绑定execute及无waiver新提取execute>=1；真实tmp-overlay/timeout只在被实际触发时报告。

独立freeze集成复核发现162e60ee仍有筛选前valid、筛选后regression成员和coverage不一致三个缺口，详见 FREEZE_INTEGRATION_REVIEW_TWO.json。它们不阻塞本轮生产采集，但后续不能绕过这些门启动训练；修复不得混入轮次A源码。
