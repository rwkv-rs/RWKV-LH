import sys
xp,yp,xv,yv=map(int,sys.stdin.buffer.read().split())
print('Polycarp' if (xp<=xv and yp<=yv) or xp+yp<=max(xv,yv) else 'Vasiliy')
