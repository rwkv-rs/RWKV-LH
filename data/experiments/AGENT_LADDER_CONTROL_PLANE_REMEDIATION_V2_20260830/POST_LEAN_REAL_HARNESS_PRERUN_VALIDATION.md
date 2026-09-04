# 精简 Planner 后真实 Harness 复跑前验证

- 日期：2026-08-30。
- targeted regression：94/94 通过。
- full project regression：649/649 通过；唯一 warning 为 Python 3.13 fork deprecation，不是测试失败。
- Planner-only production canary V2：5/5 HTTP、strict Schema、contract 编译、mutation→verify；伪路径 0；具体 operation 选择 0。
- canary result SHA256：`7973411b391d188d6bc5932b442653964e36d654db9ecc96eec4df56b8bad3ed`。
- authority reanalysis SHA256：`19ee5965752717a5132fd06e9dfadde43fac86121d27dc7fcd33202be7dc59c7`。
- 产品 `127.0.0.1:29610/health`：HTTP 200。
- 远端实验端口 18075、local output、orchestration、remote evidence tag 和 remote log 均确认未占用。
- 远端 executor 固定物理 GPU0 UUID：`GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；产品 18070 不停止。

真实复跑继续使用冻结 10 题、S66 zero Selector、离线 G3、联网 G6、concurrency 3、max transitions 300 和既有 exact acceptance。不得修改任何 RWKV 原始输出。

