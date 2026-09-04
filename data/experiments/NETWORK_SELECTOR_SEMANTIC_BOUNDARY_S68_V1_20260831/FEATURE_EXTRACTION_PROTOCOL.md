# S68 单次前向特征提取协议

日期：2026-08-31（Asia/Shanghai）

## 目的

在不打开 locked test 的前提下，为 S68 train/dev 提取同一当前阶段前向中的
`global_mean + suffix_mean + final_last`。三项特征必须来自一个未修改的
`forward_all_hidden` 结果；当前阶段 recurrent state 只推进一次。

## 固定输入

| 输入 | SHA-256 |
|---|---|
| S68 preregistration | `4e5f0a29560fbce4ab60509e14aaf81dad380b5c0e1f7ba7713758d14779d08b` |
| S68 cases | `8b0f1a17f25863f448858d082c7b6cf7dec5cb76414f635f5f2ab8416566d218` |
| S68 manifest | `4a6e201e3d1dc6dff63f72660a08455ae619c1186b45c95c7f9d86ffc985ea0c` |
| 2.9B model weights | `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044` |
| FP32-CMix source-validation result | `bf771bf0fde7541199c6c99dff3bd5ab1ff566de6b161db603e744af8ed2e6a8` |
| extractor implementation at freeze | `a01c662ae342602b9de8c8fc6c0df5c9aa508dec3dee7bb0e03fe18347bccb17` |
| runtime derivation manifest | `39483f8781e97a467a5642714f396ad26592eb52f71cfa187ce4ca770b552593` |

## 固定引擎与精度

- 引擎：`data/runtime/engines/vllm-rwkv-quality-fp32-cmix-v1`，commit
  `0501caa628967103490507d734f6a5efaf165794`。
- `rwkv7.py`：`a1f6282e3c65a0bc7e05d01a27eccf6e50fd79a5225c6001de9dbf95c97dfc75`。
- WKV mode：`fp32io16`。该模式禁止 FP16 atomic CMix accumulation；source
  validation 已对五个长度边界证明重复路径、CPU state round-trip 与已验收
  ablation bitwise 一致。
- 模型 artifact 仍绑定转换时 revision
  `67f0c5996c50dca0ad779da545cb491527de988f`；当前执行 revision 单独记录。二者不
  同时，backend 必须验证
  `data/runtime/compatibility/vllm_rwkv_2p9b_67f0_to_0501_fp32_cmix_v1.json`，不得
  通过改写原模型 manifest 或跳过 revision 校验运行。
- 这里只把引擎作为候选实验运行时，不替换 `rwkv-8222:18070` 产品服务；正式采用
  仍需独立性能与服务回归。

## 隔离和输出

1. 读取每行原始文本中的 `split` 标记；`test` 行必须在 `json.loads` 前跳过。
2. 重放 bootstrap 和所有 prior steps；当前 step 只调用一次
   `advance_hidden_global_suffix_views`。
3. suffix 边界必须为 V7 `complete_requirement` 的字面 byte-tail，且 prefix/suffix
   token 严格 additive。
4. feature shard 不存 label；原始 float32 hidden reduction 直接保存，不做修补、
   重排、截断或 logit 后处理。
5. 固定规模 train/dev `2000/500`；test JSON parsed、label accessed、metric computed
   必须均为 `0/0/false`。
6. 只用物理 GPU0；远端产品服务在运行前后必须健康。

本协议先于特征运行冻结；运行器和全部 shard/manifest 的 SHA-256 由最终 manifest
登记。输出路径必须投影为最终目录，不得写入 `.pending` 路径。
