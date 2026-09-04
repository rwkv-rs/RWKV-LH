# EXE-G6 task-level deterministic engine R7 只读门禁复核预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在复核程序和复核结果生成前冻结；本轮不发起任何模型请求。

## 复核原因

R7 已按预注册完成 432 个正式生成和一个 explicit-zero probe。原报告
`DETERMINISTIC_ENGINE_ABLATION_RESULT.json` 的 SHA-256 为
`f83470cb85f0f1c0339e727bdf7188ccb49861308a9c59e433f78fe093ff6144`。其唯一失败门禁为
`candidate_extension_mapped_in_all_services=false`。

原 runner 在采集映射证明时使用目的目录标签 `G3_SERVICE`、`G6_SERVICE`、`multi` 作为字典键，且三项
均保存了非空 PID；生成最终门禁时却查询 `g3`、`g6`、`multi`。这是报告键名接线错误，不是推理、
kernel、state、数据、指标或阈值失败。本轮只允许根据已经冻结的证据修正该键名映射：

- `g3 -> G3_SERVICE`
- `g6 -> G6_SERVICE`
- `multi -> multi`

不得修改或覆盖原 R7 结果、raw journal、derived journal、protocol、summary、服务日志或 attestation。

## 冻结证据与方法

1. 原 R7 预注册 SHA-256：
   `60006cfe67cecfefc26dc466c5c4309fba40630627f13180dfdb2f8841151a01`。
2. 原 R7 execution freeze SHA-256：
   `66161dfcebd1f9ecddd2ce6fb157212276f52bb72073dbf53f700939a4a92d34`。
3. 原 R7 runner SHA-256：
   `32afc31cd57b86a88d17df30d1308ec0e752c653ff632e7a920686524801aa7e`。
4. 冻结比较 helper SHA-256：
   `739df0e1f9743e79da73e9f8a147c3cbf0893a6253cceefae2a27f4d30c2ae96`。
5. 冻结 deterministic evaluator SHA-256：
   `4b2ed1bfa6c4e693241ea36e1a48e06a39948cc76d77405af4d8f3dd2b281006`；
   其 raw-first base SHA-256：
   `9c85c2058632d9a58ba0a928e50071b3d2062c6c09acff56ab1dfea4134f9993`。
6. 全部 R7 文件的逐文件 SHA-256 在单独的 execution freeze 中登记；复核前必须逐一相等，且 R7
   目录不得出现未登记文件。
7. 使用冻结 evaluator 的 `validate_raw_integrity` 独立重验四组 hash-chain、request/response body、
   OpenAI envelope 与 raw-derived 链接；使用冻结 helper 独立重算两 profile 的三路 exact 比较和延迟门禁。
8. 重新计算原 R7 的全部十项门禁。除上面的固定键名映射外，计算口径、样本、参数和阈值一字不改。

## 固定通过条件

- 四组证据行数分别为 72、72、144、144，raw/derived 完整性均为 `valid`。
- G3、G6 各自 dedicated 与两种 multi 顺序的 common/raw text/raw token IDs/finish reason/canonical
  pass-fail 均为 72/72。
- dedicated 质量不低于 R6；dedicated 相对 R6 p50 ≤1.10×、p95 ≤1.15×；multi 相对同轮 dedicated
  p50 ≤1.25×、p95 ≤1.35×。
- explicit-zero 与所有 G3/G6 pair 成功；request semantics、raw retention、task-level profile 不切换均成立。
- `G3_SERVICE`、`G6_SERVICE`、`multi` 三项映射 PID 都是非空正整数数组；remote engine identities 前后
  完全相等，candidate 与 canonical-original 的 SHA 身份分别符合原 R7 冻结值。
- 原报告除唯一映射门禁外其余九项均为 true，原始输出未修改/删除/隐藏/重排，产品 18070 当前仍健康，
  物理 GPU0 UUID 不变。

全部通过时，新结果状态固定为
`deterministic_engine_r7_gate_passed_after_readonly_wiring_correction`，并可将原 R7 推理证据标记为
`eligible_for_quality_ablation=true`。这不修改原 R7 报告，也不等同于联网质量、Full90 或正式 V1 已通过。
