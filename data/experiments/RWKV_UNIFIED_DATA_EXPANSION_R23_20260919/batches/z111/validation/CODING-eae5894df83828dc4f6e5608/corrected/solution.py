import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];levels=v[1:];last=[0]*(n+1);children=[[] for _ in range(n+1)]
for i,depth in enumerate(levels,1):children[last[depth-1]].append(i);last[depth]=i
stack=children[0][:];permutation=[0]*n;value=0
while stack:
 node=stack.pop();value+=1;permutation[node-1]=value;stack.extend(children[node])
bit=[0]*(n+1);answer=0
for value in reversed(permutation):
 j=value-1;length=0
 while j:
  if bit[j]>length:length=bit[j]
  j-=j&-j
 length+=1;answer+=length;j=value
 while j<=n:
  if bit[j]<length:bit[j]=length
  j+=j&-j
print(answer)
