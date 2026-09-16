from pathlib import Path
import requests,json,time,concurrent.futures,sys
root=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916/outputs/runs')
bodies=[]
for name in ['CODING-1400bfe58d4dd04e44f48a99','CODING-04f55c8b3331a95a7f6e9db7']:
 events=[json.loads(l) for l in (root/name/'execution/strong_trace.jsonl').read_text().splitlines()]
 b=[e['body'] for e in events if e['type']=='strong_execution_wire_request'][1]
 b.update(max_tokens=256,ignore_eos=True,seed=18);bodies.append(b)
def run(b):
 s=requests.Session();s.trust_env=False;t=time.monotonic();r=s.post('http://127.0.0.1:18244/v1/chat/completions',json=b,timeout=180);r.raise_for_status();return {'seconds':time.monotonic()-t,'response':r.json()}
out={'arm':sys.argv[1],'requests':bodies,'rounds':[]}
for i in range(3):
 t=time.monotonic()
 with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(run,bodies))
 elapsed=time.monotonic()-t;out['rounds'].append({'seconds':elapsed,'tokens_per_second':sum(x['response']['usage']['completion_tokens'] for x in results)/elapsed,'results':results})
 print(i,elapsed,out['rounds'][-1]['tokens_per_second'],flush=True)
Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=2))
