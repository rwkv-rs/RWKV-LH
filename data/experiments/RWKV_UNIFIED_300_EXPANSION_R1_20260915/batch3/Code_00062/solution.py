import sys
from collections import deque
input=sys.stdin.buffer.readline
h,w,k=map(int,input().split());sx,sy,tx,ty=map(int,input().split());sx-=1;sy-=1;tx-=1;ty-=1
g=[input().strip() for _ in range(h)];d=[[-1]*w for _ in range(h)];d[sx][sy]=0;q=deque([(sx,sy)])
while q:
    x,y=q.popleft()
    if (x,y)==(tx,ty):print(d[x][y]);raise SystemExit
    nd=d[x][y]+1
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        xx,yy=x,y
        for _ in range(k):
            xx+=dx;yy+=dy
            if not (0<=xx<h and 0<=yy<w) or g[xx][yy]==64:break
            old=d[xx][yy]
            if 0<=old<nd:break
            if old==nd:continue
            d[xx][yy]=nd;q.append((xx,yy))
print(-1)
