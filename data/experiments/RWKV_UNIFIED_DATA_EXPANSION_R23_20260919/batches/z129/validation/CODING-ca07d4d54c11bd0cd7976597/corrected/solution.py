import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];b=v[n+1:2*n+1];c=v[2*n+1:];active=[a[i]+c[i] if a[i] else 0 for i in range(n)];exports=[min(b[i],active[i]) for i in range(n)];pool=sum(exports)
if pool==0:print(*active);print(sum(active));raise SystemExit
gain=[min(b[i],c[i]+1)-1 if a[i]==0 and b[i]>0 else 0 for i in range(n)];extra=sum(gain);answer=[]
for i in range(n):
 if a[i]:answer.append(active[i]+pool-exports[i]+extra)
 else:answer.append(pool+extra-gain[i]+c[i])
total=sum(active)+sum(c[i] for i in range(n) if not a[i] and b[i]);sinks=sorted((c[i] for i in range(n) if not a[i] and not b[i]),reverse=True);total+=sum(sinks[:pool+extra]);print(*answer);print(total)
