# Round53 固定真实 Canary 选择

状态：在任何 Round53 真实模型调用之前登记。Canary 仅诊断，不替代完整 E2E-90。

| Case | 冻结选择原因 |
| --- | --- |
| E2E-B01 | Round46 Strict；最小写入控制，检查 reviewer 是否破坏正确动作。 |
| E2E-B02 | Round46 Strict；读→派生 JSON 控制，检查依赖 observation 传递。 |
| E2E-B04 | Round46 safe fail；目录/复制角色错位。 |
| E2E-B29 | Round46 FP；copy Task 丢失 source bytes。 |
| E2E-B30 | Round46 safe fail；run-tests Task 反而改写测试。 |
| E2E-M03 | Round46 Strict；中等迁移控制。 |
| E2E-M06 | Round46 FP；copy Task 写 manifest 代替复制。 |
| E2E-M08 | Round46 FP；Markdown Task 选择 JSON/错误模板。 |
| E2E-H12 | Round46 safe fail；单 Task 试图承担 15 shards。 |
| E2E-H15 | Round46 FP；未观察项目即实现且 Run tests 选错工具。 |
| E2E-LH09 | Round46 FP；API workflow 阶段角色错位。 |
| E2E-LH11 | Round46 safe fail；集合 phase/cursor/member 动作错位。 |

判断只看动作 reviewer 的 accept/reselect 因果链、Strict/FP/FN 和相对 Round46 outcome，不按速度或请求数淘汰。
