import sys
v=list(map(int,sys.stdin.buffer.read().split()));queries=v[1:1+v[0]];wanted=set(queries);counts=[0]*10;answers={0:' '.join(map(str,counts))}
for i in range(1,max(queries,default=0)+1):
 for c in str(i):counts[int(c)]+=1
 if i in wanted:answers[i]=' '.join(map(str,counts))
print('\n'.join(answers[i] for i in queries))
