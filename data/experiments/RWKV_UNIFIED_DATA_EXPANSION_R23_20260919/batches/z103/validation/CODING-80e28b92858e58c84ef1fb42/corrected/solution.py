import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));n,m1,m2,r=v[:4];p=4;pairs=[];triples=[]
for _ in range(m1):a,b=v[p:p+2];p+=2;pairs.append((1<<(a-1),1<<(b-1)))
for _ in range(m2):a,b,c=v[p:p+3];p+=3;triples.append((1<<(a-1),1<<(b-1),1<<(c-1)))
if r>=n:print('1 1');raise SystemExit
if r<=0:print('-1 0');raise SystemExit
size=1<<n;full=size-1;valid=[]
for state in range(size):
 if any(bool(state&a)!=bool(state&b) for a,b in pairs):continue
 if any(bool(state&a)!=bool(state&b) and bool(state&a)!=bool(state&c) for a,b,c in triples):continue
 valid.append(state)
def transform(a):
 step=1
 while step<size:
  block=step*2
  for start in range(0,size,block):
   for i in range(start,start+step):x=a[i];y=a[i+step];a[i]=x+y;a[i+step]=x-y
  step=block
spectral=[]
for s in range(n+1):
 value=0
 for moved in range(1,r+1):
  for j in range(max(0,moved-(n-s)),min(s,moved)+1):value+=(-1 if j&1 else 1)*math.comb(s,j)*math.comb(n-s,moved-j)
 spectral.append(value)
eigen=[spectral[i.bit_count()] for i in range(size)];frontier=[0]*size;frontier[0]=1;unseen=set(valid);unseen.remove(0);distance=0
while unseen:
 distance+=1;transform(frontier)
 for i in range(size):frontier[i]*=eigen[i]
 transform(frontier)
 if frontier[full]:print(distance,frontier[full]//size);break
 next_frontier=[0]*size;reached=[]
 for state in unseen:
  count=frontier[state]//size
  if count:next_frontier[state]=count;reached.append(state)
 if not reached:print('-1 0');break
 unseen.difference_update(reached);frontier=next_frontier
else:print('-1 0')
