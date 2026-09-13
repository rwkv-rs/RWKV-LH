from pathlib import Path
import sys,json
R=Path('/home/chase/GitHub/RWKV-LH');sys.path[:0]=[str(R),str(R/'tests')]
from test_read_only_agent import factory,settings
from test_unified_controller import call
from rwkv_lh.read_only_agent import ReadOnlyJob,run_read_only_job
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913/offline_reconsideration';D.mkdir();w=D/'workspace';w.mkdir();(w/'doc.md').write_text('source')
a=ReadOnlyJob('first','read',str(w),str(D/'first'));run_read_only_job(a,settings=settings(),session_factory=factory([call('read_file',path='doc.md'),call('final_answer',text='old')]))
b=ReadOnlyJob('new','read',str(w),str(D/'new'),reconsider_from=str(D/'first'),advice='check',advice_model='test')
r=run_read_only_job(b,settings=settings(),session_factory=factory([call('final_answer',text='new')]));print(r['error']);print(r['final']);s=json.load(open(D/'new/state_snapshot.json'));print([(s['causal_records'][k]['event_type'],s['causal_records'][k]['payload']) for k in s['causal_order'][-5:]])
