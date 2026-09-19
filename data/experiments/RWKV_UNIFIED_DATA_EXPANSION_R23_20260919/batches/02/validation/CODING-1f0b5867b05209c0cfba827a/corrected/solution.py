import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];prob=v[1:1+n];mod=998244353;inv100=pow(100,mod-2,mod);values=sorted(set(prob)-{0});index={p:i for i,p in enumerate(values)};ps=[p*inv100%mod for p in values];history=[0]*len(ps);inverses={p:pow((100-p)*inv100%mod,mod-2,mod) for p in set(prob)};answer=0
for p in prob:
 increment=1 if p==0 else (1+history[index[p]])*inverses[p]%mod
 answer=(answer+increment)%mod
 history=[(s+q*increment)*q%mod for q,s in zip(ps,history)]
print(answer)
