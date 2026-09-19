import sys,math
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);k=[next(it) for _ in range(n)];edges=[];period=1
for _ in range(n):
 m=next(it);period=math.lcm(period,m);edges.append([next(it)-1 for _ in range(m)])
answer=array('h',[0])*(n*period);out=[]
for _ in range(next(it)):
 vertex=next(it)-1;c=next(it)%period;state=vertex*period+c;path=[]
 while answer[state]==0:
  answer[state]=-1;path.append(state);vertex,c=divmod(state,period);c=(c+k[vertex])%period;state=edges[vertex][c%len(edges[vertex])]*period+c
 if answer[state]>0:result=answer[state]
 else:
  begin=path.index(state);result=len({s//period for s in path[begin:]})
 for s in path:answer[s]=result
 out.append(str(result))
print('\n'.join(out))
