# RWKV-LH Agent Capability Ladder V1

- 来源：用户授权的真实本地 Agent 工作流；seed 由确定性脚本合成，未复制外部语料。
- 版本：1（2026-08-30 冻结）。
- 用途：独立于 Full90，测量五层连续端到端能力上限；仅作 holdout，禁止进入 state tuning。
- 生成：`uv run python scripts/generate_agent_capability_ladder_v1.py`。
- 任务：10（每层 2）；本地 8，联网 2。
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- 评价：byte-exact、公有 verifier、隔离隐藏 checker、真实 evidence URL 交集；不得按结果修改口径。
