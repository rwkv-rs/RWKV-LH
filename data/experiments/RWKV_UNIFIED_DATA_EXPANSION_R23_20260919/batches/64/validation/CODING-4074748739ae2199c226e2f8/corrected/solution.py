import sys
v=sys.stdin.buffer.read().split();p=0;case=0;out=[]
while p<len(v):
 r=int(v[p]);p+=1
 if r==0:break
 c=int(v[p]);p+=1;grid=[x.decode() for x in v[p:p+r]];p+=r;case+=1;numbers={};number=0
 for i in range(r):
  for j in range(c):
   if grid[i][j]!='*' and (i==0 or j==0 or grid[i-1][j]=='*' or grid[i][j-1]=='*'):number+=1;numbers[i,j]=number
 if out:out.append('')
 out.extend([f'puzzle #{case}:','Across'])
 for i in range(r):
  for j in range(c):
   if grid[i][j]!='*' and (j==0 or grid[i][j-1]=='*'):
    end=j
    while end<c and grid[i][end]!='*':end+=1
    out.append('%3d.%s'%(numbers[i,j],grid[i][j:end]))
 out.append('Down')
 for i in range(r):
  for j in range(c):
   if grid[i][j]!='*' and (i==0 or grid[i-1][j]=='*'):
    end=i;word=[]
    while end<r and grid[end][j]!='*':word.append(grid[end][j]);end+=1
    out.append('%3d.%s'%(numbers[i,j],''.join(word)))
print('\n'.join(out))
