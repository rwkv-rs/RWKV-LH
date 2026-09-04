# EXE-G9 稳定 schema 对比修复预登记

登记时间：2026-08-29。登记发生在 G9 数据生成、训练、checkpoint 推理之前；G8 已按冻结
协议完整结束，结果为 `no_candidate_passed`。

## 已知证据与根因

- G8 ablation：`a4c3f57e807dd9e2f6adfea7dbb1436c5e99d0e98bbcb62883dce6f656a1b9b2`；
- G8 failure analysis：`51ba6667061d497d1f577fc7e2085a13deecebaf6a59725f7e372b8f79bff999`；
- G8 的 G6-dev 八 checkpoint oracle 仅 `466/480`，低于固定门槛 `467`；稳定失败 14 条；
- G8 holdout oracle 为 `231/240`，稳定失败 9 条；
- 稳定失败集中于两种极相似台账工作流的 position-2 `write_json` schema、position-7
  exact final，以及少量 discount `read_json/write_file`、implementation manifest 与 direct
  `web_search` query；后期 G8 还固定回归一条 network recovery；
- 因此根因不是 checkpoint 路由，而是宽泛整轨迹 replay 对已正确行产生扰动，同时关键位置的
  对比密度不足。不得用多 state 事后拼接、用例路由或 Parser 修复规避这一结论。

## G9 数据协议（train=2000）

只使用冻结 G4 deterministic generator 的全新 `train` identity，以及冻结 G4/G6 **训练集**
锚点。G4/G6 dev、G8 holdout 的 prompt、target、token、数值和 identity 均不得复制、改写或
进入训练；它们只提供上面的聚合失败类别。

固定构成：

1. `960`：fresh `failed_check_dual_output_recovery` position 2 `write_json`；
2. `160`：fresh recovery position 7 exact final；
3. `160`：fresh `discount_ledger_release` position 7 exact final；
4. `80`：fresh discount position 5 `write_file`；
5. `80`：fresh discount position 2 `read_json`；
6. `80`：fresh `implementation_bundle` position 5 `write_json` manifest；
7. `240`：G4 train 的 24 operation balanced direct anchor，各 10 条；
8. `120`：G6 train clean-network anchor，固定 operation quota；
9. `120`：G6 train rejection-recovery anchor；包含该训练面全部 20 条 `append_file`，并保留
   其余 11 operation。

数据必须：target suffix mask、literal `current_requirement` 为续写前最后字段、无 target
截断、最大长度 `<=2496`、exact prompt duplicate=0、train/eval source identity overlap=0、
generated RWKV text=false、raw output modified=false。与 live V1/V2 用户请求使用预登记
byte-5-gram cosine，最大相似度必须 `<0.75`。

## 训练协议

- base model：13.3B G1i，SHA-256
  `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`；
- parent：干净的 G6 step-1500 training state，SHA-256
  `648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78`；不继承 G8；
- physical GPU0；BF16；FLA；`ctx_len=2496`；shuffle=1；seed=1091；
- `epoch_steps=2000`，save every 250；warmup=40；Adam beta1=0.9、beta2=0.99、eps=1e-8；
- cosine LR `5e-7 -> 5e-8`。这是 G8 初始 LR 的 1/4，固定用于降低正确行回归；运行后不得调整；
- 必须自然完成，不允许 early-stop、挑 loss 或覆盖 checkpoint；全部 8 个 checkpoint 都验证
  61 个 BF16 tensor、训练态/vLLM 态一致性与 parent delta。

## 固定消融与门槛

复用同一冻结 G4-dev480、G6-dev480、G8-holdout240、采样、解析、canonical 相似度算法及
raw-first journal。每 checkpoint 共 1200 行、concurrency=8、hidden retry=0、postprocess=false。

门槛不因 G8 失败而降低：

1. 全 surface transport/envelope/schema/operation 完整；
2. G4 canonical `>=453/480`，且 critical operations 不低于 G6 parent；
3. G6 canonical `>=467/480`；retention `>=323/336`；clean `72/72`；recovery `72/72`；
4. 相对 G6 parent：retention 净增益为正、network 144 行回归数=0；
5. G8 holdout canonical `>=231/240`；discount `>=45/48`；recovery `>=45/48`；其他 family
   各 `>=46/48`；
6. 全部 raw/integrity/profile/GPU0 证据有效，产品 18070 全程保留。

选择满足全部门槛的**最早** checkpoint；若无候选则 G9 不激活，不进入 Stage B/C，不修改
`.env.local` 正式路由。只有胜出后才继续 S60 + live V1/V2 + retrieval9、最少 state 引擎和
Agent V1 项目能力矩阵。

