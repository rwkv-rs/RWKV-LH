import sys,bisect
v=sys.stdin.read().split();n=int(v[0]);tails=[]
for i in range(n):
 species=int(v[2+2*i]);j=bisect.bisect_right(tails,species)
 if j==len(tails):tails.append(species)
 else:tails[j]=species
print(n-len(tails))
