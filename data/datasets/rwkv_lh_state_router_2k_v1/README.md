# RWKV-LH State Router 2K v1

- 来源：历史 RWKV-LH 路由/停止缺陷签名与设计稿中冻结的显式系统边界；不使用 ECRA/E2E 请求作为生成种子。
- 版本：`rwkv-lh.state-router-2k.v1`。
- 用途：阶段 0 离线 State Router 多头分类；不得作为主模型任务答案 SFT。
- 生成：`uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_state_router_2k_v1.py`。
- 切分：semantic-family 分组的 train/dev/test = 1400/300/300；同族镜像不会跨 split。
- 协议：最终层有效 token mean-pooled hidden；机械 evidence/policy 真值高于 Summary。
- 污染检查：`utf8-byte-ngram-cosine.v1`，byte 5-gram，ECRA120 与 E2E90 固定 holdout，阈值 `<0.75`。
