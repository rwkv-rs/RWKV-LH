import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
while True:
 n=next(v);q=next(v)
 if n==q==0:break
 weights=[next(v) for _ in range(n)];bits=[0]*(n+1);bits[0]=1;total=sum(weights)
 for i,w in enumerate(weights):
  for count in range(i+1,0,-1):bits[count]|=bits[count-1]<<w
 for _ in range(q):
  target=next(v);answer=[str(count) for count in range(n+1) if 0<=target<=total and (bits[count]>>target)&1];out.append(' '.join(answer) if answer else "That's impossible!")
print('\n'.join(out))
