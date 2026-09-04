# INVALID：运行期间 checker 语义修正

日期：2026-08-23

本目录不计分，也不得用于 Round161 门槛、架构消融或训练正样本。

原因：首个活动用例 E2E-B10 的在线 typed assertion 显示
`command_succeeded.expected="0"`。运行代码原先只把 `expected` 解释为 operation 名，未把
`"0"` 解释为成功退出码。该通用 schema/checker 语义在其余用例仍排队时被修正，导致本目录
可能包含修正前后不同代码进程。主 runner 随即通过 SIGINT/SIGTERM 终止，目录原样改名保留。

处置：新增退出码 0 的确定性解释和失败 command 的 contradicted 证据，完整回归通过后，从
新的空输出目录重新执行预注册 Stage A。此目录没有正式结果解释。
