# Round134 — GPT-5.4 Supervisor on R126 full-schema spine 预注册

日期：2026-08-21

## 因果问题

Round133 canary 已证明 progressive 两阶段在动作结果后会使固定 G1i-13.3B 复读上一条 direct
operation，无法进入完整 Hybrid E2E。Round134 不修改或容错 progressive，而是回到已验证的
R126 full-schema `single-rwkv-direct-action` 执行 spine，在其外只增加 GPT-5.4 有界计划与 Final
审查。这是新的实验，不与 Round133 合并。

## 固定配置

- 数据：冻结 RWKV-E2E-90，30 basic / 30 medium / 30 hard。
- Worker：`rwkv7-g1i-13.3b-20260805-ctx16384`，prompt replay，temperature 0.05。
- Harness disclosure：`RWKV_TOOL_DISCLOSURE_MODE=full`。
- Supervisor：OpenAI-compatible `gpt-5.4`，temperature 0.1。
- Supervisor 一次 plan；每个 RWKV Final 一次 review；最多一次 REVISE 返修。
- Supervisor 无工具执行权、不能生成 Harness 参数、不能改写 Final、不可见 hidden acceptance。
- max transitions 200；concurrency 1；其他 RWKV sampling 与当前固定配置一致。

## 固定命令

```bash
RWKV_TOOL_DISCLOSURE_MODE=full \
/home/chase/GitHub/RWKV-LH/.venv/bin/python \
  /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --supervisor openai --suite all --case E2E-B01 \
  --max-transitions 200 --concurrency 1 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round134_hybrid_gpt54_r126_canary_B01_20260821

RWKV_TOOL_DISCLOSURE_MODE=full \
/home/chase/GitHub/RWKV-LH/.venv/bin/python \
  /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --supervisor openai --suite all \
  --max-transitions 200 --concurrency 1 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round134_hybrid_gpt54_r126_full90_20260821
```

## Canary gate

1. B01 Strict PASS；`greeting.txt` 精确字节验收 PASS。
2. 一个 plan、至少一个 review，provider/model 均为 `openai_compatible/gpt-5.4`。
3. RWKV 独立执行写入与读取验证；Supervisor 无 action record。
4. delivered Final 与 RWKV 原始 `final_answer.text` 字节一致。
5. hidden acceptance 不进入两类模型 trace；audit、causal ledger、run protocol 完整。

## Full90 固定评价

- 主指标：Strict、FP、FN、OTHER；isolated verifier 口径不变。
- Terminal target：Strict > 36、FP <= 24、FN <= 1、90/90 valid、0 running。
- byte-precision B01/B06/B13/B19/B28 = 5/5。
- 相对 R126 official、R132 与 Round133 canary 报告任务 churn、RWKV 请求/动作/协议拒绝、
  Supervisor plan/review/REVISE 数量、token usage 和延迟。
- Full90 开始后不修改任务、参数、阈值或评分口径，不因中途结果提前选择性停止。
