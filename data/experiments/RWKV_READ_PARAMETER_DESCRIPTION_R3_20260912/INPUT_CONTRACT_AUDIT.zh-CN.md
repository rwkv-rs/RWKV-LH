# 真实失败与说明审计（生成前完成核对）

R1三次失败原文分别为：

1. full_text-1-r1：read_file(path="README.md", start_byte=0, end_byte=-1)。
2. full_text-2-r1：同上。
3. full_text-2-r2：read_file(max_tokens=4096, max_lines=2048, max_bytes=8192, path="README.md", start_byte=0)。

三次均自然stop。完整输入文本、原始输出、输入输出token及源文件SHA保存在FAILURE_INPUT_OUTPUT_AUDIT.json；回归fixture保留逐条原始JSON及来源SHA。此前R1/R2报告把三次都归为end_byte不准确，以本审计更正；旧报告和评分保持封存。

| 内容 | 原输入已经表达 | 说明尚未表达 |
|---|---|---|
| path | string、required、相对工作区 | 必填性在schema内，未用完整自然语言强调 |
| start_byte | integer、minimum=0、default=0、非required | inclusive、UTF-8字符边界、不是字符/行索引、EOF边界 |
| max_tokens | integer、256..8192、default=4096、非required | 省略意义、预算单位、不保证一块读完剩余文本 |
| end_byte/max_bytes/max_lines | 不在properties；additionalProperties=false | end_byte仅为结果元数据、半开区间、不可用-1表示EOF；不应以byte/line预算替代token预算 |

合法参数集合并不歧义：模型违反了清楚的机器schema。缺口在自然语言的读取终点和预算语义，因而“澄清说明能降低非法字段”是可证伪候选假设，不能在实测前写成已证明根因。

仅改唯一ActionHarness read_file登记中的description文本及三个字段description。原字段、类型、required、默认值、范围、additionalProperties、normalize/parser、Harness handler、stop boundary均不变。AST移除description后，修改前后完整harness.py相等；所有其他生产文件逐文件SHA相等。不会加入非法参数alias、自动删除参数、根据README后缀或路径分支、额外模型调用或Coordinator。

工程回归先保留真实拒绝行为，再验证生成输入包含完整语义说明；另外用实际Harness校验默认值、UTF-8边界、半开字节范围、精确EOF与越界。回归只证明合同传递与代码行为，模型是否遵守由冻结前后对照决定。
