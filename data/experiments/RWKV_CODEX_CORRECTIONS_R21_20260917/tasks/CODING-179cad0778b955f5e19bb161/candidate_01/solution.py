import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,q=v[:2];books=sorted(v[2:2+n]);out=[]
for i in range(q):
 length,code=v[2+n+2*i:4+n+2*i];mod=10**length;out.append(str(next((x for x in books if x%mod==code),-1)))
print('\n'.join(out))
