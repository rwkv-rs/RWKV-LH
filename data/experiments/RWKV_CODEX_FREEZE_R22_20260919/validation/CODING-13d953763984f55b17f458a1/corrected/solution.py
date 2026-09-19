import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);sums=[[0]*(4*n),[0]*(4*n)];lazy=bytearray(4*n)
def swap(x):sums[0][x],sums[1][x]=sums[1][x],sums[0][x];lazy[x]^=1
def push(x):
 if lazy[x]:swap(x*2);swap(x*2+1);lazy[x]=0
def operate(x,l,r,ql,qr,typ,arr=0,value=0):
 if ql<=l and r<=qr:
  if typ==0:return sums[arr][x]
  if typ==2:swap(x);return 0
  sums[arr][x]=value;return 0
 push(x);mid=(l+r)//2;answer=0
 if ql<=mid:answer+=operate(x*2,l,mid,ql,qr,typ,arr,value)
 if qr>mid:answer+=operate(x*2+1,mid+1,r,ql,qr,typ,arr,value)
 if typ:
  for a in (0,1):sums[a][x]=sums[a][x*2]+sums[a][x*2+1]
 return answer
out=[]
for _ in range(m):
 typ=next(it)
 if typ==2:operate(1,0,n-1,next(it),next(it),2)
 else:
  arr=next(it);l=next(it);r=next(it)
  if typ==0:out.append(str(operate(1,0,n-1,l,r,0,arr)))
  else:operate(1,0,n-1,l,l,1,arr,r)
print('\n'.join(out))
