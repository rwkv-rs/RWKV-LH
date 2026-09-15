s=input().strip();k=int(input());mod=10**9+7;inv2=(mod+1)//2;ways=pow(2,s.count('?')*k,mod)
def difference(a,b):
    if '?' in (a,b):return ways*inv2%mod
    return ways if a!=b else 0
edges=sum(difference(a,b) for a,b in zip(s,s[1:]))*k
edges+=difference(s[-1],s[0])*(k-1)
ends=0 if len(s)*k==1 else difference(s[0],s[-1])
print((edges+ends)*inv2%mod)
