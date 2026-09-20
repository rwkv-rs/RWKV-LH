import sys,itertools
from array import array
def integers():
 for line in sys.stdin.buffer:
  for token in line.split():yield int(token)
it=integers();n=next(it);weights=array('I',itertools.islice(it,n));q=next(it);head=array('i',[-1])*(n+1);nxt=array('i');starts=array('I');answer=array('Q',[0])*q
for i in range(q):
 a=next(it)-1;b=next(it);starts.append(a);nxt.append(head[b]);head[b]=i
for step in range(1,n+1):
 ids=[];i=head[step]
 while i>=0:ids.append(i);i=nxt[i]
 if not ids:continue
 ids.sort(key=lambda i:(starts[i]%step,-starts[i]));residue=-1;upper=n;total=0
 for i in ids:
  start=starts[i];current=start%step
  if current!=residue:residue=current;upper=n;total=0
  total+=sum(weights[start:upper:step]);upper=start;answer[i]=total
sys.stdout.write('\n'.join(map(str,answer)))
