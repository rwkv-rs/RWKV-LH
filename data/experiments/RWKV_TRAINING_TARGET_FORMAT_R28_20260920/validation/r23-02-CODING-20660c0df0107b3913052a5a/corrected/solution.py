import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,c=v[:2];stairs=v[2:n+1];elevator=v[n+1:];walk=0;ride=c;out=[0]
for a,b in zip(stairs,elevator):walk,ride=min(walk,ride)+a,min(ride,walk+c)+b;out.append(min(walk,ride))
print(*out)
