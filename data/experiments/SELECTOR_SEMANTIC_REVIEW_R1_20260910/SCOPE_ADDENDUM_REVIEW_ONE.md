# AI reviewer one：语义复核附件绑定审查

决定：accept，精确绑定SCOPE_ADDENDUM_APPROVAL_ONE.json所列proposal与wrapper SHA。仅审查转换与范围；没有修改原独立决定或重新争取一致。

Agent级：没有新Agent运行/成绩；本附件不能代表Strict、completed、mutation或终止改善。角色级：独立重新对账126行，34原标签一致、68纠正一致、24否决/不一致；204条human_reviews逐字段等于两名原始决定转换，24条拒绝行没有任何复核准入附件。pending=0表示复核工作已结案，不表示全部行获准，原抽取器可能仍把24条写入review_queue。

已校验所有proposal引用文件SHA、原126行源JSONL身份；按sample_id逐行核对两份独立决定，一票拒绝或操作不一致即reject；每条转换的request/role/source/run/boundary/original_output_record/input SHA/target SHA/purpose/显式纠正target/rationale/reviewer_id/evidence_refs均精确相等。没有添加新证据引用，保留AI身份而不是伪造人工签名。

从derivative registration删除human_reviews字段后，结构精确恢复原14来源注册，其他字段及原artifact pin不变；RP-WEB-02仍排除。waiver SHA仍f53186ec…，为同10文件已批准源码身份映射。wrapper使用显式require/SystemExit、固定selector_intent及新输出，校验全部附件字节、限定结构与双AI对proposal/wrapper SHA的批准；无可覆写scope的CLI透传。

只读核验程序：temp/semantic_one_addendum_check_20260910.py（绝对路径执行）；明细：SCOPE_ADDENDUM_CHECK_ONE.json。没有运行extract、测试或训练，没有更改生产代码、旧签名、评分或原决定。
