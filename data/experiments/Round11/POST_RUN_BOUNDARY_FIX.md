# Round11 运行后 capsule token 边界修复

## 发现

正式 Round11 的 95 个 obligation capsule 中，E2E-H14 和 E2E-M15 按完整序列化后的
RWKV tokenizer 复算为 5005 和 5012 token，超过预注册的 5000 上限。

根因是裁剪循环结束后才写入 `projection.capsule_tokens`；该自描述字段本身再增加
token，而旧测试只检查了记录值，没有将完整 capsule 重新 tokenization 并比较。

## 修复

- 从初始 capsule 构造起就包含 token 计数字段。
- 最终数量字段写入后做固定点复算；若完整 payload 仍超限，继续按原有确定性
  优先级裁剪详细 observation/artifact/evidence/workspace/task 投影。
- 完整 active task index、Goal digest、unresolved criterion 与 RWKV 语义字段不被修改。
- 无可裁剪详细投影而权威 index 仍超限时 fail closed。

## 验证和口径

- 专项回归：2/2。
- 全量产品测试：190/190。
- LH-Control：30/30。
- 没有重跑或改写 Round11 E2E；18/90 External、0 Strict、0 Completed 仍是冻结成绩。
- 修复不使用 hidden acceptance、标准答案、相似度或语义筛选。

