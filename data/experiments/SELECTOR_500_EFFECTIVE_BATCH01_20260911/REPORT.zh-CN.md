# SELECTOR_500_BATCH01_20260911

Agent：Strict 0/12、completed 0/12、42 动作、1 次实际文件变更；12 题均 identical_success_budget_exhausted。原评分未改。2194.052 秒完成，冻结生产源码3ae1efcc全程未变。

Selector：60 条自动候选，78 条待审全部完成独立双AI复核；共同保留原标签7、共同纠正54、拒绝17。原始输出不改，拒绝记录保留。12来源均通过交接核验，新来源没有使用waiver。

全量旧来源256行加本批121行，共377行按原byte 5-gram cosine 0.95/边界聚类政策去重，保留33行：train28/dev3/confirmation2；12独立边界，其中train10。比上轮净增9行。5个固定评测anchor不变，execute覆盖3。逐组来源真实重放、候选逐字节匹配、33行normalize均通过，status=valid。

Owner最新目标是至少500条有效Selector训练行、至少167个独立训练边界，固定验证另计；尚缺472训练行/157训练边界。旧30行门槛不再用于启动首训。freeze/smoke/train均未执行，optimizer steps=0，未创建正式数据版本，未启动Executor阶段。

5ff6ed4a路径工程及1480passed证据已push，但本批仍固定3ae1efcc。旧waiver不覆盖5ff6ed4a；进入新源码需要单独部署身份和精确范围复核。第二批保持登记的原源码/题集/模型/预算，正在采集。

沿用现有生产trace抽取与selected-source管线。抽取不调用模型，耗时主要来自新真实运行且重复边界产出率低；同时盘点更早同协议来源，避免重复采集。完整原始运行工件保存在本地并在COMPLETED_EVIDENCE_SHA256.json逐文件pin；不把含私有验收的大型原始audit加入Git。无Holdout读取。
