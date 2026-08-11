# RWKV G1i online tool-dialog dataset v1

- 来源：用户提供的 G1i 线上完整格式：`System: Tools:`、`Assistant: ```json`、
  `User: Function output:`、最终 `submit`。
- 版本：`rwkv-g1i-online-tool-dialog.v1`。
- 用途：测试首轮函数调用和固定工具返回后的第二轮 `submit`；不执行任何工具。
- 生成方式：从读文本、写文本、读 JSON、删行、运行命令五类通用动作构造两阶段固定期望对象。
- 固定评价：`utf8-byte-ngram-cosine.v1`，UTF-8 byte 5-gram cosine，exact 阈值 1.0，
  near-duplicate 阈值 0.95。
- 文件摘要：见同目录 `manifest.json`。

