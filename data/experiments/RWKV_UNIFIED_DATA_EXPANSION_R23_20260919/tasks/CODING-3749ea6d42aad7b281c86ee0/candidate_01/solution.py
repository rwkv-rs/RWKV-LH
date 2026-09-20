import sys
MOD=2011
def evaluate(grid,top,bottom,left,right):
 while all(grid[y][left]=='.' for y in range(top,bottom)):left+=1
 baseline=next(y for y in range(top,bottom) if grid[y][left]!='.');row=grid[baseline];position=left
 def skip():
  nonlocal position
  while position<right and row[position]=='.':position+=1
 def factor():
  nonlocal position
  skip();start=position;char=row[position]
  if char=='-' and position+1<right and row[position+1]=='-':
   while position<right and row[position]=='-':position+=1
   numerator=evaluate(grid,top,baseline,start,position);denominator=evaluate(grid,baseline+1,bottom,start,position);return numerator*pow(denominator,MOD-2,MOD)%MOD
  if char=='-':position+=1;return -factor()%MOD
  if char=='(':
   level=1;position+=1;inner=position
   while level:
    if row[position]=='(':level+=1
    elif row[position]==')':level-=1
    position+=1
   value=evaluate(grid,top,bottom,inner,position-1)
  else:value=int(char);position+=1
  if baseline>top and position<right and grid[baseline-1][position].isdigit():value=pow(value,int(grid[baseline-1][position]),MOD);position+=1
  return value
 def term():
  nonlocal position
  value=factor();skip()
  while position<right and row[position]=='*':position+=1;value=value*factor()%MOD;skip()
  return value
 value=term();skip()
 while position<right:
  operator=row[position];position+=1;other=term();value=(value+other if operator=='+' else value-other)%MOD;skip()
 return value
lines=iter(sys.stdin.read().splitlines());out=[]
for line in lines:
 if not line.strip():continue
 n=int(line)
 if n==0:break
 raw=[next(lines).replace(' ','.') for _ in range(n)];width=max(map(len,raw));grid=[s.ljust(width,'.') for s in raw];out.append(str(evaluate(grid,0,n,0,width)))
print('\n'.join(out))
