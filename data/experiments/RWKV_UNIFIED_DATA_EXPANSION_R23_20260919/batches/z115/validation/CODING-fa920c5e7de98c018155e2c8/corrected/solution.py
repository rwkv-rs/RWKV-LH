import sys
v=sys.stdin.buffer.read().split();p=0;case=0;out=[]
while p<len(v):
 n=int(v[p]);p+=1
 if n==0:break
 rows=v[p:p+n];p+=n;best=0;previous=[]
 for r,line in enumerate(rows):
  current=[0]*len(line)
  for j in range(0,len(line),2):
   if line[j]==45:
    current[j]=1
    if r and rows[r-1][j+1]==45:current[j]+=min(previous[j],previous[j+2])
    best=max(best,current[j])
  previous=current
 following=[]
 for r in range(n-1,-1,-1):
  line=rows[r];current=[0]*len(line)
  for j in range(1,len(line),2):
   if line[j]==45:
    current[j]=1
    if r+1<n and j>=2 and j<len(following) and rows[r+1][j-1]==45:current[j]+=min(following[j-2],following[j])
    best=max(best,current[j])
  following=current
 case+=1;out.extend((f'Triangle #{case}',f'The largest triangle area is {best*best}.'))
print('\n'.join(out))
