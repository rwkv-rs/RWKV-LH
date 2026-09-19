import sys,re,bisect
lines=sys.stdin.read().splitlines();n=int(lines[0]);stack=[(-2**31,2**31-1)];assignments=[];coordinates={-2**31,2**31}
for line in lines[1:n+1]:
 s=line.strip()
 if s.startswith('if'):
  value=int(re.search(r'\d+',s).group());low,high=stack[-1]
  if '>' in s:low=max(low,value+1)
  else:high=min(high,value-1)
  stack.append((low,high))
 elif s.startswith('}') :stack.pop()
 else:
  value=int(re.search(r'\d+',s).group());low,high=stack[-1]
  if low<=high:assignments.append((low,high,value));coordinates.update((low,high+1))
coordinates=sorted(coordinates);values=[0]*(len(coordinates)-1)
for low,high,value in assignments:
 left=bisect.bisect_left(coordinates,low);right=bisect.bisect_left(coordinates,high+1)
 for i in range(left,right):values[i]=value
print(' '.join(map(str,sorted(set(values)))))
