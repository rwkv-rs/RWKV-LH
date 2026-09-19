import sys,math
out=[]
for k in map(int,sys.stdin.read().split()):
 row=(math.isqrt(8*k+1)-1)//2
 if row*(row+1)//2<k:row+=1
 col=k-row*(row-1)//2;out.append(str(row-col+1)+'/'+str(col))
print('\n'.join(out))
