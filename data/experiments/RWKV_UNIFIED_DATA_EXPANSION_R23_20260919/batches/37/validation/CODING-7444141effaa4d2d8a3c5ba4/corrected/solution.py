import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=list(zip(v[1::2],v[2::2]));size=652;freq=[array('i',[0])*651 for _ in range(651)]
for x,y in points:freq[x][y]+=1
pre=[array('i',[0])*size for _ in range(size)]
for x in range(651):
 row=pre[x+1];old=pre[x];running=0
 for y in range(651):running+=freq[x][y];row[y+1]=old[y+1]+running
out=[]
for x,y in points:
 higher=n-pre[x+1][651]-pre[651][y+1]+pre[x+1][y+1];lower=pre[x][y]
 # Equality at the650-pointscoregap preventsstrictoutranking evenwithoutdominance.
 tied_gap=(freq[x][0] if y==650 else 0)+(freq[0][y] if x==650 else 0)
 out.append(str(higher+1)+' '+str(n-lower-tied_gap))
print('\n'.join(out))
