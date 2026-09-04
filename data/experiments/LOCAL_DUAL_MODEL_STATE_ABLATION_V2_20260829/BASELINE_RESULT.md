# EXE-Z0-V2 固定 dev480 基线

有效 run：`exe_z0_v2_dev480_r2`。

## 身份与不干预

- 物理 GPU0；13.3B base SHA-256
  `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- vLLM-RWKV `fp32io16`、V2 runner、native sampler；initial-state adapter 路径与 SHA 未设置，
  所以是 native zero state。
- 480 条各请求一次；无 retry、guided decoding、repair 或 postprocess。
- HTTP response body、RWKV text、token IDs、finish/model/usage 先 append+fsync，再运行 Parser。
- raw chain、raw SHA、模型身份、token IDs、derived link 均为 480/480。

## 固定结果

| 指标 | 结果 |
|---|---:|
| transport / response envelope | 480 / 480 |
| current Harness schema valid | 467 / 480 |
| committed operation correct | 467 / 480 |
| canonical complete call exact | 327 / 480 |
| wire arguments exact | 306 / 480 |
| final required facts | 18 / 20 |
| latency p50 / p95 | 2223.837 / 4397.672 ms |

中英文 canonical exact 分别为 161/240、166/240。13 个 schema failure 是 12 个
`run_command` 达到固定 256 token 上限后未闭合，以及 1 个 `check_command` JSON 结束错误。
主要参数残差集中于 `bind_evidence`、`check_command`、`list_directory`、`replace_text`、
`run_command`、`write_json`，以及部分新增联网/确定性工具。工具选择不是这一批残差的根因。

RWKV 原始输出普遍使用 pretty JSON，而训练 target 是 compact JSON，所以 byte exact 为 0/480；
这不是输出修改。raw 文件保留原格式，canonical 指标来自显式 Parser 与当前 Harness 的派生视图。

## 内容地址

- `RAW_GENERATIONS.jsonl`：
  `f9f7af7745125d48a1b66171bb82db812737b1bf4a24b2219dda914c69393592`
- `DERIVED_EVALUATION.jsonl`：
  `3cdbde9b4de6ae702cf1afdb616310ae5a01dffbe508fa353bbaf51230e169e4`
- zero server log：
  `5651ef1a92dad5c53a3048179f6f9e6af8ad1995de8340d8dfa10d969c1a575f`

`exe_z0_v2_preflight24` 与 `exe_z0_v2_dev480` 的 `ABORTED.json` 记录了两次评测器问题；
它们的已有产物均保留且不计入上述结果。
