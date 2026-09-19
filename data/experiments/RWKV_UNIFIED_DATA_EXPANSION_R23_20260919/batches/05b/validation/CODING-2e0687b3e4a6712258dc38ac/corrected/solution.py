import sys
it=iter(sys.stdin.buffer.read().split());n=int(next(it));q=int(next(it));s=next(it);size=1
while size<n:size*=2
g=[(0,0,0,0,0,0)]*(2*size)
def leaf(c):return (int(c==97),int(c==98),int(c==99),0,0,0)
def merge(l,r):
 a,b,c,ab,bc,abc=l;d,e,f,de,ef,def_=r
 return a+d,b+e,c+f,min(a+de,ab+e),min(b+ef,bc+f),min(a+def_,ab+ef,abc+f)
for i,c in enumerate(s):g[size+i]=leaf(c)
for i in range(size-1,0,-1):g[i]=merge(g[2*i],g[2*i+1])
out=[]
for _ in range(q):
 p=int(next(it))-1+size;c=next(it)[0];g[p]=leaf(c);p//=2
 while p:g[p]=merge(g[2*p],g[2*p+1]);p//=2
 out.append(str(g[1][5]))
print('\n'.join(out))
