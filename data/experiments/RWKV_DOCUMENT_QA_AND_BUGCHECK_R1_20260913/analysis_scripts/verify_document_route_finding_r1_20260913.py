from pathlib import Path
import json,subprocess,socket,sys,time,urllib.request,urllib.error
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
api=D/'external_verification/api'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
p=subprocess.Popen([sys.executable,str(api/'server.py'),'--db',str(api/'route_check.sqlite'),'--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    for _ in range(100):
        try:urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=.2).close();break
        except OSError:time.sleep(.02)
    rows=[]
    for route in ['/bookings','/bookings/test-id']:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}{route}',timeout=2) as response:status=response.status;body=response.read().decode()
        except urllib.error.HTTPError as e:status=e.code;body=e.read().decode()
        rows.append({'method':'GET','route':route,'status':status,'body':body});assert status==501
finally:p.terminate();stdout,stderr=p.communicate(timeout=10)
(D/'external_verification/ROUTE_FINDING.json').write_text(json.dumps({'observed':rows,'supports':'RWKV budget_probe api_bug serial r2 finding: documented business GET routes not implemented','scope':'external verifier, not sent to RWKV'},ensure_ascii=False,indent=2)+'\n');print(rows)
