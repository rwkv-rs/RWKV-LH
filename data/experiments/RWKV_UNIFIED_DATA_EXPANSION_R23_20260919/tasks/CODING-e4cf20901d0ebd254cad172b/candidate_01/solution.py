import sys
v=iter(map(int,sys.stdin.read().split()));n=next(v);k=next(v);a=[[next(v)-1 for j in range(n)] for i in range(n)];u,w=0,1;seen={};actors=[];target=k-1
while (u,w) not in seen:
 seen[u,w]=len(actors);actors.append(u)
 if len(actors)-1==target:print(u+1);raise SystemExit
 u,w=w,a[w][u]
start=seen[u,w];index=start+(target-start)%(len(actors)-start);print(actors[index]+1)
