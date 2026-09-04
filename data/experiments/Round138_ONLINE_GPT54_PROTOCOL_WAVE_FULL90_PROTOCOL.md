# Round138 GPT-5.4 在线微任务 + RWKV 波次 Full90 协议

日期：2026-08-22

晋级来源：Round137 canary gate PASS。运行开始后不得修改代码、数据、参数、hidden verifier、
相似度或阈值以改善结果。

## 固定配置

- Suite：固定 RWKV-E2E-90（Basic30 / Medium30 / Hard18 + Long-horizon12）。
- Worker：`rwkv7-g1i-13.3b-20260805-ctx16384`，prompt replay，temperature 0.05。
- Supervisor：OpenAI-compatible GPT-5.4，temperature 0.1，strict directive JSON。
- 架构：online microtask；GPT 无 Harness authority；RWKV 是唯一工具与 Final 主体。
- full tool disclosure（CLI 显式 pin）。
- action wave 6；相同零进展 action 2 次提前 review；protocol rejection wave 2。
- max protocol rejections 12；max directives 64；max transitions 200。
- 6 个隔离 case worker processes；每题独立 workspace/store。
- 输出：`Round138_online_gpt54_protocol_wave_full90_20260822`。
- frozen bubblewrap isolated verifier；hidden acceptance 不进入任何模型或 Supervisor trace。

## 有效性与晋级门槛

- 必须 90/90 有结果、0 running，无基础设施/Verifier 失败。
- Strict TP > 36（R126 official=36）。
- FP <= 24；FN <= 1。
- 5 个 byte-precision cases 5/5。
- Basic / Medium / Hard / Long-horizon 无系统性 completion collapse。
- GPT action count 0；Final byte-exact；无 credential/hidden acceptance 泄漏。

未满足则不替换 R126 canonical baseline。无论通过与否，必须报告 Supervisor calls/tokens、RWKV
requests/actions/rejections、workspace mutation 与重复动作、分层 TP/FP/FN/OTHER，并把错误 acceptance
与拒绝 completion 分开归因。Full90 完成前不生成训练数据。
