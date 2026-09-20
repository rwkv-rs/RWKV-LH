import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];difference=[0]*n
for i,value in enumerate(a[:-1]):
 difference[i]+=value;distance=n-1-i;position=i
 while distance:
  jump=1<<(distance.bit_length()-1);position+=jump;distance-=jump
  if position<n-1:difference[position]+=value
current=0;out=[]
for value in difference[:-1]:current+=value;out.append(str(current))
print('\n'.join(out))
