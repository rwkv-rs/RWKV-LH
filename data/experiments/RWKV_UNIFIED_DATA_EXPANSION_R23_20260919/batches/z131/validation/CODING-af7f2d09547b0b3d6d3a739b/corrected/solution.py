import sys
v=sys.stdin.buffer.read().split();expression=v[0];plus=int(v[1]);minus=int(v[2]);limit=min(plus,minus);rare_plus=plus<=minus;stack=[];inf=10**9
for ch in expression:
 if 49<=ch<=57:stack.append(([ch-48],[ch-48]));continue
 if ch!=41:continue
 rightmax,rightmin=stack.pop();leftmax,leftmin=stack.pop();size=min(limit+1,len(leftmax)+len(rightmax));high=[-inf]*size;low=[inf]*size
 for i,hi in enumerate(leftmax):
  lo=leftmin[i]
  for j,hj in enumerate(rightmax):
   total=i+j
   if total>=size:break
   lj=rightmin[j];p=total+rare_plus;m=total+(not rare_plus)
   if p<size:
    high[p]=max(high[p],hi+hj);low[p]=min(low[p],lo+lj)
   if m<size:
    high[m]=max(high[m],hi-lj);low[m]=min(low[m],lo-hj)
 stack.append((high,low))
print(stack[0][0][limit])
