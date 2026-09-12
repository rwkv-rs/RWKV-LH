# 单步读取夹具修复 R2

没有新项目级 Agent Strict/completed；mutation=0；每次在一次读取和真实观察入 State 后截停，不声明任务完成。

修正的 index.html 不存在场景独立重复 **3/3 通过**，实际工具成功 **0/3**，三次均应以真实 FileNotFoundError 保留异常。输入 token 核验 3/3；完整 State、父子交接、输入/输出、token 和原始错误见 runs/ 与 RAW_EVIDENCE.tar.gz。

## 根因、修复与回归

R1 选择了历史不存在动作，却直接配对最终工作区。该文件随后被实际 write_file 创建，因此原3次评分不能代表模型失败。通用根因是冻结阶段只检查整个目录SHA，没有验证源动作的存在性和内容身份；影响任何发生后续创建/修改/删除的生产trace，不限于文件名或项目。

新增只读 preflight：缺失例必须实际不存在且源错误为 FileNotFoundError；成功例必须为普通文件、匹配原 artifact SHA 和原结果字节。真实R1错误夹具的回归先失败（REGRESSION_RED.log：未抛ValueError），修复后两个测试通过（REGRESSION_GREEN.log），其余七个R1夹具均核验通过。

本轮复用已授权 realprojectdevv1 的 RP-WEB-02 公开初始工作区，通过现有 materialize_workspace 创建隔离副本，没有新编场景或新数据集版本。修复只改变诊断夹具和预检，生产模型、工具、parser、stop boundary、State和R1 scorer逐字节不变；R1已封存原分，不重评分，也不将R2替换进R1分母。

## 当前能力结论与下一步

R1有效证据18/21：代码全文6/6、EOF空读取6/6、server.py不存在3/3、README全文3/6；本轮另一不存在文件独立3/3。两轮分开报告。读取基本路径已有有限重复证据，但README相同输入仍生成非法end_byte，通用单步读取稳定性未达标；不进入自主定位或修改阶段。

最小生产候选仍仅建议澄清唯一 read_file 工具说明中的合法输入字段、max_tokens和next_start_byte语义；须先失败后通过的回归及另行冻结验证，不通过扩展参数兼容或程序代选掩盖模型能力。本次没有实施生产修复。

完整tests/为1508 passed、0 skipped（R1同一生产源码运行）；另有本轮夹具红绿2项测试。原5个未提交文件保持SHA，未训练、部署、更新GitHub或读取Holdout。预注册SHA `3ad1cb08abda257be20d7ad9a2c6347fae411c0e6176e1dd7f734657fe6dfc1e`；完整证据清单见SHA256SUMS.json。
