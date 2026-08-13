# Round9 结构变更

- Phase A intent/operator 选择不变。
- 每个 intent 分别获得一个只含 `bind_criterion_assertion` 的动态 G1i tool contract。
- Phase B 只填写 actual/expected arguments 与 transforms；criterion/subject/producer/comparison/operator 复用同一
  RWKV 的 Phase A 决定。
- 标准 G1i 透明外壳归一、wrong name/unknown fields、参数合同与 proof 全部 fail-closed。
- 任一 claim 失败时不执行部分 proof；raw call、normalization/error、tool definition 完整持久化。

未增加按工具名猜 arguments 的 parser 分支，未修改 RWKV 输出或证据语义。
