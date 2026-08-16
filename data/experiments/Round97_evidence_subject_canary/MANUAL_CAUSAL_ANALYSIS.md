# Round97 四题人工因果分析

## 结果

- Strict `2/4`：B01、H04 PASS；B02、B03 FAIL。
- External `3/4`；B03 为 FN；FP=0。
- 四题 Final 均非空且等于 RWKV原始输出。

## 逐题

- B01：RWKV声明 `greeting.txt`，写入、读取、显式完成；Strict PASS。
- H04：RWKV声明 `safe/result.txt`，写入、读取、显式完成；Strict PASS。
- B02：Task proposal正确声明 T1/input.txt 与 T2/report.json。T2读取 input.txt 后 readiness 保持 false，证明 subject绑定有效；但 RWKV继续选择 read_json(input.txt)，形成真实失败和重复循环。剩余放大点是 recovery 中 Task objective 与 declared subject不够紧邻，模型没有转向创建/观察 report.json。
- B03：T1提前执行并验证 `patch_json(config.json)`，工作区已正确。T2声明 workspace_mutation/config.json，但只读取正确结果后尝试完成；Controller拒绝，因为 mutation证据属于已完成依赖 T1而非 T2。随后出现重复 read_json 和另一种显式 flattened 外壳拒绝，最终 FN。

## 跨题结论

- subject绑定消除了“任意文件同类型即可”的结构漏洞，未破坏 B01/H04。
- Task-owned 限制过窄：已完成依赖闭包内、同 subject、同结构类型的权威 Attempt 应可复用；无依赖或 subject不同仍不可复用。
- B03 的 `top-level operation + operation_arguments(actual args)` 所有语义值均显式存在，应由简单转换层搬运。
