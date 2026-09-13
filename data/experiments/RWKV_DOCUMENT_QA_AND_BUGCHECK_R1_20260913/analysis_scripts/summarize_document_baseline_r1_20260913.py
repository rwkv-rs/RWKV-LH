from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
groups=json.loads((D/'GROUPS.json').read_text());mechanical=json.loads((D/'MECHANICAL.json').read_text());summary=json.loads((D/'TASK_SUMMARY.json').read_text());rows=[]
all_refs=set();disjoint=True
for p in sorted((D/'runs').iterdir()):
    state=json.loads((p/'execution/state_snapshot.json').read_text());refs={v['native_state_ref'] for v in state['model_states'].values()};disjoint=disjoint and not(refs&all_refs);all_refs.update(refs)
for arm,stats in summary['arms'].items():
    selected=[g for g in groups if g['mode']==arm];elapsed=sum(g['elapsed_seconds'] for g in selected)
    rows.append({'arm':arm,'batch_seconds':[g['elapsed_seconds'] for g in selected],'total_batch_seconds':elapsed,'met':stats['met'],'delivered':stats['delivered'],'accepted_tasks_per_hour':stats['met']/elapsed*3600,'all_attempts_calls_per_accepted':stats['diagnostics']['model_calls']/stats['met'] if stats['met'] else None})
result={'task_level':summary['arms'],'performance':rows,'state_refs_disjoint_across_independent_tasks':disjoint,'checkpoint_count':len(all_refs),'generations':mechanical['checked_generations'],'state_and_exact_input_checks':True,'resource_limits':{'money':'unknown: no verified unit prices; not zero','peak_exclusive_gpu':'not measured','compute':'logical full prompt tokens are not physical prefill compute under native State','confounds':['local full regression suite overlapped part of serial repeat1','service request/global State locks serialize work','small fixed task group and unequal quality; not a concurrency benefit claim']},'mutation_count':0,'false_work_claim_count':0,'stability_passed':False,'original_read_regression':'not rerun in this round; no stability claim','input_boundary':'no unused JSON opener before User turn in all59 reconstructed inputs','assessment_caveat':'one rules answer is useful and faithful but frozen contract bundled overlap detail into essential material item; retain partially_met, do not reinterpret as model inability'}
(D/'BASELINE_SUMMARY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rows,ensure_ascii=False))
