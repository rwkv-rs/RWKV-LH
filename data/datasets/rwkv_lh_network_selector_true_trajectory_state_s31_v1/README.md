# True-trajectory Selector state S31 v1

- 仅使用冻结 S30 train 的 2000 条全 25 类均衡真实轨迹优化 2.9B Selector 初始 WKV state。
- S30 dev 只用于本地开发消融，S30 test、S28、S23/ECRA、13.3B Executor 与 Harness 均未进入 state 训练。
- target 只监督精确类别后缀；未生成、修改、过滤或删除任何 RWKV 原始输出。
