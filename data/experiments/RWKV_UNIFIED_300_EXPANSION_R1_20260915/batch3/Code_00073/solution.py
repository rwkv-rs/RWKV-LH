import sys
sys.setrecursionlimit(1000000)
a=iter(map(int,sys.stdin.buffer.read().split()));n=next(a);colors=[next(a)-1 for _ in range(n)];g=[[] for _ in range(n)]
for _ in range(n-1):
    u,v=next(a)-1,next(a)-1;g[u].append(v);g[v].append(u)
covered=[0]*n;ans=[n*(n+1)//2]*n
# Components left when a color is removed contain all paths avoiding that color.
def dfs(u,p):
    c=colors[u];before=covered[c];size=1
    for v in g[u]:
        if v==p:continue
        prev=covered[c];child=dfs(v,u);gap=child-(covered[c]-prev)
        ans[c]-=gap*(gap+1)//2;size+=child
    covered[c]=before+size
    return size
dfs(0,-1)
for c in range(n):
    rest=n-covered[c];print(ans[c]-rest*(rest+1)//2)
