from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');C=R/'data/experiments/FULL_TRACE_CAMPAIGN_R2_20260911';O=R/'data/experiments/FULL_TRACE_COLLECTION_R2_20260911';D=R/'data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((D/'ACTIVATION.json').read_text());a['health_validation']='passed';a['health_evidence']={'path':str(O/'all_zero/runtime_doctor.json'),'sha256':sha(O/'all_zero/runtime_doctor.json')};(D/'HEALTH_VERIFIED.json').write_text(json.dumps(a,indent=2)+'\n')
for k in ['freeze','upload']:
 p=R/f'temp/{k}_full_trace_deployment_r2_20260911.py';shutil.copyfile(p,D/('EVIDENCE_SCRIPT_'+p.name))
shutil.copyfile(Path(__file__),C/('EVIDENCE_SCRIPT_'+Path(__file__).name))
(C/'REPORT.zh-CN.md').write_text('''# 最新信息流协议部署与全题集重测 R2

Agent：本轮实际开始0/117，无新Strict/completed/mutation分数。Selector等角色新trace为0，optimizer steps=0。阻塞是官方Planner账户余额不可用，启动前余额门已拒绝采集，未把117题制造为模型失败。

Owner授权重新部署最新修改并重测、以最新源码作为trace。冻结de029c88，ROLE_INFORMATION_FLOW_REPAIR_R1；1502 passed、0 skipped，249.51秒。新隔离工作树/home/chase/GitHub/RWKV-LH-full-trace-r2-20260911。当前角色Selector/Executor/Step Auditor v7、Finalizer v3、Final Auditor v5、feedback v2；旧协议不重放、不用waiver伪装准入，旧State不复用，模型权重不变且角色全zero。

132项目文件和6393engine文件的完整清单已冻结上传并逐文件核验。远端根/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911，服务器没有使用Git。项目SHA733fdcb5c63bfe94ac5743b68baf530d61215cf34ac44fba3d6fb0dde8d99f6b，engine SHA016d3ac4af9c5eca71fa27b82d3fe71d4e029314bee3f0c1a1513bc00b839693，decoder SHAcb204ccf5ae744591a9cb32eb3f5cab2250d02f79519cc2bd7d1f12cad85d1cb。

两个current服务已切换并健康通过。冷启动期间首次preflight连接重置，保存在PREPARATION_ATTEMPT01，未发生模型生成；服务完成加载后重新核验通过。canonical .env.local四项公开Selector身份配置已更新到当前decoder/协议，密钥未变、未记录。driver使用同一冻结身份。

117道独立公开题、119个题集成员与R1完全相同，2个重复任务及验收完全相等只跑一次，固定题序；200 transitions、单题1800秒、单并发、总210600秒上限、Executor1800保持。增加运行前官方余额门，以及实际题目返回HTTP402后暂停剩余队列的规则。这是基础设施失败调度差异，提前登记，不改题目评分。旧R1已自然结束，未杀进程、未删除原始trace；R1的77题Planner402和LH09无trace继续保留，不冒充RWKV能力失败。

当前重测已完成register/完整服务健康/源码冻结；collect在余额门拒绝，BLOCKED_BEFORE_GENERATION.json为收据，无STARTED.json。充值后执行：

```bash
cd /home/chase/GitHub/RWKV-LH-full-trace-r2-20260911
/home/chase/GitHub/RWKV-LH/.venv/bin/python /home/chase/GitHub/RWKV-LH/temp/run_full_trace_collection_r2_20260911.py collect
```

该命令再次核验冻结身份和实时官方余额后才生成。需要的只是外部余额恢复，不需要改源码、重新生成任务或改协议。成功启动后保留此前余额拒绝证据，另写STARTED/逐题PROGRESS/最终COMPLETION。新trace单独保存在FULL_TRACE_COLLECTION_R2_20260911/all_zero。

本轮旧角色训练样本不自动获得新协议valid身份，后续数据只从新生产trace按当前builder抽取并验证；不宣称旧57行仍可用于当前协议训练。没有启动StateTune或创建正式datasets版本，没有读取Holdout。
''')
h=R/'docs/HANDOFF.zh-CN.md';s=h.read_text().replace('# 当前交接\n','# 当前交接\n\n## 2026-09-11 最新de029c88部署完成，R2重测等待Planner余额\n\n已按owner授权上传最新信息流修复及唯一新协议，132/6393文件清单核验、两模型服务健康通过；1502 passed。117道公开任务与原顺序已登记，当前实际开始0/117，无新Agent分数/角色trace，optimizer steps=0。官方余额接口确认不可用，collect被运行前余额门拒绝，未生成整批402失败。充值后可直接执行既有R2 collect；运行中402将暂停剩余队列。新旧trace分目录，不把旧协议数据视为当前valid。[部署和启动说明](../data/experiments/FULL_TRACE_CAMPAIGN_R2_20260911/REPORT.zh-CN.md)。\n',1);h.write_text(s)
paths=[p for p in C.iterdir() if p.is_file()]+[p for p in D.iterdir() if p.is_file()]+[p for p in O.rglob('*') if p.is_file()]
(C/'DEPLOYMENT_EVIDENCE_SHA256.json').write_text(json.dumps({str(p.relative_to(R)):sha(p) for p in sorted(paths)},indent=2)+'\n');print('evidence',sha(C/'DEPLOYMENT_EVIDENCE_SHA256.json'))
