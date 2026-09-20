import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));M,N=v[:2];freq=[0]*M
for x in v[2:]:freq[x]+=1
r=M;depth=0
for prime in (2,5):
 exponent=0
 while r%prime==0:r//=prime;exponent+=1
 depth=max(depth,exponent)
answer=sum(count*((-x)%M) for x,count in enumerate(freq))
for step in range(depth):
 following=[0]*M
 for x,count in enumerate(freq):following[x*10%M]+=count
 freq=following;answer=min(answer,step+1+sum(count*((-x)%M) for x,count in enumerate(freq)))
if r==1:print(answer);raise SystemExit
g=M//r;seen=bytearray(r);by_length={};period=1
for start in range(r):
 if seen[start]:continue
 cycle=[];x=start
 while not seen[x]:seen[x]=1;cycle.append(x);x=x*10%r
 L=len(cycle);period=math.lcm(period,L);weights=[freq[g*x] for x in cycle]
 if not any(weights):continue
 values=[(-g*x)%M for x in cycle]
 if L==1:contribution=[weights[0]*values[0]]
 else:
  # Any coefficient is <= N*M <= 10^10, below the 40-bit lane width.
  left=int.from_bytes(b''.join(w.to_bytes(5,'little') for w in weights[::-1]),'little')
  right=int.from_bytes(b''.join(w.to_bytes(5,'little') for w in values+values[:-1]),'little')
  product=(left*right).to_bytes((3*L-2)*5,'little');contribution=[int.from_bytes(product[5*(L-1+k):5*(L+k)],'little') for k in range(L)]
 if L in by_length:
  acc=by_length[L]
  for k in range(L):acc[k]+=contribution[k]
 else:by_length[L]=contribution
cost=[depth+k for k in range(period)]
for L,values in by_length.items():
 for start in range(0,period,L):
  for k,value in enumerate(values):cost[start+k]+=value
print(min(answer,min(cost)))
