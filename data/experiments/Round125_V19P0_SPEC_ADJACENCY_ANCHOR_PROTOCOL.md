# Round125 v19-P0 规格邻接锚点（Spec-Adjacency Anchor）预注册协议（冻结前草案 → 冻结）

日期：2026-08-16（实现前预注册；运行后不得修改口径、门槛或变量定义）。
基线 = Round119 v18-P0（Strict 30 / FP **36** / FN 0；字节精确 5/5；代码链 6/6）。

## 授权与依据链

R124 判 REVERT（27/90）给出**决定性程序级结论**：采样温度是**错误的干预层**
（flip 矩阵 INTR→TP = 0——升温把成功重复循环由 loop 变成 FP，从不变成 TP）。
真正的主导失败类是 **FP（completed 但 external=False）**：R119 有 **36 个 FP、0 个 FN**。
本轮把根因目标移到 **完成边界的正确性 / 交付物字面保真**，不再调温（采样已字节回退到
R119 `_SAMPLING` temp0.05）。方向由项目所有者的**固定态邻接第一性原理**直接给出：
「每次调用一个身份、一个决定、最少的竞争信息；**最关键的 literal 内容放在离续写点最近的地方**」。

## 全量 90 轨迹分析（R119 基线，本轮决策来源）

分类：TP=30，FP=36，FN=0，INTR/其它=24。对 **36 个 FP** 按 external_checks 的
actual-vs-target 机械归类：

| 机制 | N | 用例 |
|---|---|---|
| json_key_names（顶层键名/结构字面漂移） | 10 | B18 H06 H08 LH04 LH09 M15 M16 M22 M26 M29 |
| wrong_path_or_missing_artifact（目标路径字面漂移） | 7 | B04 H03 H18 LH01 LH06 M06 M23 |
| json_value_or_structure | 6 | B17 M03 M13 M14 M19 M27 |
| text_content_mismatch | 5 | B16 B24 B29 M04 M25 |
| other/refusal_or_empty | 4 | H01 H09 M10 M18 |
| whitespace_newline_only（尾换行/空白字面） | 3 | B05 B11 B22 |
| ordering_only（排序字面） | 1 | M08 |

**21/36（key-names 10 + path 7 + whitespace 3 + ordering 1）是纯字面保真失败**：计算基本正确，
交付物偏离任务文本中逐字写明的字面 token（精确路径 `archive/2026/`、精确键名 `events`
vs `entries`、尾部 `\n`、精确排序）。样本佐证：
- **B04**：任务要求 `archive/2026/source.txt`，agent 写 `archive/source.txt`（丢 `2026/`），
  并自述「created and **verified**」——自检对照的是自己的**改写**而非原始字面。
- **B05/B11/B22**：内容按空白折叠后与 target 逐字相同，仅缺任务明写的尾换行。
- **LH04**：写 `{entries:[...]}`，target 顶层键为 `events`。
- **H03**：seed.txt（7 字节）存在却「refuse: no content」——未真正读取即声明完成。

**代码级根因（已核对 `rwkv_lh/model.py` + `model_session.py` + `model_io.py`）**：R119 为
append 抄本架构。每回合续写点在 `Assistant: ```json\n` 之后；其**最近邻**恒为**最新一条
观察** `User: Function output: {obs}`；而逐字规格 `immutable_request` 只在**根引导块**出现
（随回合越来越远），或在 rollover 的 `_assignment` 里被 `sort_keys=True` 字母序压到
`workspace_manifest` 之后。**最关键 literal 距续写点最远**——正是所有者原理的反面。

## 假设

1. 把**逐字任务请求**放到每回合续写点的**最近处**（邻接锚点），字面漂移型 FP（≥21 例，
   尤其 B04/B05/B11/B22/LH04/M08 等）有机会 FP→TP，Strict 上升且 FP 下降。
2. 因重申的是任务**自身逐字文本**（不解析、不读隐藏验收、不改写），字节精确对照组
   （B01/B06/B13/B19/B28）不回退，甚至更稳。
3. 保留 R119 append 抄本（不折叠历史）+ 锚点仅为生成期后缀（不写入持久抄本），
   故不重现 R123 的确定性不动点，也不污染因果账本。

## 精确变更（单一根因变量：规格邻接；全局机制，无单题特判）

### C1 生成期规格邻接锚点（`rwkv_lh/model_session.py` + `rwkv_lh/model.py`）

1. `ModelSession.generate` 增加可选形参 `continuation_anchor: str = ""`。当非空时，发送给
   `text_completion` 的 prompt 由 `checkpoint.transcript` 派生：在**结尾续写标记**
   `"\n\nAssistant: ```json\n"` **之前**插入 `"\n\n" + continuation_anchor`。**持久
   checkpoint 及其 transcript_digest 不变**（下一回合 append 仍基于干净抄本）。
2. 诚实审计：`model_session_generation_started` 事件新增
   `continuation_anchor_tokens`（锚点本地 token 数）与 `effective_prompt_tokens_local`
   （= transcript + 锚点），`prompt_tokens_local` 仍报持久 transcript 值；输入预算检查
   改用 effective 值。transport 仍为 `prompt_replay`。
3. `LongHorizonModel._generate` 组装锚点（仅 ACTION 与 terminal 两条生成路径均用）：
   逐字、无解释、无任务解析——
   ```
   AUTHORITATIVE REQUEST (verbatim — reproduce every literal path, key name, ordering,
   and byte-level formatting, including trailing newlines, EXACTLY as written; verify your
   artifact against this text before completing):
   {state.goal.request}
   CONSTRAINTS: {state.goal.constraints}
   ```
   仅注入 `state.goal.request` 与 `constraints` 的逐字内容（与根引导块同源），不含 manifest、
   不含隐藏验收、不含控制器判断。
4. 预算保护（防 FN）：`_generate` 若发现 `checkpoint.token_count + anchor_tokens` 超输入
   预算，则**本回合跳过锚点**并记 `policy_reason="anchor_skipped_budget"`；其余回合照常。
5. 采样：`_SAMPLING` 保持 R119 字节精确（temp0.05 等），本轮**不动采样**。

### 明确不做 / 红线兼容

- 不解析任务文本、不抽取「目标路径/键名」（那会是控制器解释任务）；只逐字重申整段请求。
- 不读隐藏验收、不加 reviewer/judge/Task/projection；控制器不选工具、不填参、不改 Final。
- 不折叠 append 历史（那是 R123 变量，已 INVALID）；锚点是生成期后缀，不入持久抄本。
- transport 诚实标注 prompt_replay；审计暴露锚点 token 与 effective prompt token。

## KEEP 门槛（因果归因 + 噪声感知，基线 = Round119；单run方差 ±3）

1. **G1 字节精确对照组** B01/B06/B13/B19/B28 = **5/5**（本变量重申精确规格，若反而打坏
   字节精确即机制反噬，从严要求满分）；
2. **G2 Strict ≥ 32**（R119 30 + 超噪声增益；且 > Round46 历史最好 31）；
3. **G3 FP ≤ 31**（自 36 实降 ≥5；字面保真的直接检验，方向必须向下）；
   —— G2 与 G3 为**联合**必要条件：Strict 升 **且** FP 降，二者同时越过噪声才算真改进；
4. **G4 FN ≤ 1** 且 90/90 终态完整、0 running（锚点预算保护须生效，不得制造中断）；
5. **G5 R119-TP 保留 ≥ 28/30**（邻接锚点不得打坏已过题，损失 ≤2 计噪声）。
期望（非 KEEP 条件）：字面漂移型 FP（B04/B05/B11/B22/LH04/M08/LH09/M15/M16 …）FP→TP。
若 KEEP 且 Strict > 31 → 追加 unchanged-source confirmatory 再判最终 KEEP，然后 git checkpoint。

## 前置与冻结

基线 = Round119。其余与 R119–124 一致：model `rwkv7-g1i-13.3b-20260805-ctx16384`、
endpoint `http://127.0.0.1:29610/v1`、max-transitions 200、concurrency 1、uv 0.12.5、suite all（90）。

## 流程

1. 实现 C1（model_session.py + model.py）；离线回归：锚点插入位置/预算跳过、审计新字段、
   ACTION 与 terminal 两路径均注入、持久 transcript_digest 不变；全量 pytest、catalog 90/90、
   compileall、diff check。
2. 冻结只读 source manifest（temp/generate_round125_*_source_manifest.py，--check）→
   Full90 一次 → `Round125_v19p0_full90/` 完整产出（REPORT、results、cases、
   MANUAL_CAUSAL_ANALYSIS 含三向 flip + 字面漂移 FP 逐题核对 + 字节精确/代码链逐题 +
   锚点生效/跳过统计）→ KEEP/REVERT。REVERT 则字节回退两文件至 R119 冻结值。
