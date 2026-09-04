# EXE-G9 训练数据执行冻结

冻结时间：2026-08-30；在远端权威 tokenizer/`MyDataset` 预检、G9 训练和任一 G9
checkpoint 推理之前。

- 预登记：`EXE_G9_STABLE_SCHEMA_CONTRAST_PREREGISTRATION.md`，SHA-256
  `0c50e9d185ffe5732fffb9eeba3e3affd535e59b425eb619f9646f9f3678c54a`；
- 生成器：`scripts/generate_executor_stable_schema_contrast_g9_2k.py`，SHA-256
  `1cdb431c4c6b6573a62c4071d08a6e00c2269f4ad3263c11ac8d35a0a39a6591`；
- 数据目录：`data/datasets/rwkv_lh_executor_stable_schema_contrast_g9_2k/`；
- manifest SHA-256：`08920c420b60e2df0126f74af27c2aa01ff1084bb8e7d881907b8f04470282a8`；
- target-suffix 训练 JSONL SHA-256：
  `189b4fc8115ef74660c011eb828ce36414e31df4f6c0b5d08338a7581976c733`；
- stage SFT JSONL SHA-256：
  `4855f789114d39d49c60cba8a971226164022542726ecea602fcfd3d2417956b`。

冻结数据为 2,000 行，构成严格等于预登记的九类配额。生成期检查结果：exact prompt
duplicate=0、train/eval source identity overlap=0、target truncation=0、literal
`current_requirement` 位于续写点前最后位置、generated RWKV text=false、raw output
modified=false。与冻结 live holdout 的 byte-5-gram cosine 最大值为
`0.2255307816261732 < 0.75`。

远端预检只能验证并复制这些字节，不得重写、过滤、重新排序或替换任何行。预检失败则训练
fail closed；训练后不得修改本冻结记录、数据、评价门槛或相似度算法。
