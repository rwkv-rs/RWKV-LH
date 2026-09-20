import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[];base=2401;powers=[1,7,49,343];corner={0:0,2:1,6:2,8:3};moves=[[j for j in range(9) if i//3==j//3 or i%3==j%3] for i in range(9)];covers=[]
for pos in range(9):
 y,x=divmod(pos,3);covers.append([4*y+x,4*y+x+1,4*y+x+4,4*y+x+5])
advance=[]
for age in range(base):
 ages=[age//power%7 for power in powers];row=[]
 for wet in range(5):
  nextages=[0 if i==wet else ages[i]+1 for i in range(4)];row.append(-1 if max(nextages)>6 else sum(x*power for x,power in zip(nextages,powers)))
 advance.append(row)
while p<len(v):
 n=v[p];p+=1
 if n==0:break
 schedule=[v[p+16*i:p+16*i+16] for i in range(n)];p+=16*n
 if any(schedule[0][cell] for cell in covers[4]):out.append('0');continue
 states={4*base+400}
 for day in schedule[1:]:
  allowed=[not any(day[cell] for cell in cover) for cover in covers];new=set()
  for state in states:
   pos,age=divmod(state,base)
   for target in moves[pos]:
    if allowed[target]:
     nxt=advance[age][corner.get(target,4)]
     if nxt>=0:new.add(target*base+nxt)
  states=new
  if not states:break
 out.append('1' if states else '0')
print('\n'.join(out))
