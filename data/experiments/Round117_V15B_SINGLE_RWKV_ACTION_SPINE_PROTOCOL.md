# Round117 v15-B Single RWKV Action Spine 预注册协议

## 决策来源

Round116 v15-A 官方 Basic30 为 Strict `8/30`、External `8/30`、FP `20`、FN `0`，
只保留 Round46 的 `6/24` 个 Basic 真阳性。逐题人工审计表明，失败不是“一次 Action
边界”单独造成，而是在线自然语言 Task、泛化 `lh_task_call`、Task completion commit、
Goal completion review 四个语义层共同放大了 RWKV 的错误 Action。

Round117 不在 v15-A 上修 B02/B03/B06，也不恢复 Round46 的 Goal解析、criterion、静态
DAG、reviewer 或 controller语义验证。它只测试一个不可分割的架构变量：把在线语义
执行改成单一 RWKV direct-action session。

## 唯一实验变量

在线链路固定为：

```text
verbatim immutable user request
  -> one RWKV semantic session
  -> one operation-specific registered Harness call OR final_answer
  -> exact ActionResult / typed Observation / artifact revision
  -> the same RWKV semantic session
```

具体要求：

1. 只存在一个在线语义 lane。不存在 Goal planning lane、Task lane、Task completion lane、
   Goal reviewer lane或独立 Final reviewer。
2. 模型边界直接注册每个 Harness Action 的精确 schema，例如 `read_file`、`write_json`、
   `run_command`；另注册 `final_answer(text)`。不向模型暴露
   `lh_task_call(operation, operation_args)`，也不增加 selector。
3. 每个 RWKV回合只允许一个完整直接工具调用或 Final。Harness原样执行模型显式参数，
   Controller不选择 operation、不补参数、不改结果。
4. 每个 Action自动获得稳定 action id、ActionResult、artifact refs/revisions和 workspace
   observation。UI需要的步骤列表只能从 ledger确定性投影，不成为第二套模型进度状态。
   模型调用、Action开始、ActionResult、协议拒绝、恢复和 Final 全部写入同一种内部因果信封：
   `id / parent_id / kind / name / status / payload / refs / digest`。其中 `payload` 只承载该
   环节已经存在的原始数据；信封不得生成 operation参数、结果或完成语义。它是唯一跨环节
   接口与 append-only 审计链，不是新的进度状态机。
5. 删除在线 `lh_tasks`、`lh_task_done`、`lh_goal_done`、`completion_claim committed` 和
   同 evidence digest下的第二次 completion review。RWKV通过继续调用 Action推进，或通过
   `final_answer`结束。
6. Action失败、协议拒绝和 transient结果返回同一 session。重复预算绑定
   `(operation, explicit arguments, target artifact revision, failure fingerprint)`；不能通过
   Task replacement/id变化重置。
7. Final必须非空并保持 raw RWKV文本字节一致；失败或预算终止也必须从同一 RWKV状态
   fork一次 terminal response，不由 Controller撰写结论。

## 明确禁止

- 不解析用户请求为模型生成的 Goal、验收条件或 criterion。
- 不保留在线四字段 Task schema作为控制协议；Round116数据只作历史审计。
- 不从用户文本、Action名、路径或输出推断业务角色、正确答案或完成状态。
- 不用隐藏验收、Codex标准答案、文件名规则或单题白名单影响 RWKV调用。
- 不引入同模型 reviewer/judge、semantic resampling、候选选择或第二模型。
- 不引入 workset/member ledger、collection优化、native-state宣称或效率优化；这些只在
  Basic30过门后另行预注册。
- 简单格式转换层只接受常见 call envelope：`function/name/tool` 与
  `params/parameters/arguments/args/function_args`，以及透明 Markdown code fence；不补
  operation、path、value、content、argv、expected或Final文本。

## 保留能力

- verbatim用户请求、workspace scope、sandbox、`shell=False`、uv Python；
- 单一 `ActionDefinition` registry；
- tokenizer byte cursor、exact ActionResult、raw/normalized审计；
- SQLite/checkpoint/crash resume、artifact revision和版本失效；
- 当前后端只标注 `prompt_replay`，不得宣称 native recurrent state；
- Final即使错误也必须交付，不由框架改写。

## 离线完成条件

1. 测试中不存在可调用的在线 `lh_tasks/lh_task_done/lh_goal_done/lh_task_call`。
2. 模型看到 operation-specific工具及其精确 required/additionalProperties schema。
3. 一次 direct call产生一次且仅一次 Harness Action；协议拒绝不执行 Action。
4. 下一回合看到 exact prior Observation和最新 artifact revision。
   每个持久化 revision 同时只追加一个统一因果信封，parent链、sequence和 digest连续；
   UI/runner只从这条链和Action ledger确定性投影，不读取历史Task字段。
5. 失败预算跨恢复/重启保持同一因果键；artifact改变后形成新键。
6. raw/normalized call均完整审计且语义字段不生成。
7. Final `text`非空并与 raw RWKV显式值一致；terminal fallback仍来自 RWKV。
8. 现有 sandbox、uv Python、cursor/EOF、crash resume、web UI和固定数据目录回归通过。
9. E2E-90 catalog保持 `90/90`，LH-Control v1/v2继续分开登记。

## 固定数据、模型与参数

- 数据：`data/datasets/rwkv_e2e_90_v1/manifest.json`登记的固定 E2E-90。
- Stage A：恰好 `E2E-B01..E2E-B30`，顺序固定，不先跑单题优化。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`。
- endpoint：`http://127.0.0.1:29610/v1`。
- sampling：temperature `0.05`、top-p `1.0`、top-k `0`、现有 penalties不变。
- `max-transitions=200`、concurrency `1`、WSL `UbuntuRecovered`、uv `0.12.5`。
- 官方运行过门后才进行一次相同源码/数据/顺序/参数的 confirmatory；两次全部报告，
  不选择较优结果。

## Stage A 验收门槛

必须同时满足：

- Strict `>=24/30`；
- External `>=24/30`；
- FP `<=1`、FN `<=1`；
- 保留 Round46 至少 `23/24` 个 Basic真阳性；
- missing-zero artifact similarity：固定 40 个
  `file_content/json_equals/json_exact_keys/directory_file_set`验收项，缺失记 `0`，平均值
  `>=0.959895851803`（重算后的 Round46 Basic基线）；
- B02/B12/B15/B17/B21/B28 的 producer回合不因 generic wrapper退回重复读取；
- B06/B14/B25 不因自然语言 multi-action Task边界丢失第二来源；
- B13/B30 不通过 Task replacement重置恢复预算；
- Final非空和 raw equality `30/30`；
- 每题人工复核首次 RWKV Action偏离、后续放大和真实产物。

请求数、prompt tokens和延迟只作诊断，不替代质量门槛。Stage A任一核心门槛失败即
拒绝 v15-B，不运行 collection或 full90，不加单题 gate。

## 后续门槛

只有 official与confirmatory Basic30都过门，才另行预注册 collection/workset；只有
collection过门，才运行完整 E2E-90。完整 E2E-90仍须 Strict `>31/90`、FP `<=24`、
FN `<=1`、Basic `>=24`、Medium `>5`、Hard `>2`。

## 源码冻结

实现完成、全部离线检查通过后，在第一次在线请求前追加独立
`Round117_v15b_source_manifest.json`，记录所有 runtime/test/catalog哈希、dirty diff、
endpoint能力和实际离线结果。冻结后不得修改 runtime源码；若修改，必须新建实验版本。
