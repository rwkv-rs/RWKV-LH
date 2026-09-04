# Stage4–6 三轮最终报告

日期：2026-08-27

## 结论

三轮候选都没有通过预注册的全部 safety gate。按冻结选择规则，正式部署恢复 Stage1 step500；
当前远端服务为 `helicopter-vllm-g1i-13p3b-rwkv-lh-stage1-selector-gpu0.service`，模型别名
`rwkv7-g1i-13.3b-rwkv-lh-stage1-selector500-bos-ctx2496`，state SHA-256
`180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`，direct `[V,K]`
加载 attestation 通过。

“最优”需区分：Stage4 是三轮中冻结 first-tool 能力最强的实验状态，但停止门失败；Stage1 是唯一
按预注册 fallback 可保留的正式状态。没有把 Stage4 的局部高分冒充为可部署最优。

## 统一冻结结果

| 状态 | dev200 op | direct args | local | web | det | connector | mixed | privacy | first total | net macro-F1 | online FNR | stop fail | safety |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Stage1 fallback | 200/200 | 107/121 | 20/30 | 23/25 | 14/15 | 0/20 | 1/20 | 0/10 | 58/120 | 0.9742 | 0.0923 | 4 | baseline fallback |
| Stage4 | 200/200 | 107/121 | 26/30 | 22/25 | 15/15 | 11/20 | 17/20 | 9/10 | 100/120 | 0.9742 | 0.0923 | 9 | fail: stop |
| Stage5 | 199/200 | 107/121 | 23/30 | 21/25 | 15/15 | 12/20 | 3/20 | 3/10 | 77/120 | 0.9488 | 0.1385 | 1 | fail |
| Stage6 | 199/200 | 107/121 | 22/30 | 16/25 | 14/15 | 8/20 | 14/20 | 6/10 | 80/120 | 0.8743 | 0.2769 | 1 | fail |

三轮预注册 selection vector：Stage4 `[3,0.55,59,100]`，Stage5 `[2,0.15,39,77]`，
Stage6 `[2,0.40,44,80]`。这些 vector 只用于通过 safety gate 的候选；三者均不具备资格，故不按
vector 部署。

## 三轮学到的因果关系

- Stage4 的完整平衡边界能显著学习 local/web/connector/mixed/privacy 分类，但没有足够的
  “证据充分后停止”状态，9 个运行被中断；
- Stage5 加入 240 条 completion selector 后，停止错误从9降至1，但 completion 权重把
  `final_answer`/下游工具扩散到 pre-evidence 状态，mixed 17降至3、privacy 9降至3；
- Stage6 将 completion 降至80并恢复全部 Stage4 锚，mixed 回到14且停止保持1，但联网召回
  发生破坏性干扰，web 16、connector 8、online FNR 0.2769。

因此下一轮不应再做单一 flat mixture 的配额搜索。应进行逐状态的 contrastive curriculum：先用
相同 immutable request 构造 `evidence_missing -> local/network tool` 与
`evidence_committed -> final_answer` 成对样本；再单独训练 ordinary-web vs structured-connector
成对语义；每个小阶段立刻在冻结 dev/ECRA 上测量 state delta，只有不破坏 safety anchor 才继续。

## 工程与全量验证

- 数据集测试与全工程：323 passed；
- `git diff --check`：通过；
- E2E90 catalog：90/90，`catalog_valid=true`；
- Stage4/5/6 各自 dev200、own dev240、ECRA120 B 已全部执行；
- 三个 final checkpoint、tokenizer/BOS、loss、direct orientation 和 vLLM health 均验证；
- final Stage1 服务健康，Stage4/5/6 服务均未保留运行；GPU0 上冲突的 Round71 自动训练队列已停止。

contract-graph live E2E90 在执行任何 case 前 fail-closed：模型列表健康探针成功，但强模型 completion
readiness 返回原始错误 `SupervisorTransportError: supervisor HTTP 403 during readiness`。因此没有
把未运行的 live90 记作通过；这是外部强模型调用通道阻塞，不是本轮 RWKV/vLLM 工程回归。
