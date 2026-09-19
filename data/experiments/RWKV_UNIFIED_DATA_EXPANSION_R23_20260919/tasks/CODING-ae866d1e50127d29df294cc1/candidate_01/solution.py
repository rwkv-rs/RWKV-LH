import sys
v=list(map(int,sys.stdin.read().split()));truck=v[8:12];answer=0
for a,b,c,d in (v[:4],v[4:8]):answer+=(c-a)*(d-b)-max(0,min(c,truck[2])-max(a,truck[0]))*max(0,min(d,truck[3])-max(b,truck[1]))
print(answer)
