import sys
v=list(map(int,sys.stdin.buffer.read().split()));queries=v[1:];maximum=max(queries);grundy=[0,0];forward={};reverse={}
for n in range(2,maximum+1):
 index=n-2;g=grundy[index]
 for value in reverse:reverse[value]<<=1
 forward[g]=forward.get(g,0)|(1<<index);reverse[g]=reverse.get(g,0)|1;candidate=0
 while True:
  exists=False
  for a,positions in forward.items():
   if positions&reverse.get(a^candidate,0):exists=True;break
  if not exists:break
  candidate+=1
 grundy.append(candidate)
print('\n'.join('Arjuna' if grundy[n] else 'Bhima' for n in queries))
