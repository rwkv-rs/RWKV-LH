import sys,math
read=sys.stdin.buffer.readline;n=int(read());size=1<<n;f=[0]*size
for _ in range(size):
 signs,value=read().split();mask=0
 for j,c in enumerate(signs):
  if c==45:mask|=1<<j
 s=value.decode();negative=s.startswith('-');s=s.lstrip('+-');whole,sep,decimal=s.partition('.')
 cents=int(whole)*100+int((decimal+'00')[:2]);f[mask]=-cents if negative else cents
step=1
while step<size:
 jump=step*2
 for base in range(0,size,jump):
  for j in range(base,base+step):
   a,b=f[j],f[j+step];f[j]=a+b;f[j+step]=a-b
 step=jump
denominator=100*size;stack=[(0,0,'')];out=[]
while stack:
 mask,start,name=stack.pop();value=f[mask]
 if value:
  g=math.gcd(value,denominator);top=value//g;bottom=denominator//g
  coefficient=str(top) if bottom==1 else str(top)+'/'+str(bottom)
  out.append(coefficient+(' '+name if name else '')+'\n')
  if len(out)>=4096:sys.stdout.write(''.join(out));out=[]
 for j in range(n-1,start-1,-1):stack.append((mask|(1<<j),j+1,name+'x'+str(j+1)))
sys.stdout.write(''.join(out))
