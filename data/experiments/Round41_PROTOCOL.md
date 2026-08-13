# Round41 预注册协议：Canonical Goal 证据角色目录

## 触发证据

Round40的12个FN中，8个发生在正确workspace到达Goal frontier之后：RWKV从catalog选择同ref或同workspace path lineage作为actual/expected。catalog当前把全部actual再次放入`independent_expected_sources`，并把同一写Attempt的弱action summary与强post-action snapshot并列。

## 唯一架构变更

在不改变任何模型输出和workspace的前提下，确定性生成一个canonical Goal source catalog：

1. **Actual canonicalization**：同一Task/Attempt若存在post-action workspace snapshot，则Goal catalog使用snapshot替代同Attempt的低信息action-result summary；read/list/command/evidence等没有snapshot的真实观察继续保留。权威memory与event log不删除。
2. **Expected role**：expected只包含：
   - Immutable `GOAL`；
   - 来自只读Harness action、且其workspace path在该观察之前没有被active side-effect Task生产过的原始输入观察。
3. **合法配对投影**：每个actual source增加`eligible_expected_refs`，由现有机械规则计算：ref不同、workspace path lineage不重叠。至少保留GOAL。
4. criterion-local响应若选择catalog外ref或不在该actual的`eligible_expected_refs`中，在同一criterion的第二次协议请求中只返回错误类型并要求RWKV重选；不回显被拒JSON，不由Controller选择ref。
5. 最终Controller仍运行原provenance validator并原子提交全部criterion。

“原始输入”只依据action definition的`read_only/side_effect`、Task insertion order和workspace path revision计算，不看criterion文本、外部验收或答案内容。

## 明确禁止

- 不按criterion关键词筛选source，不给RWKV预选actual/expected。
- 不计算或补目标值，不修改reason/decision/ref。
- 不删除权威memory、artifact或审计记录；只改变Goal请求的canonical投影。
- 不把producer output当成expected来证明自己。
- 不修改Task规划、Task verifier、action选择、格式转换、最终答案。

## 固定验证

1. 写Attempt有snapshot：actual catalog含snapshot、不含同Attempt弱summary；底层memory仍两者都在。
2. 读原始输入：可作为expected；先写后读同path：该read不能作为expected。
3. 每个actual的eligible refs排除自身和共享path，包含GOAL。
4. RWKV首选不合法pair：第二次只给同criterion contract error，不回显JSON；第二次合法可通过。
5. 全部候选仍由真实completed Task/succeeded Attempt拥有。
6. pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
7. canary：B05、B06、B08、B11、B12、B13、B18、B28、B29；前8题覆盖catalog FN，B29检查FP。
8. canary后显式B01–B30，对比Round40/Round39。

## 成功判据

- Strict高于14；
- FP不高于Round40的1；
- Goal pair contract失败数低于Round40；
- Controller semantic fields generated=false，RWKV输出未被增删改查。
