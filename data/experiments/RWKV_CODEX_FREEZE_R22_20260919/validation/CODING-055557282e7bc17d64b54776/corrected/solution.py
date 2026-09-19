import sys
f=sys.stdin.buffer;n=int(f.readline());traits=[]
for _ in range(n):
 p=f.readline().split();traits.append(set(p[2:2+int(p[1])]))
print(max(len(traits[i]&traits[j]) for i in range(n) for j in range(i))+1)
