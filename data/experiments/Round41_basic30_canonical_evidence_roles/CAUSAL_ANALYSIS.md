# Round41 Basic30 Canonical Goal 证据角色分析

## 指标

| 指标 | Round40 | Round41 |
|---|---:|---:|
| Strict | 14 | 17 |
| External | 26 | 24 |
| FP | 1 | 3 |
| FN | 12 | 7 |
| 请求 | 486 | 467 |

Canonical actual投影和expected角色目录把8个已知Goal FN中的B05、B06、B08、B11、B12、B13、B18恢复为Strict；B28仍FN。全轮Strict提高3、FN减少5、请求减少19，证明source role整改有效。

但FP为B04、B27、B29，超过预注册上限1，因此Round41不上传。

## 三个FP的共同新根因

三题均已越过格式、候选角色和pair合法性问题：

- B04 GC2选择copy snapshot；expected选择GOAL。copy内容实际与source不等。
- B27选择最终service.conf观察；内容仍有`protocol=v1`。
- B29 GC1第一次弱summary被pair contract拒绝，第二次选择backup完整snapshot与source原始read；两者内容明显不等。

RWKV在同一个大catalog请求里同时承担选择refs、读取内容、比较和给pass/replan，最终仍将不等判断为pass。B29尤其证明继续删候选会变成用规则筛答案：正确独立pair已经存在且被选中，错误发生在RWKV比较本身。

## 剩余FN

B14、B19、B24、B28主要仍在Goal选择/协议或后续replan；B21、B25、B26是不可执行验证Task/恢复问题。需分别整改，不能混为格式问题。

## 结论

保留canonical证据角色目录，但Round42应把“选证据”和“比较证据”拆成两个RWKV请求。比较请求只展示单criterion和选中的完整actual/expected，不由Controller执行比较或修改结论。
