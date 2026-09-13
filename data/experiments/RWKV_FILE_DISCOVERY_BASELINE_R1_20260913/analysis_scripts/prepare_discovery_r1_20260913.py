from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D.mkdir(exist_ok=False)
shutil.move('/tmp/rwkv-lh-discovery-env.log',D/'ENVIRONMENT.log')
old=R/'temp/run_direct_candidate_tasks_r2_20260913.py';s=old.read_text();s=s.replace("P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation_r2';S=P/'training_runtime/source_r2'","P=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D=P;S=P/'source'")
a=s.index('def used_calls():');b=s.index('def run(split):',a);s=s[:a]+"def used_calls():\n return sum(sum(json.loads(line)['type']=='model_session_generation_started' for line in f.read_text().splitlines()) for f in (D/'dev').rglob('model_trace.jsonl'))\n"+s[b:]
s=s.replace("(['zero','candidate'] if repeat==1 else ['candidate','zero'])","['zero']").replace('used_calls()>=200','used_calls()>=48').replace('time.time()-started<5400','time.time()-started<3600')
(R/'temp/run_discovery_r1_20260913.py').write_text(s)
v=(R/'temp/verify_summary_advice_server_r3_20260913.py').read_text().replace('RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913','RWKV_FILE_DISCOVERY_BASELINE_R1_20260913');(R/'temp/verify_discovery_server_r1_20260913.py').write_text(v)
for folder in ['rwkv_lh','scripts']:
 shutil.copytree(R/folder,D/'source'/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for f in ['pyproject.toml','uv.lock']:shutil.copy2(R/f,D/'source'/f)
old=json.loads((R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/PREEXISTING_FINAL_PRESERVED.json').read_text());assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==h for f,h in old.items());(D/'PREEXISTING.json').write_text(json.dumps(old,indent=2)+'\n')
p=R/'docs/RWKV_CODING_AGENT_HARNESS_V1.zh-CN.md';t=p.read_text();a=t.index('状态：');b=t.index('\n\n## 1.',a);t=t[:a]+'状态（2026-09-13更新）：产品是RWKV专属Agent Harness与以RWKV为主要执行模型的Code Agent。第一版职责保持，实际实现与实验状态以HANDOFF为准；已完成读取/摘要和两轮StateTune，当前推进自主定位文件的只读基线。本轮不追加训练、不新建数据集版本、不更新GitHub。'+t[b:];t=t.replace('产品是以 RWKV 为主要执行模型、强模型按需补足能力的编程 Agent。','最终目标是为RWKV构建适合其State机制、输入组织和执行特点的专属Agent Harness，做出以RWKV为主要执行模型、强模型按需补足能力的可用Code Agent。成本、交付时间与吞吐是该产品在质量达标前提下的优化属性，不是最终产品目标；StateTune是改进手段。');p.write_text(t)
print(D)
