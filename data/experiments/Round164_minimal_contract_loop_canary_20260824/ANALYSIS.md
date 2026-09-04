# Round164 Minimal Contract Loop Canary 分析

## 结论

Round164 未通过，不晋级 Full90。分类为
TP/FP/FN/OTHER=`8/3/
3/7`，external pass=
`11/21`。同集 Round162 基线为
`3/3/9/6`：简化循环显著恢复 TP、减少 FN，但 FP 未下降且 external pass 从 12 降到 11。

## 成本与结构

- logical/physical/returned GPT=`95/123/
93`；total tokens=`400008`。
- 对 Round162 同集，logical/physical/tokens 分别下降
`33.6%/35.3%/
56.3%`。
- `104` 个 minimal batches 合计 `27319` bytes，均值
`262.7` bytes；legacy process fields 为 `[]`。
- evidence replay：artifact inheritance=0、content shadow=0、completed transaction
integrity violations=0、authoritative terminal=21/21。

## 全局根因

1. B08 的 `digest_equal` 错把带 target JSON pointer 的关系解释为 manifest 文件自身摘要，
造成正确 artifact 被本地 checker 否定。
2. M12 在 obligations 已满足后仍要求 replacement finalizer 依赖所有历史 correction work，
重复调 Planner 后产生 semantic plan failure；finalizer readiness 不应复制 work DAG。
3. B18 的 Reviewer 把 JSON number `80.0` 当作没有“两位小数文本”，混淆数值舍入和
JSON 序列化表示。
4. 三个 FP 全部来自 semantic Reviewer acceptance：B25/M29 的 frozen contract/output shape
错编，M19 则是 Reviewer 将 `/items` 四次误数为三次。仅简化 evidence transport 不足以
保证 contract 等价性和语义算术正确性。

## 预注册门

- PASS `complete_21`
- PASS `running_zero`
- PASS `runtime_failure_zero`
- PASS `authoritative_terminal_21`
- FAIL `strict_tp_at_least_10`
- FAIL `fp_zero`
- FAIL `fn_at_most_2`
- FAIL `external_pass_at_least_12`
- PASS `artifact_binding_zero`
- PASS `content_shadow_zero`
- PASS `transaction_violation_zero`
- PASS `logical_at_most_100`
- PASS `tokens_at_most_700000`
- PASS `batch_has_no_legacy_fields`
- PASS `review_payload_node_fields_zero`
