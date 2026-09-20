import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];events={2:[],m+1:[]}
for i in range(n):
 row,l,r=v[2+3*i:5+3*i];events.setdefault(l,[]).append((row-1,1));events.setdefault(r+1,[]).append((row-1,-1))
mod=1000000007
def multiply(a,b):return tuple(sum(a[3*i+k]*b[3*k+j] for k in range(3))%mod for i in range(3) for j in range(3))
powers={}
def apply(state,mask,length):
 if mask not in powers:
  mat=tuple(int(abs(i-j)<=1 and not(mask>>i&1)) for i in range(3) for j in range(3));p=[mat]
  for _ in range(m.bit_length()):p.append(multiply(p[-1],p[-1]))
  powers[mask]=p
 bit=0
 while length:
  if length&1:
   a=powers[mask][bit];state=tuple(sum(a[3*i+j]*state[j] for j in range(3))%mod for i in range(3))
  bit+=1;length>>=1
 return state
active=[0]*3;state=(0,1,0);points=sorted(events)
for x,y in zip(points,points[1:]):
 for row,delta in events[x]:active[row]+=delta
 mask=sum(1<<r for r in range(3) if active[r]>0);state=apply(state,mask,y-x)
print(state[1])
