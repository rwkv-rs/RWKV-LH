# RWKV-LH Selector 单协议收敛结果

日期：2026-09-04（Asia/Shanghai）

## 结论

Selector 已从多代并存收敛为唯一当前路径：`rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1`、固定 25 类顺序、单个 MLP Head artifact，以及 `persistent-causal-sequences.v1` 状态身份。compact protocol v3-v8、退役 20 类客户端/协议、Soft-MoE、description、takeover、hierarchical takeover 和 objective gate 均不再存在于源码或发布包。

本阶段没有训练、生成、加载或选择任何 StateTune，也没有训练 Selector Head。

## 变更范围

- `rwkv_lh/exact_tool_selector/` 从 21 个 Python 模块收敛为 7 个职责模块：`__init__.py`、`head.py`、`input_protocol.py`、`network_client.py`、`network_protocol.py`、`network_service.py`、`runtime_projection.py`。
- 当前 MLP artifact 从代际文件名 `model_v2.py` 改为职责文件名 `head.py`；服务只加载这一种 25 类 artifact。
- 删除 122 个退役源码、脚本和专属测试文件；最终提交共改动 141 个文件，新增 260 行、删除 30,043 行，净减少 29,783 行。
- 旧生成器、旧服务启动脚本和旧数据代次测试退出可执行工程；历史实验数据没有被改写或作为兼容入口加载。
- G1J prompt 的工具菜单与网络协议工具菜单合并为同一来源，避免训练/在线描述漂移。
- 产品运行时不再根据旧协议布尔标志分支；存在 Selector 即进入唯一 G1J Selector→Executor 合同。

## 验证

- `python -m compileall -q rwkv_lh scripts tests`：通过。
- `pytest -q --tb=short`：`637 passed in 53.51s`。
- `uv lock --check`：通过，43 个包解析一致。
- `git diff --check`：通过。
- 退役协议/模型静态扫描：生产源码、当前脚本和测试中 0 个引用。
- clean wheel 构建：通过。首次构建发现 setuptools 的旧 `build/` 缓存会把已删除模块带入 wheel；清除明确的生成缓存后重新构建，wheel 中 Selector 只包含上述 7 个模块，Selector 脚本只包含当前 G1J 数据生成、特征提取和 Head 训练三个入口。

## 剩余阻断

当前合法的 `rwkv_lh_g1j_selector_intent_head_v2` 尚未生成。现有历史 Head 来自每行复用 bootstrap State 的独立样本，不能满足在线 step-revision-local 持久因果状态身份，运行时继续 fail closed。下一阶段必须先预注册并构造真实同分布的持久因果特征，再训练新的非 StateTune 分类 Head；不能把旧 Head 改名或补元数据后复用。
