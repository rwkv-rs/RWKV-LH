import sys
lines=sys.stdin.read().splitlines();ops=[line.split() for line in lines[1:] if line.strip()];values=sorted({int(op[1]) for op in ops if len(op)>1});index={x:i for i,x in enumerate(values)};size=1
while size<len(values):size*=2
counts=[0]*(size*2);sums=[[0]*5 for _ in range(size*2)];out=[]
for op in ops:
 if op[0]=='sum':out.append(str(sums[1][2]));continue
 x=int(op[1]);p=size+index[x];counts[p]=int(op[0]=='add');sums[p]=[x,0,0,0,0] if counts[p] else [0]*5;p//=2
 while p:
  left=p*2;right=left+1;shift=counts[left]%5;counts[p]=counts[left]+counts[right];sums[p]=[sums[left][j]+sums[right][(j-shift)%5] for j in range(5)];p//=2
print('\n'.join(out))
