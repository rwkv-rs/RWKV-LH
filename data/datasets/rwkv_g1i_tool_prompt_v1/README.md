# RWKV G1i tool prompt micro-dataset v1

- 来源：用户提出的线性 `System: Tools / User / Assistant:json` 格式，以及 RWKV-LH 当前
  `### User / ### Assistant / fenced JSON` 格式。
- 版本：`rwkv-g1i-tool-prompt.v1`。
- 用途：只测试函数调用 JSON 的生成与解析，不执行任何工具。
- 生成方式：人工构造 5 个覆盖读、写、JSON、行删除和命令描述的通用工具选择用例；预期对象采用
  canonical JSON 比较。
- 固定评价：`utf8-byte-ngram-cosine.v1`，UTF-8 byte 5-gram cosine，exact 阈值 1.0，
  near-duplicate 阈值 0.95。
- 文件摘要：见同目录 `manifest.json`。

