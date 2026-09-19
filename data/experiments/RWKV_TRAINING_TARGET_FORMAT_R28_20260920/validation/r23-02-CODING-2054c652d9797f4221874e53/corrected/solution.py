import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];counts=[0]*4
for age in v[1:1+n]:counts[0 if age<=18 else 1 if age<=35 else 2 if age<=60 else 3]+=1
for count in counts:
 hundredths=(count*20000+n)//(2*n);print(f'{hundredths//100}.{hundredths%100:02d}%')
