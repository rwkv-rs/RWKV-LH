import sys
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);d=next(v);a=[next(v)-1 for i in range(n)]
 if any((x-i)%d for i,x in enumerate(a)):out.append('-1');continue
 answer=0
 for r in range(d):
  group=a[r::d];bit=[0]*(len(group)+1);seen=0
  for x in group:
   p=x//d+1;z=p;count=0
   while z:count+=bit[z];z-=z&-z
   answer+=seen-count;seen+=1
   while p<len(bit):bit[p]+=1;p+=p&-p
 out.append(str(answer))
print('\n'.join(out))
