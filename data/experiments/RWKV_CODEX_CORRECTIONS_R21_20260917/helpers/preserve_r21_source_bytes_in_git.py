from pathlib import Path
import subprocess,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';tasks=list((D/'tasks').glob('*/TASK.md'))
def mismatches():
 process=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE);bad=[]
 for p in tasks:
  rel=str(p.relative_to(R));process.stdin.write((':'+rel+'\n').encode());process.stdin.flush();header=process.stdout.readline().split();size=int(header[-1]);blob=process.stdout.read(size);assert process.stdout.read(1)==b'\n'
  if blob!=p.read_bytes():bad.append({'path':rel,'working_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'index_sha256':hashlib.sha256(blob).hexdigest()})
 process.stdin.close();process.wait();return bad
before=mismatches();assert len(before)==92,len(before)
(D/'.gitattributes').write_text('tasks/**/TASK.md -text\n')
subprocess.run(['git','add',str(D/'.gitattributes')],check=True);subprocess.run(['git','add','--renormalize',str(D/'tasks')],check=True);after=mismatches();assert not after,after
(D/'GIT_SOURCE_BYTE_REGRESSION.json').write_text(json.dumps({'scope':'Only R21 copied source TASK.md; no global attributes changed','before_mismatches':len(before),'after_mismatches':len(after),'checked_tasks':len(tasks),'reason':'Repository text=auto normalized mixed CRLF, breaking sealed source SHA; per-experiment -text preserves exact source bytes','before':before},indent=2));print('Git source byte check:',len(before),'mismatches ->',len(after))
