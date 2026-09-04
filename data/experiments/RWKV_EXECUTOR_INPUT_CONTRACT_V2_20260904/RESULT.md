# RWKV Executor 任务语义尾部合同结果

日期：2026-09-04（Asia/Shanghai）

- E2 保持相同 zero-State 13.3B、原生 State、采样参数和冻结六例矩阵。
- 严格 operation+remaining path 通过 3/6，未达到 6/6 门槛，不进入生产。
- 六例 operation 均为合法 `read_file`，但三例仍选择 completed path。
- 失败分布不是中文、英文、字典顺序或目录层级单一因素：中英文均有成功和失败。
- 相比 E1 的 remaining path 6/6，移除结构化 role/schema 标记并改为自然语言外壳使遵循率下降，说明不能只以“更短”为优化目标；必须保持 G1J 已见的角色协议形状，同时把动态状态放到该形状的尾部。
- 结果 SHA-256：`f7b53501a3b47a285f99fc9600b3820196615b86163226d7f18bfa3a3a61753e`。
- 本实验没有使用 StateTune，也没有修改冻结矩阵或评价口径。
