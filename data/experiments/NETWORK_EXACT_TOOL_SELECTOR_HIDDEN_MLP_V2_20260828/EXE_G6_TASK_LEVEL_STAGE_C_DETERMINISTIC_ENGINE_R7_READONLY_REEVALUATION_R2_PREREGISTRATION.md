# EXE-G6 deterministic engine R7 只读复核 R2 预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在 R2 裁决程序与结果之前冻结；模型请求固定为 0。

## 唯一问题

R1 只读复核结果 SHA-256 为
`c2963bfd86338fd3e688b4ce71ba1eb90f5792e9a1d8bbd8bfc32f1cca8c55b7`。它独立重验后得到：

- 原 R7 的十一个固定门禁全部为 true，包括修正键名后的 extension runtime-map 门禁；
- 八项附加审计中七项为 true；
- 唯一 false 是 `original_r7_report_shape_proves_single_wiring_failure`。

R1 runner SHA-256 为
`bd45459a136afa13f21ebdeb4ded260cd743e30aeb5812faeb1176c10c64e559`。冻结源代码在该审计项中错误要求
`len(r7.get("gates", {})) == 10`；原 R7 实际有十一个门禁，其中 runtime-map 一项 false，另外十项 true。
因此 R1 是附加审计计数接线错误，不是 R7 推理、raw 完整性、性能或质量失败。

## 固定方法与通过条件

R2 不重复推理，不修改任何 R7/R1 文件，不改变指标或阈值。只读取并冻结校验原 R7 结果、R1 协议、R1
execution freeze、R1 runner 和 R1 结果，然后验证：

1. 原 R7 结果 SHA-256 仍为
   `f83470cb85f0f1c0339e727bdf7188ccb49861308a9c59e433f78fe093ff6144`，门禁总数恰为 11，且只有
   `candidate_extension_mapped_in_all_services` 为 false。
2. R1 结果的十一个重算门禁全部为 true；八项 audit gate 只有
   `original_r7_report_shape_proves_single_wiring_failure` 为 false。
3. R1 报告保存的四组 raw integrity 全为 `valid`，G3/G6 三路 raw/token/finish/canonical 比较均为
   72/72，raw 未修改，模型请求和阈值改动均为 0。
4. R1 冻结源确实同时包含错误断言 `len(...) == 10`；R2 固定校正为 11，不允许其他重解释。
5. R1 已保存的 corrected PID 三组都为非空正整数；remote identity before/after/current exact 和产品
   18070/GPU0 gate 均为 true。R2 额外只读确认当前 18070 健康、物理 GPU0 UUID 不变。

全部满足时状态固定为
`deterministic_engine_r7_gate_passed_after_readonly_wiring_correction_r2`，且
`eligible_for_quality_ablation=true`。R1 失败结果和原 R7 失败报告都继续作为不可覆盖的审计记录保留。
