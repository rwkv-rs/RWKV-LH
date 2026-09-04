# vLLM-RWKV state-tuning 部署代码审查

日期：2026-08-26

## 结论

本轮线上 state tuning 的主要故障不在 vLLM 的 RWKV7 WKV 递归核，而在项目外置
`sitecustomize` adapter 的 checkpoint→runtime 映射。旧 adapter 对 RWKV-PEFT
`blocks.<layer>.att.time_state` 再执行一次 `transpose(-2, -1)`，把训练参数的内部
`[V,K]` 方向错误部署成 `[K,V]`。

FLA 训练接口接收公开布局 `[K,V]`，所以 RWKV-PEFT 调用处先转置；但 FLA kernel 内部按
`[V,K]` 使用该内存。vLLM 的 recurrent state 本身直接是 `[V,K]`，部署时必须直接复制，
不能再转置。

## 可复核证据

固定单步递归核对照（诊断脚本 `temp/validate_rwkv_state_orientation_contract.py`）：

- FLA 与原始 parameter/internal 方向 cosine `0.9999975562`；
- vLLM direct/no-transpose cosine `0.9993027449`；
- 旧 adapter transpose cosine `0.2380073071`。

修复方向后 frozen dev200：

- Round1 parent：schema 200/200、operation 182/200；
- Stage1 child：schema 200/200、operation 200/200，救回 18、回归 0；
- Stage1 child 重复运行 operation 仍为 200/200。

因此旧 adapter 下产生的线上模型行为评价标记为
`INVALID_wrong_state_orientation`；训练 checkpoint、loss 与 tokenizer 验证不受影响。

## 已审查的 vLLM 路径

- `vllm/v1/worker/gpu/model_states/rwkv.py`：request→resident-row 映射、add/remove 时状态
  清理、packed prefill、mixed prefill/decode 和 dummy state 生命周期；
- `vllm/model_executor/models/rwkv7.py`：fp32io16 state dtype、packed WKV 参数与 direct
  `[V,K]` state 使用；
- `vllm/config/model.py` / `vllm/config/vllm.py`：attention-free prefix cache 禁用、V2
  model runner 和 unsupported-feature fail-fast；
- `vllm/tool_parsers/rwkv_tool_parser.py`：不在 RWKV-LH 的 completions 主路径内，不会替换
  Controller direct-call 的工具语义。

上述核心路径未发现第二个能解释旧线上退化的确定性错误。工具选择错误来自错误 state 映射
遮蔽了已学能力，而不是 parser 擅自改写或 WKV request state 串线。

审查时固定的运行源文件 SHA-256：

- `vllm/model_executor/models/rwkv7.py`：
  `e7980ffba01a303fd939e6d042007bbc924e62fc5297bae786edb64f8632e87e`；
- `vllm/v1/worker/gpu/model_states/rwkv.py`：
  `24dc28626ee34b2e93231b67a72dce9c20ac765ede5194c053b39d743ac47c3a`；
- `vllm/config/model.py`：
  `9d5179d6ca49b09c3720f483db3a99d4dff47442f91f79419ce03793bef300dc`；
- `vllm/config/vllm.py`：
  `29b41651313b72f190c2684a1c3145fc148c5b30f476cf88abde31f070018dbd`；
- `vllm/tool_parsers/rwkv_tool_parser.py`：
  `06862ecb5bc3a5654948a6b81aad7fdce40d716518e3911db1af8e25c6396cbf`。

该部署目录不含 `.git` 元数据，因此不能用 commit id 证明来源；正式实验以实际 import source、
上述文件摘要、预编译扩展摘要与服务 attestation 为准。安装分发 metadata 与 source tree 不一致
是可追溯性问题，但没有证据表明它改变本轮行为。

## 整改与防回归

- adapter 改为 contiguous direct copy，并在 runtime attestation 写入
  `state_orientation=rwkv_peft_parameter_v_k_direct`；
- adapter、state、base model 和 runtime manifest 均由 SHA-256 fail-fast 栅栏固定；
- real request row、dummy prefill state、weight-update reset 使用同一 initial state；
- `tests/test_rwkv_state_tuning_vllm_adapter.py` 静态保护禁止 loader 引入 transpose/permute，
  并检查三条 state initialization 路径；
- kernel 数值诊断与线上 corrected parent/child 成对结果作为完整语义回归证据。

Stage2/Stage3 的所有部署只接受修正后的 adapter SHA-256
`be0523b8abb557b8cdbbc22c4cc8dd927b2d07d675afba25b8702897a485bec2`。
