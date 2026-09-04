# RWKV-LH 三阶段 state tuning 最终报告

日期：2026-08-27

## 最终结论

三阶段训练、部署和冻结评价均已按协议完成。Stage1 是唯一通过稳定性要求的可部署版本；
Stage2 和 Stage3 的训练与部署在数值上有效，但行为门失败，未被选择。正式服务已经恢复为
Stage1 step 500。

本轮查明并修复的唯一确定性 vLLM 部署 P1 是外置 adapter 的 state 方向错误，而不是 vLLM
RWKV7 WKV 核错误。RWKV-PEFT `time_state` 参数内部为 `[V,K]`；旧 adapter 再转置为
`[K,V]` 后交给 vLLM，破坏了已学习状态。修复后使用 direct contiguous copy，运行时以 SHA
和 orientation attestation fail-fast 固定。

## 三阶段冻结结果

| 指标 | Stage1 | Stage2 | Stage3 |
|---|---:|---:|---:|
| Round1 dev200 operation | 200/200 | 197/200 | 200/200 |
| Round1 direct arguments exact | 107/121 | 107/121 | 107/121 |
| ECRA first-tool exact | 58/120 | 76/120 | 87/120 |
| local-only | 20/30 | 26/30 | 27/30 |
| public-web | 23/25 | 25/25 | 21/25 |
| deterministic | 14/15 | 15/15 | 15/15 |
| connector | 0/20 | 0/20 | 20/20 |
| mixed local-first | 1/20 | 5/20 | 2/20 |
| privacy local-first | 0/10 | 5/10 | 2/10 |
| network macro-F1 | 0.974210 | 0.982512 | 0.918864 |
| local network FP | 0 | 0.066667 | 0.30 |
| failed/interrupted | 4 | 20 | 8 |

Stage1 学会了 selector/停止/协议纠错，且保持联网安全边界；Stage2 在带显式路由提示的合成
dev96 上 96/96，但没有迁移到自然 connector 问法，并引入重复动作；Stage3 在自然 dev176
上 176/176，并把 ECRA connector 提升至 20/20，但把 online/connector 先验推得过强，导致
mixed、privacy、本地任务和普通 web 边界退化。因此总体 first-tool 提升不等于可部署。

## vLLM 代码审查结果

已核对 request/resident row 生命周期、prefill/decode state 打包、dummy/reset state、RWKV7
fp32 state 路径、attention-free feature guard 与 tool parser。未发现第二个能解释行为退化的
确定性 vLLM 核心错误，也没有发现请求间 state 串线的证据。

内核方向对照：FLA 与原始 parameter/internal state cosine `0.9999975562`；vLLM direct
cosine `0.9993027449`；旧 adapter transpose cosine 仅 `0.2380073071`。修复 adapter SHA
为 `be0523b8abb557b8cdbbc22c4cc8dd927b2d07d675afba25b8702897a485bec2`。

仍需改善的一项工程可追溯性问题：服务器的 `/home/chase/vllm-rwkv` 没有 `.git` metadata，
安装分发 metadata 与实际 source tree 也不一致。它不是本轮行为根因，但后续应把运行镜像、
源码 commit、extension 和 wheel lock 为一个可复现构件。

## 下一轮数据方向

下一轮继续以 Stage1 为 parent，不沿 Stage2/Stage3 checkpoint 续训：

1. connector 正例与 ordinary-web、local-command hard negative 做同语义配对，比例至少保持
   1:2 的非 connector 负例，避免单类先验压倒边界；
2. mixed/privacy 样本必须以自然任务表述和真实 observation 回放训练“先读取指定本地依赖，
   再根据证据决定是否联网”，不在 prompt 中直接泄露路由标签；
3. 增加动作完成后的 `final_answer` 对照，以及“证据未充分时继续/证据充分时停止”的成对轨迹，
   覆盖 read、digest、calculator、date_diff、check_command 等完成边界；
4. 保留完整 Stage1 selector replay，并用冻结 ECRA120 评价；不因结果修改阈值，不使用 ECRA
   原题做训练；
5. 下一阶段先做较小、平衡的边界校准，只有同时保持 local FP=0、mixed/privacy local-first 和
   failed/interrupted 门时才扩大数据量。

## 最终验证与部署状态

- `uv run pytest -q -s`：311 passed，79.09 秒；
- adapter 定向回归：2 passed；
- `rwkv-lh-e2e --suite all --validate-only`：固定目录 90/90，catalog valid；
- `git diff --check`：通过；
- Stage1 vLLM service：active/running，health ready；
- runtime loaded state SHA：
  `180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`；
- runtime orientation：`rwkv_peft_parameter_v_k_direct`。

强模型 contract-graph 的完整 E2E90 没有在本轮重跑：现有外部 strong-model endpoint 在先前
canary 中返回 HTTP 403。该阻塞与 vLLM/RWKV state 无关；恢复 endpoint 后应先跑单例
contract-plan canary，再跑全量 supervisor E2E90。
