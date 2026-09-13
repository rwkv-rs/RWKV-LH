from pathlib import Path
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
s=(R/'temp/audit_direct_candidate_tasks_r2_20260913.py').read_text().replace("P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation_r2';sys.path.insert(0,str(P/'training_runtime/source_r2'))","P=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913';D=P;sys.path.insert(0,str(P/'source'))")
s=s.replace('from rwkv_lh.harness import ActionHarness','from rwkv_lh.harness import ActionHarness\nimport importlib.util\nspec=importlib.util.spec_from_file_location("menu_runner",R/"temp/run_input_menu_r1_20260913.py"); runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)')
s=s.replace('harness=ActionHarness());goal=',"harness=(runner.ReadOnlyMenuHarness() if r['arm']=='readonly' else ActionHarness()));goal=")
s=s.replace("'actual_input_sha256':sha_text(tokenizer().decode(ids))", "'actual_input_sha256':sha_text(tokenizer().decode(ids)),'root_non_menu_sha256':sha_text(bootstrap.split('\\n',1)[1])")
s=s.replace("digest=r['calls'][0]['actual_input_sha256']","digest=r['calls'][0]['root_non_menu_sha256']").replace('initial arm inputs differ','non-menu initial input differs')
s=s.replace("key=sha_text('candidate-task-r2:'","key=sha_text('input-menu-r1:'").replace("'final':r['final']}","'final':r['final'],'observations':[__import__('json').loads(q.read_text()) for q in sorted(p.glob('observation_*.json'))]}")
exec(compile(s,str(R/'temp/audit_direct_candidate_tasks_r2_20260913.py'),'exec'),{})
