import sys
f=sys.stdin.buffer;n,m=map(int,f.readline().split());size=1<<n;skills=[0]+[int(f.readline()) for _ in range(size)];tree=[0]*size+list(range(1,size+1))
for x in range(size-1,0,-1):
 l=tree[x*2];r=tree[x*2+1];tree[x]=l if skills[l]>skills[r] else r
out=[]
for _ in range(m):
 p=f.readline().split()
 if p[0]==b'W':out.append(str(tree[1]))
 elif p[0]==b'R':
  i=int(p[1]);skills[i]=int(p[2]);x=(size+i-1)//2
  while x:
   l=tree[x*2];r=tree[x*2+1];winner=l if skills[l]>skills[r] else r
   tree[x]=winner;x//=2
 else:
  i=int(p[1]);x=(size+i-1)//2;wins=0
  while x and tree[x]==i:wins+=1;x//=2
  out.append(str(wins))
print('\n'.join(out))
