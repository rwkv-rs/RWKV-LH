from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/evaluation_r2'
source=(R/'temp/audit_advice_read_regression_r3_20260913.py').read_text()
for arm in ['zero','candidate']:
 s=source.replace("D=R/'data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913';rd=D/'read_regression'",f"D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/evaluation_r2';rd=D/'read_{arm}'")
 profile=json.loads((D/'RUN_REGISTRATION.json').read_text())['profiles'][arm]
 s=s.replace("b['state_profile_id']=='zero' and b['state_profile_sha256']=='0'*64",f"b['state_profile_id']=={profile['id']!r} and b['state_profile_sha256']=={profile['sha256']!r}")
 exec(compile(s,str(R/'temp/audit_direct_read_r2_20260913.py'),'exec'),{})
summary=json.loads((D/'DEV_SUMMARY.json').read_text());gain=summary['candidate']['task_pass']-summary['zero']['task_pass']
reads={arm:json.loads((D/f'read_{arm}/MECHANICAL_AUDIT.json').read_text()) for arm in ['zero','candidate']}
assert all(len(v)==24 and all(x['passed'] for x in v) for v in reads.values())
gate=dict(passed=False,dev_gain=gain,required_gain=2,original_read_regression={a:dict(passed=sum(x['passed'] for x in v),tasks=len(v),tool_success=sum(x['tool_success'] for x in v),input_state_verified=True) for a,v in reads.items()},reason='Gain 1/8 below preregistered 2/8; no confirmation or production retention. Even permissive scoring of every answer gives gain 0, so borderline summary decisions cannot reverse this gate.',confirmation='not run; no confirmation results inspected',candidate_status='preserved as research artifact, not retained as production default')
p=D/'DEV_GATE.json';assert not p.exists();p.write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n');print(gate)
