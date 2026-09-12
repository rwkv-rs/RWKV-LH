# 简短读取参数说明 R4：固定用例前后验证

没有新项目级Agent Strict/completed；诊断mutation=0；均在一次调用或协议拒绝边界截停，不声明任务完成。没有进入自主定位、多步任务或Coordinator。

## 前后结果

| 固定组 | 本轮新采原说明 | 本轮简短说明 |
|---|---:|---:|
| R1有效7例×3遍 | 18/21 | 21/21 |
| R2修正缺失例×3遍（独立） | 3/3 | 3/3 |

| 主组遍次 | 原说明 | 简短说明 |
|---|---:|---:|
| 1 | 6/7 | 7/7 |
| 2 | 6/7 | 7/7 |
| 3 | 6/7 | 7/7 |

协议错误3→0，提前final_answer 0→0。不存在文件的正确读取尝试以真实FileNotFoundError通过诊断，其工具success仍为false。任何替代必要读取的final_answer均按更严格口径算提前终止；没有生成观察后的回答，不声称已验证回答理解或任意成功声明。

**预注册门通过。** 门要求最后两遍两组全部通过，零协议错误与提前final_answer，且原说明3/3用例不退化。门只适用于这些固定输入，不证明普遍稳定；本轮不自动升级任务。

| 用例 | 原说明 | 简短说明 |
|---|---:|---:|
| full_text-1 | 0/3 | 3/3 |
| full_text-2 | 3/3 | 3/3 |
| full_code-1 | 3/3 | 3/3 |
| full_code-2 | 3/3 | 3/3 |
| offset-1 | 3/3 | 3/3 |
| offset-2 | 3/3 | 3/3 |
| missing-1 | 3/3 | 3/3 |
| missing-2 | 3/3 | 3/3 |

## 完整历史与原因界限

R1历史有效18/21、独立R2历史3/3分别保留；R1另外3次夹具无效记录未替换或重评分。原始三次R1参数失败实际为两次end_byte=-1、一次max_lines=2048与max_bytes=8192，旧“全部end_byte”汇总以R3的完整输入输出审计更正。

本任务先测的R3较长说明明确提到了非法结束字段：新采主组19/21→14/21、独立补充3/3→2/3、协议错误2→8，NO_KEEP。R3不是本轮基线，不能省略失败候选、合并分母或只展示获胜文案。R4重新采集了原说明与简短说明两个完整固定组。

原schema的合法字段、类型、required、范围和additionalProperties=false本来明确；自然语言缺少省略、起止范围、EOF和token预算语义。R3证明“加上更详细的禁止说明”不充分。R4仅列合法输入及正向语义，不在输入描述里列举非法字段名或负值示例。本轮检验的是该说明整体（措辞和长度都改变），不能单独断言负向提示、注意力或训练分布是已证实的内部原因。

唯一生产变化仍是read_file登记的description及参数description：path必填字符串；start_byte可省略默认0、inclusive UTF-8字节偏移、字符边界至decoded text EOF；max_tokens可省略默认4096、整数256..8192、token单位；结束位置由工具计算且不包含。字段、类型、默认值、范围、parser、normalizer、Harness执行、stop boundary均未改变，不接纳或重写非法参数，不按README或后缀特判，没有程序代选操作或参数。

## 冻结、State与运行证据

预注册SHA `0372f069e586581aaf16bf9843cfa68e5bafcc9a41a8e263b8fd51136485203e`。在模型运行前同时冻结原说明/候选客户端，AST忽略read_file说明后完全相同，其他生产文件SHA相同。按before→after，每臂主组21次+独立补充3次；原request、workspace、scorer、13.3B模型、zero State、temperature0.1/top_p1/top_k0、1800输出token上限不变。没有语义重试或新增模型调用。
完整输入token逐项核验：before 24/24、after 24/24；去掉唯一说明差异后实际输入一致：True。每例三遍输入相同与逐次raw输出、生成token、模型/State身份、commit/rollback、实际观察父子State交接见CALL_AUDIT.json及RAW_EVIDENCE.tar.gz。

- before input tokens 2865–3043；output tokens 37–47；停止原因 {'stop': 24}。
- after input tokens 3012–3190；output tokens 37–49；停止原因 {'stop': 24}。

基线offset-1-r1在生成返回后的commit遭本地SSH转发断开；远端健康。恢复转发后，现有Native恢复以原request_id与digest安全重发commit一次，只有一次generation，后续观察提交成功；原始错误和恢复事件完整保留，不算模型重新采样或删除失败。监听消失的原因未知，未修改网络代码。服务器项目132/engine6393文件均与原上传manifest匹配，无服务器Git或重新部署。

## 回归和当前范围

回归保存原R1三份原文及R3两个真实新增退化样本。5 failed/1 passed→6 passed：候选说明确实进入模型输入，非法输出仍在Harness执行前拒绝；实际Harness测试覆盖默认值、UTF-8边界、半开范围、EOF和越界。候选源码完整tests/：1514 passed、0 skipped、241.68秒。工程回归不是模型能力得分。

这两轮是有限候选搜索，原基线也表现出采样波动。没有独立新用例泛化检验，长文件分页、其他换行形式、目录/权限异常、定位和回答仍未在本轮覆盖。只据冻结门报告当前固定用例，不扩大结论。

原5个未提交文件逐文件SHA保持不变。未训练、新建datasets版本、访问Holdout、更新GitHub或恢复项目级A/B。原始run/SQLite/输入输出/State/工作区/日志封装于RAW_EVIDENCE.tar.gz，两套冻结客户端见FROZEN_SOURCE_SNAPSHOTS.tar.gz，逐文件SHA见SHA256SUMS.json。
