# Round42 focused comparison canary：失败并回退

- Strict：`0/10`
- B04、B29错误产物被挡住；B27本次外部结果正确但blocked。
- B05、B06、B08、B11、B12、B13、B18全部从Round41 Strict回归为FN。

## 根因

Selection prompt禁止判断相关性，RWKV普遍机械选择第一个早期观察。Focused comparison随后正确发现这个旧观察不建立当前criterion并返回replan。例：

- B05选择修改前仍含`deprecated=true`的T1 read；
- B06选择part_a输入来判断后续combined产物；
- B08选择payload文本来判断manifest digest；
- B29选择source read而非backup snapshot来判断copy结果。

将相关性选择与语义判断完全分离，破坏了弱模型选择正确actual的能力。统一comparison还会把存在/格式/关系等不同criterion误压成同一种actual-vs-expected比较。

## 处置

Round42代码已完整回退到Round41 criterion-local + canonical role实现。协议和失败数据保留，不进入有效架构指标，不运行Basic30，不上传。
