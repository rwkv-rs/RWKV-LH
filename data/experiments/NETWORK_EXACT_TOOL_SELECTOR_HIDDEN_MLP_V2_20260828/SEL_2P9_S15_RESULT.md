# NET-SEL-2P9-S15 结果

日期：2026-08-28  
状态：拒绝接入

## 实验问题

验证 S2 学得 state 能否同时作用于 compact query 与静态 tool description，再由共享 description-conditioned MLP 完成 25 路选择。所有输入、训练参数、阈值与 S15 预注册一致。

## 固定产物

- query feature manifest SHA256：`aba6c9701945aa31bfb31bb53f32fad588176a2d2df7cd5a936a3bb5481fa309`
- tool feature manifest SHA256：`dc849b030dd9401add88e6bb8a9e3fe0de34baf891a5a930706b21fecea6e181`
- head SHA256：`d219acdef07fab183391e1cff0b46ecbc81ec74a281d9bbec1ec721dc2095904`
- 完整指标：`run_s15_description_state_head/TRAINING_REPORT.json`

## 结果

- 25 路 test accuracy：`0.2960000`
- macro-F1：`0.2552332`
- boundary accuracy：`0.2666667`
- natural dev：`99/176 = 0.5625`
- ordinary web：`0/16`
- privacy local-first：`8/48`
- test 上 `read_file`、`web_search`、`connector_lookup` recall 均为 `0`
- RWKV 文本生成调用：`0`；sampling 调用：`0`

所有预注册质量门均失败，因此未读取外部 ECRA，未进入在线流程。

## 根因与结论

S2 state 是按旧的生成式标签协议训练的。把它同时注入任务和静态工具锚点，会把两类表示都搬离 S8 已验证的共享语义坐标系；这不是可复用的“全局 selector state”。S15 不得接入，也不得用后处理掩盖其原始分数。

