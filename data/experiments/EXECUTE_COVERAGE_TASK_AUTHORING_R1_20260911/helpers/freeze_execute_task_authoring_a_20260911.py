from pathlib import Path
import hashlib,json,subprocess,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
O=R/'data/experiments/EXECUTE_COVERAGE_TASK_AUTHORING_R1_20260911';B=R/'benchmarks/rwkv_e2e/rwkv_execute_diagnostics_v1';A=R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
new=json.loads((B/'tasks.json').read_text());old=json.loads((R/'benchmarks/rwkv_e2e/rwkv_real_project_dev_v1/tasks.json').read_text())
for t in new['tasks'][:2]:assert t==next(x for x in old['tasks'] if x['task_id']==t['task_id'])
newacc=json.loads((B/'acceptance.json').read_text());oldacc=json.loads((R/'benchmarks/rwkv_e2e/rwkv_real_project_dev_v1/acceptance.json').read_text())
for k in ['RP-CLI-01','RP-WEB-02']:assert newacc['cases'][k]==oldacc['cases'][k]
v=json.loads((O/'AUTHOR_VALIDATION_V3.json').read_text())
assert len(v['cases'])==15
assert all(c['passed']==(c['variant']=='reference') for c in v['cases'])
write(B/'MANIFEST.json',{'schema_version':'rwkv-execute-diagnostics-v1.manifest.v1','suite':'executediagnosticsv1','owner_authorization':'2026-09-11 explicitly delegate two diagnose-first tasks finalization, register, collect round A','registration_api':'scripts.run_rwkv_e2e_benchmark.SuiteDefinition / SUITES / load_suite; fixed twelve-task freeze_project_benchmark CLI is not applicable to this four-task suite','task_ids':[t['task_id'] for t in new['tasks']],'controls_byte_equivalent':True,'files':{n:sha(B/n) for n in ['__init__.py','tasks.json','acceptance.json','audit_binding.py']},'validation_path':str(O/'AUTHOR_VALIDATION_V3.json'),'validation_sha256':sha(O/'AUTHOR_VALIDATION_V3.json'),'author_references':{str(p.relative_to(O)):sha(p) for p in sorted(O.glob('NEW-DIAG-*/*')) if p.is_file()},'acceptance_limit':'Final immutable file identities and real failure/success command stdout are checked; temporary tampering followed by restoration is not fully attested. This is not an adversarial execution-history security benchmark.','private_feedback_available_to_agent':False,'author_fixtures_are_training_sources':False,'holdout_accessed':False})
A.mkdir(exist_ok=False)
d=json.loads((R/'data/experiments/EXECUTE_COVERAGE_PREREG_R1_20260911/ROUND_A_PREREGISTRATION_DRAFT.json').read_text())
d.update(round_id=A.name,status='registered_before_generation',task_ids=[t['task_id'] for t in new['tasks']],production_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),task_bundle_manifest_sha256=sha(B/'MANIFEST.json'),driver_sha256=sha(R/'temp/run_execute_coverage_a_20260911.py'),deployment_manifest_sha256=sha(R/'data/experiments/EXECUTE_COVERAGE_DEPLOYMENT_A_20260911/PROJECT_SOURCE.json'))
d['task_content']={'NEW-DIAG-01':'Cache TTL expiry boundary; 4 public tests, exactly one failure; generalized TTL/clock private probes.','NEW-DIAG-02':'Stock signed-movement aggregation; 4 public tests, exactly one failure; ordering, zero totals, iterable and immutable-input private probes.'}
d['acceptance_limit']='Trusted command stdout exact report matching and final pinned tests/helper; not full hostile intermediate-history attestation.'
write(A/'ROUND_A_PREREGISTRATION.json',d)
write(O/'PUSH_VERIFICATION.json',{'remote_branch':'chase/rwkv-goal-loop-v2-cleanup','remote_head':'c6b46d0185b4b5c8e6df358128b20ad46d0776ad','explicit_owner_authorized_push':True,'full_regression':'1464 passed, zero skipped/failed','pytest_sha256':sha(O/'PYTEST.log')})
print('Task manifest and A preregistration frozen')
